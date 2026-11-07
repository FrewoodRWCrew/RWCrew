# Shared logic for "festivals per team" (MasterData_team_festival): at which
# festivals of a year a team works. This is the only writer of that table —
# used by MasterData's "Festivals per ploeg" grid (module_9/router.py), by
# step 1 of Altsien Select's Ploeg Wizard (module_8/router.py), by its "copy
# from last season" panel (module_8/previous_season.py) and by the XLSX import
# (module_9/team_festival_import.py), so the rules are the same everywhere —
# the same idea as team_responsible_service.py.
#
# The rules:
#   - a new link must point at an *active* festival of that year (a link that
#     already exists may stay, even when the festival was deactivated since);
#   - removing a link also removes the team's Plan a kar delivery location at
#     that festival (KarTracker_kar_afleverlocaties);
#   - every change un-marks the wizard's "afleverlocaties" step (the delivery
#     locations must be confirmed again), and a team left without festivals
#     also loses its "festivals" step.
# Nothing here commits: the caller does.
#
# This module only imports models (no module-8 code), so module-8 can import
# it without an import cycle.

import re
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.festival import Festival
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival

# The Altsien Select wizard steps built on the festival choice (see
# module_8/steps.py) — kept here so every place that changes the choice can
# un-mark them.
FESTIVALS_STEP_KEY = "festivals"
AFLEVERLOCATIES_STEP_KEY = "afleverlocaties"


class TeamFestivalError(ValueError):
    """A change that breaks one of the rules above; the message is the
    English detail the routers return with a 400.
    """


# --- Small read helpers -------------------------------------------------------


def linked_festival_ids(db: Session, season_id: int, team_id: int) -> set[int]:
    """The festivals this team works at in this year."""
    return set(
        db.scalars(
            select(TeamFestival.festival_id).where(
                TeamFestival.season_id == season_id, TeamFestival.team_id == team_id
            )
        ).all()
    )


