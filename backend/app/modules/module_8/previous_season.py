# "Copy from last season" for Altsien Select's Ploeg Wizard: most teams
# make largely the same choices every season, so a step can offer last
# season's values line by line and copy the lines the Kernlid ticks into
# the current season. Copying only adds or updates — it never removes a
# current choice and never marks the step as done.
#
# To offer this on another wizard step (e.g. products, once that module
# exists): write a list_lines + copy_lines pair below and register it in
# COPYABLE_STEPS under the step's key. The wizard then shows the panel for
# that step automatically (StepResponse.copy_from_previous).

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_request_status import AltsienSelectRequestStatus
from app.db.models.altsien_select_special_request import AltsienSelectSpecialRequest
from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.season import Season
from app.db.models.team_responsible import TeamResponsible
from app.db.models.user import User
from app.modules.module_2.plan_kar_service import upsert_plan_kar_rows
from app.modules.module_8.steps import selected_festival_ids
from app.modules.module_9.team_responsible_service import apply_team_responsible_fields, list_team_responsibles

# Why a line can't be copied (the frontend translates these codes).
NOT_IN_SEASON = "not_in_season"
FESTIVAL_NOT_SELECTED = "festival_not_selected"
LOCATION_INACTIVE = "location_inactive"


@dataclass(frozen=True)
class PreviousLine:
    """One of last season's values, as offered in the wizard's copy panel."""

    # Stable identifier within the step (the source row's id), sent back
    # by the frontend to say which lines to copy.
    key: str
    # What the line is (a festival, a person, a request text) ...
    label: str
    # ... and its value last season (a location, contact details, a status).
    detail: str | None = None
    # Where it lands this season, when that differs from the label (e.g.
    # the matching festival of this season).
    target: str | None = None
    # The value there now, when it differs from last season's.
    current_detail: str | None = None
    # True when this season already holds the same value.
    already_present: bool = False
    # Set when the line can't be copied at all (see the codes above).
    unavailable_reason: str | None = None
    # What copy_lines needs to write the line; never sent to the frontend.
    payload: object = field(default=None, compare=False, repr=False)

    @property
    def copyable(self) -> bool:
        """Whether copying this line would change anything."""
        return self.unavailable_reason is None and not self.already_present


@dataclass(frozen=True)
class CopyHandler:
    """How one wizard step lists and copies last season's values."""

    # (db, previous season, current season, team id) -> lines
    list_lines: Callable[[Session, Season, Season, int], list[PreviousLine]]
    # (db, user, current season, team id, copyable lines to copy) -> None;
    # adds the rows to the session, the caller commits.
    copy_lines: Callable[[Session, User, Season, int, list[PreviousLine]], None]


def previous_season_of(db: Session, season: Season) -> Season | None:
    """The season right before this one, by name — the same order as the
    module's season dropdown ("2025" comes before "2026").
    """
    return db.scalar(select(Season).where(Season.name < season.name).order_by(Season.name.desc()).limit(1))


_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
_NON_WORD_PATTERN = re.compile(r"[\W_]+")


def normalize_festival_name(name: str) -> str:
    """A festival's name without case, years and punctuation, so that
    "Rock Werchter 2025" and "rock werchter 2026" count as the same festival.
    """
    without_years = _YEAR_PATTERN.sub(" ", name.lower())
    return " ".join(_NON_WORD_PATTERN.sub(" ", without_years).split())


# --- Step 2: delivery locations --------------------------------------------


def _afleverlocatie_lines(db: Session, previous: Season, season: Season, team_id: int) -> list[PreviousLine]:
    """Last season's delivery location per festival, each matched to this
    season's festival with the same (normalized) name.
    """
    # Last season's Plan a kar rows of the team, with festival + location.
    previous_rows = db.execute(
        select(
            Festival.id.label("festival_id"),
            Festival.name.label("festival_name"),
            KarTrackerAfleverlocatie.id.label("location_id"),
            KarTrackerAfleverlocatie.name.label("location_name"),
            KarTrackerAfleverlocatie.active.label("location_active"),
        )
        .select_from(KarTrackerKarAfleverlocatie)
        .join(Festival, Festival.id == KarTrackerKarAfleverlocatie.festival_id)
        .join(KarTrackerAfleverlocatie, KarTrackerAfleverlocatie.id == KarTrackerKarAfleverlocatie.afleverlocatie_id)
        .where(KarTrackerKarAfleverlocatie.season_id == previous.id, KarTrackerKarAfleverlocatie.team_id == team_id)
        .order_by(Festival.start_date, Festival.name)
    ).all()
    if not previous_rows:
        return []

    # This season's festivals by normalized name (the earliest one wins
    # if two happen to normalize to the same name).
    current_by_name: dict[str, Festival] = {}
    for festival in db.scalars(
        select(Festival).where(Festival.season_id == season.id).order_by(Festival.start_date, Festival.id)
    ).all():
        current_by_name.setdefault(normalize_festival_name(festival.name), festival)
    selected_ids = selected_festival_ids(db, season.id, team_id)

    # The locations chosen so far this season, per festival.
    current_locations = {
        row.festival_id: (row.location_id, row.location_name)
        for row in db.execute(
            select(
                KarTrackerKarAfleverlocatie.festival_id,
                KarTrackerAfleverlocatie.id.label("location_id"),
                KarTrackerAfleverlocatie.name.label("location_name"),
            )
            .select_from(KarTrackerKarAfleverlocatie)
            .join(KarTrackerAfleverlocatie, KarTrackerAfleverlocatie.id == KarTrackerKarAfleverlocatie.afleverlocatie_id)
            .where(KarTrackerKarAfleverlocatie.season_id == season.id, KarTrackerKarAfleverlocatie.team_id == team_id)
        ).all()
    }

    lines = []
    for row in previous_rows:
        target = current_by_name.get(normalize_festival_name(row.festival_name))
        current_id, current_name = current_locations.get(target.id, (None, None)) if target else (None, None)

        # The first reason that applies decides why a line can't be copied.
        if target is None:
            reason = NOT_IN_SEASON
        elif target.id not in selected_ids:
            reason = FESTIVAL_NOT_SELECTED
        elif not row.location_active:
            reason = LOCATION_INACTIVE
        else:
            reason = None

        lines.append(
            PreviousLine(
                key=str(row.festival_id),
                label=row.festival_name,
                detail=row.location_name,
                target=target.name if target is not None and target.name != row.festival_name else None,
                current_detail=current_name if current_id is not None and current_id != row.location_id else None,
                already_present=current_id == row.location_id,
                unavailable_reason=reason,
                payload=(target.id, row.location_id) if target is not None else None,
            )
        )
    return lines


def _copy_afleverlocaties(db: Session, user: User, season: Season, team_id: int, lines: list[PreviousLine]) -> None:
    """Write last season's locations onto this season's matching festivals,
    through the same Plan a kar logic the step itself uses.
    """
    upsert_plan_kar_rows(db, season.id, team_id, [line.payload for line in lines])


# --- Step 3: team leads ------------------------------------------------------


def _person_key(person: TeamResponsible) -> tuple[str, str]:
    """Two rows describe the same person when name and email match."""
    return person.name.strip().lower(), person.email.strip().lower()


def _responsible_lines(db: Session, previous: Season, season: Season, team_id: int) -> list[PreviousLine]:
    """Last season's team leads, flagged when already listed this season."""
    current_keys = {_person_key(person) for person in list_team_responsibles(db, season.id, team_id)}
    return [
        PreviousLine(
            key=str(person.id),
            label=person.name,
            detail=" · ".join(part for part in (person.email, person.phone) if part),
            already_present=_person_key(person) in current_keys,
            payload=person,
        )
        for person in list_team_responsibles(db, previous.id, team_id)
    ]


def _copy_responsibles(db: Session, user: User, season: Season, team_id: int, lines: list[PreviousLine]) -> None:
    """Add a copy of each chosen person to this season — once, even when
    last season listed the same person twice.
    """
    copied: set[tuple[str, str]] = set()
    for line in lines:
        source: TeamResponsible = line.payload
        if _person_key(source) in copied:
            continue
        copied.add(_person_key(source))
        copy = TeamResponsible(season_id=season.id, team_id=team_id)
        apply_team_responsible_fields(
            copy, name=source.name, email=source.email, phone=source.phone, comments=source.comments
        )
        db.add(copy)


# --- Step 5: special requests -----------------------------------------------


def _request_lines(db: Session, previous: Season, season: Season, team_id: int) -> list[PreviousLine]:
    """Last season's requests (with the status they ended in), flagged when
    a request with the same text already exists this season.
    """
    current_texts = set(
        text.strip()
        for text in db.scalars(
            select(AltsienSelectSpecialRequest.text).where(
                AltsienSelectSpecialRequest.season_id == season.id, AltsienSelectSpecialRequest.team_id == team_id
            )
        ).all()
    )
    rows = db.execute(
        select(AltsienSelectSpecialRequest, AltsienSelectRequestStatus.name)
        .join(AltsienSelectRequestStatus, AltsienSelectRequestStatus.id == AltsienSelectSpecialRequest.status_id)
        .where(AltsienSelectSpecialRequest.season_id == previous.id, AltsienSelectSpecialRequest.team_id == team_id)
        .order_by(AltsienSelectSpecialRequest.created_at, AltsienSelectSpecialRequest.id)
    ).all()
    return [
        PreviousLine(
            key=str(request.id),
            label=request.text,
            detail=status_name,
            already_present=request.text.strip() in current_texts,
            payload=request,
        )
        for request, status_name in rows
    ]


def _copy_requests(db: Session, user: User, season: Season, team_id: int, lines: list[PreviousLine]) -> None:
    """Add each chosen text as a new request of this season, in the first
    status (the same rule as service.first_request_status — not imported
    from there because service.py imports this module).
    """
    first_status_id = db.scalar(
        select(AltsienSelectRequestStatus.id)
        .order_by(AltsienSelectRequestStatus.sort_order, AltsienSelectRequestStatus.id)
        .limit(1)
    )
    if first_status_id is None:
        raise ValueError("No request status is defined")
    # Each text once, even when last season had the same request twice.
    copied: set[str] = set()
    for line in lines:
        source: AltsienSelectSpecialRequest = line.payload
        if source.text.strip() in copied:
            continue
        copied.add(source.text.strip())
        db.add(
            AltsienSelectSpecialRequest(
                season_id=season.id,
                team_id=team_id,
                text=source.text.strip(),
                status_id=first_status_id,
                created_by_user_id=user.id,
            )
        )


# The steps that offer "copy from last season", by step key.
COPYABLE_STEPS: dict[str, CopyHandler] = {
    "afleverlocaties": CopyHandler(_afleverlocatie_lines, _copy_afleverlocaties),
    "ploegverantwoordelijken": CopyHandler(_responsible_lines, _copy_responsibles),
    "special_requests": CopyHandler(_request_lines, _copy_requests),
}


def list_previous_lines(
    db: Session, step_key: str, season: Season, team_id: int
) -> tuple[Season | None, list[PreviousLine]]:
    """Last season and its lines for one step of one team (no lines when
    there is no earlier season). The step key must be in COPYABLE_STEPS.
    """
    previous = previous_season_of(db, season)
    if previous is None:
        return None, []
    return previous, COPYABLE_STEPS[step_key].list_lines(db, previous, season, team_id)