def previous_season_of(db: Session, season: Season) -> Season | None:
    """The year right before this one, by name — the same order as the
    year dropdowns ("2025" comes before "2026").
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


def active_festivals_by_name(db: Session, season_id: int) -> dict[str, Festival]:
    """This year's active festivals by normalized name (the earliest one wins
    when two normalize to the same name).
    """
    by_name: dict[str, Festival] = {}
    for festival in db.scalars(
        select(Festival)
        .where(Festival.season_id == season_id, Festival.active.is_(True))
        .order_by(Festival.start_date, Festival.id)
    ).all():
        by_name.setdefault(normalize_festival_name(festival.name), festival)
    return by_name


def _clear_step(db: Session, season_id: int, team_id: int, step_key: str) -> None:
    """Un-mark one wizard step of a team (no-op when it wasn't marked)."""
    db.execute(
        delete(AltsienSelectStepProgress).where(
            AltsienSelectStepProgress.season_id == season_id,
            AltsienSelectStepProgress.team_id == team_id,
            AltsienSelectStepProgress.step_key == step_key,
        )
    )


# --- Writing --------------------------------------------------------------------


def set_team_festivals(db: Session, season: Season, team: Team, wanted_ids: set[int]) -> tuple[set[int], set[int]]:
    """Make the team's festivals of this year exactly `wanted_ids`.
    Returns (added ids, removed ids). Raises TeamFestivalError when a newly
    added festival isn't an active festival of the year.
    """
    current_links = {
        link.festival_id: link
        for link in db.scalars(
            select(TeamFestival).where(TeamFestival.season_id == season.id, TeamFestival.team_id == team.id)
        ).all()
    }

    # Newly added festivals must be active festivals of this year (ones
    # already linked may stay, even if they were deactivated since).
    added_ids = set(wanted_ids) - set(current_links)
    if added_ids:
        valid_ids = set(
            db.scalars(
                select(Festival.id).where(
                    Festival.id.in_(added_ids), Festival.season_id == season.id, Festival.active.is_(True)
                )
            ).all()
        )
        if valid_ids != added_ids:
            raise TeamFestivalError("Every festival must be an active festival of the year")

    # Remove deselected festivals, and the team's delivery location there.
    removed_ids = set(current_links) - set(wanted_ids)
    for festival_id in removed_ids:
        db.delete(current_links[festival_id])
    if removed_ids:
        db.execute(
            delete(KarTrackerKarAfleverlocatie).where(
                KarTrackerKarAfleverlocatie.season_id == season.id,
                KarTrackerKarAfleverlocatie.team_id == team.id,
                KarTrackerKarAfleverlocatie.festival_id.in_(removed_ids),
            )
        )
    for festival_id in added_ids:
        db.add(TeamFestival(season_id=season.id, team_id=team.id, festival_id=festival_id))

    # A changed selection invalidates the wizard steps built on top of it;
    # the Kernlid confirms them again.
    if added_ids or removed_ids:
        _clear_step(db, season.id, team.id, AFLEVERLOCATIES_STEP_KEY)
        if not wanted_ids:
            _clear_step(db, season.id, team.id, FESTIVALS_STEP_KEY)

    # Flushed now, so a later read in the same request sees the new state.
    db.flush()
    return added_ids, removed_ids


def add_team_festivals(db: Session, season: Season, team: Team, festival_ids: set[int]) -> set[int]:
    """Add festivals to the team's choice, keeping the ones it has (used by
    the XLSX import and "copy from last season", which never remove).
    Returns the ids that were really new.
    """
    current = linked_festival_ids(db, season.id, team.id)
    added, _removed = set_team_festivals(db, season, team, current | set(festival_ids))
    return added


@dataclass(frozen=True)
class GridChange:
    """One ticked/unticked cell of the grid."""

    team_id: int
    festival_id: int
    selected: bool


def apply_grid_changes(db: Session, season: Season, changes: list[GridChange]) -> tuple[int, int]:
    """Apply the grid's changed cells, per team through set_team_festivals.
    Returns (number of links added, number removed). Raises
    TeamFestivalError for an unknown team or festival.
    """
    # Group the changes per team (the last change of a cell wins).
    per_team: dict[int, dict[int, bool]] = defaultdict(dict)
    for change in changes:
        per_team[change.team_id][change.festival_id] = change.selected

    # Every festival must belong to this year (inactive ones may only be
    # unticked; set_team_festivals refuses adding them).
    festival_ids = {festival_id for cells in per_team.values() for festival_id in cells}
    if festival_ids:
        known = set(
            db.scalars(select(Festival.id).where(Festival.id.in_(festival_ids), Festival.season_id == season.id)).all()
        )
        if known != festival_ids:
            raise TeamFestivalError("Every festival must be a festival of the year")

    added_total = removed_total = 0
    for team_id, cells in per_team.items():
        team = db.get(Team, team_id)
        if team is None:
            raise TeamFestivalError("Team not found")
        wanted = linked_festival_ids(db, season.id, team.id)
        for festival_id, selected in cells.items():
            if selected:
                wanted.add(festival_id)
            else:
                wanted.discard(festival_id)
        added, removed = set_team_festivals(db, season, team, wanted)
        added_total += len(added)
        removed_total += len(removed)
    return added_total, removed_total


# --- The grid -------------------------------------------------------------------


@dataclass
class TeamFestivalGrid:
    """Everything MasterData's grid shows for one year."""

    festivals: list[Festival]
    teams: list[Team]
    # (team id, festival id) of every link.
    links: list[tuple[int, int]]
    # (team id, festival id) of links that also have a Plan a kar delivery
    # location, which unticking would delete.
    planned: list[tuple[int, int]]


def build_grid(db: Session, season_id: int) -> TeamFestivalGrid:
    """The year's festivals (active ones, plus inactive ones still linked),
    every active team (plus inactive teams that still have links), sorted
    by name, and the links between them.
    """
    links = [
        (row.team_id, row.festival_id)
        for row in db.execute(
            select(TeamFestival.team_id, TeamFestival.festival_id).where(TeamFestival.season_id == season_id)
        ).all()
    ]
    linked_team_ids = {team_id for team_id, _festival_id in links}
    linked_festival_ids_ = {festival_id for _team_id, festival_id in links}

    festivals = [
        festival
        for festival in db.scalars(
            select(Festival).where(Festival.season_id == season_id).order_by(Festival.start_date, Festival.name)
        ).all()
        if festival.active or festival.id in linked_festival_ids_
    ]
    teams = [
        team
        for team in db.scalars(select(Team).order_by(Team.name, Team.id)).all()
        if team.active or team.id in linked_team_ids
    ]

    # Links whose team has a delivery location at that festival.
    planned_pairs = {
        (row.team_id, row.festival_id)
        for row in db.execute(
            select(KarTrackerKarAfleverlocatie.team_id, KarTrackerKarAfleverlocatie.festival_id).where(
                KarTrackerKarAfleverlocatie.season_id == season_id
            )
        ).all()
    }
    planned = [pair for pair in links if pair in planned_pairs]
    return TeamFestivalGrid(festivals=festivals, teams=teams, links=sorted(links), planned=sorted(planned))


# --- Copy from the previous year -----------------------------------------------


@dataclass
class UnmatchedFestival:
    """A festival of last year with links but no active festival of the same
    name this year, so its links can't be copied.
    """

    festival_name: str
    team_count: int


@dataclass
class PreviousYearProposal:
    """Last year's links mapped onto this year's festivals — nothing saved."""

    previous_season: Season | None
    # (team id, festival id of THIS year), only links that don't exist yet.
    links: list[tuple[int, int]] = field(default_factory=list)
    # Links that already exist this year.
    already_present: int = 0
    unmatched: list[UnmatchedFestival] = field(default_factory=list)


def previous_year_proposal(db: Session, season: Season) -> PreviousYearProposal:
    """Every team's links of the previous year, each mapped onto this
    year's active festival with the same (normalized) name. Teams that are
    no longer active are skipped. Nothing is written.
    """
    previous = previous_season_of(db, season)
    if previous is None:
        return PreviousYearProposal(previous_season=None)

    previous_rows = db.execute(
        select(TeamFestival.team_id, Festival.name)
        .join(Festival, Festival.id == TeamFestival.festival_id)
        .join(Team, Team.id == TeamFestival.team_id)
        .where(TeamFestival.season_id == previous.id, Team.active.is_(True))
        .order_by(Festival.start_date, Festival.name)
    ).all()
    if not previous_rows:
        return PreviousYearProposal(previous_season=previous)

    current_by_name = active_festivals_by_name(db, season.id)
    existing = set(
        db.execute(select(TeamFestival.team_id, TeamFestival.festival_id).where(TeamFestival.season_id == season.id))
        .tuples()
        .all()
    )

    proposal = PreviousYearProposal(previous_season=previous)
    proposed: set[tuple[int, int]] = set()
    unmatched_teams: dict[str, set[int]] = {}
    for team_id, festival_name in previous_rows:
        target = current_by_name.get(normalize_festival_name(festival_name))
        if target is None:
            # No festival of that name this year: listed, not copied.
            unmatched_teams.setdefault(festival_name, set()).add(team_id)
            continue
        pair = (team_id, target.id)
        if pair in existing:
            proposal.already_present += 1
        elif pair not in proposed:
            proposed.add(pair)
    proposal.links = sorted(proposed)
    proposal.unmatched = [
        UnmatchedFestival(festival_name=name, team_count=len(team_ids)) for name, team_ids in unmatched_teams.items()
    ]
    return proposal
