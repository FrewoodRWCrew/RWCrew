# Atelier's reservations: per festival and per ploeg, how many people need
# work clothing and what each of them gets (the package: articles × pieces
# per person; the size is picked at the counter desk). The only place that
# writes Atelier_reservation and Atelier_reservation_line — the Reservaties
# screen, its "copy from last year" and the XLSX imports all go through here,
# so the rules live in one spot. Nothing here commits: the caller does.

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_reservation import AtelierReservation
from app.db.models.atelier_reservation_line import AtelierReservationLine
from app.db.models.festival import Festival
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.module_2.plan_kar_service import festivals_by_team
from app.modules.module_8.previous_season import normalize_festival_name, previous_season_of

# At the counter every package article is exactly one piece per person
# (decided 2026-10-26): whatever quantity is sent, a package line stores this.
PACKAGE_QUANTITY = 1

# Passed for `persons`, `note` or `lines` to leave that part of a
# reservation as it is (e.g. the XLSX import without a "note" column).
KEEP = object()


class ReservationError(ValueError):
    """A change that breaks a rule; the message is shown as is."""


def festival_days(festival: Festival) -> list[date]:
    """Every day of the festival, start to end (the team works each of them)."""
    return [festival.start_date + timedelta(days=offset) for offset in range((festival.end_date - festival.start_date).days + 1)]


def reservations_by_team(db: Session, festival_id: int) -> dict[int, AtelierReservation]:
    """A festival's reservations, by team id."""
    rows = db.scalars(select(AtelierReservation).where(AtelierReservation.festival_id == festival_id)).all()
    return {row.team_id: row for row in rows}


def lines_by_reservation(db: Session, reservation_ids: list[int]) -> dict[int, list[AtelierReservationLine]]:
    """The package lines of these reservations, by reservation id."""
    result: dict[int, list[AtelierReservationLine]] = {}
    if not reservation_ids:
        return result
    for line in db.scalars(
        select(AtelierReservationLine)
        .where(AtelierReservationLine.reservation_id.in_(reservation_ids))
        .order_by(AtelierReservationLine.id)
    ).all():
        result.setdefault(line.reservation_id, []).append(line)
    return result


def offered_teams(db: Session, festival: Festival) -> list[Team]:
    """The teams on a festival's Reservaties table, by name: every active
    team, plus inactive ones that already have a reservation there (so data
    entered earlier never disappears from the screen)."""
    reserved = set(reservations_by_team(db, festival.id))
    teams = db.scalars(select(Team).order_by(Team.name)).all()
    return [team for team in teams if team.active or team.id in reserved]


def festival_progress(db: Session, season_id: int) -> dict[int, list[tuple[Festival, bool]]]:
    """Per team the active festivals of the season it picked in Altsien Select
    (calendar order), each with whether its Atelier reservation is filled in
    (persons > 0; package and note aren't checked). Teams that picked nothing
    are missing from the dict ("no selection" on screen)."""
    _festivals, per_team = festivals_by_team(db, season_id)
    # Which (team, festival) pairs of the season have persons reserved.
    filled = set(
        db.execute(
            select(AtelierReservation.team_id, AtelierReservation.festival_id)
            .join(Festival, Festival.id == AtelierReservation.festival_id)
            .where(Festival.season_id == season_id, AtelierReservation.persons > 0)
        ).all()
    )
    return {
        team_id: [(festival, (team_id, festival.id) in filled) for festival in festivals]
        for team_id, festivals in per_team.items()
    }


def _get_or_create(db: Session, user: User, festival: Festival, team_id: int) -> tuple[AtelierReservation, bool]:
    """The team's reservation for the festival; a new one (0 persons) is
    added to the session when there is none. The flag says it's new."""
    existing = reservations_by_team(db, festival.id).get(team_id)
    if existing is not None:
        return existing, False
    reservation = AtelierReservation(
        season_id=festival.season_id,
        festival_id=festival.id,
        team_id=team_id,
        persons=0,
        updated_by=user.id,
        updated_by_name=user.display_name,
    )
    db.add(reservation)
    db.flush()
    return reservation, True


def _check_article(db: Session, article_id: int, already_in_package: bool) -> AtelierArticle:
    """The article must exist; an inactive one can stay in a package it's
    already in, but can't be added anew."""
    article = db.get(AtelierArticle, article_id)
    if article is None:
        raise ReservationError(f"Article {article_id} not found")
    if not article.active and not already_in_package:
        raise ReservationError(f'Article "{article.code}" is inactive and can\'t be added to a package')
    return article


def _set_lines(db: Session, reservation: AtelierReservation, lines: list[tuple[int, int]]) -> bool:
    """Replace the reservation's package with exactly these (article_id,
    quantity per person) lines — the quantity is always stored as
    PACKAGE_QUANTITY. Returns whether anything changed."""
    lines = [(article_id, PACKAGE_QUANTITY) for article_id, _quantity in lines]
    article_ids = [article_id for article_id, _quantity in lines]
    if len(article_ids) != len(set(article_ids)):
        raise ReservationError("An article can only be in a package once")
    if any(quantity < 1 for _article_id, quantity in lines):
        raise ReservationError("The quantity per person must be at least 1")

    existing = {line.article_id: line for line in lines_by_reservation(db, [reservation.id]).get(reservation.id, [])}
    changed = False
    # Lines no longer in the list are removed ...
    for article_id, line in existing.items():
        if article_id not in article_ids:
            db.delete(line)
            changed = True
    # ... and every sent line is added or updated.
    for article_id, quantity in lines:
        line = existing.get(article_id)
        _check_article(db, article_id, already_in_package=line is not None)
        if line is None:
            db.add(AtelierReservationLine(reservation_id=reservation.id, article_id=article_id, quantity_per_person=quantity))
            changed = True
        elif line.quantity_per_person != quantity:
            line.quantity_per_person = quantity
            changed = True
    db.flush()
    return changed


def _is_empty(db: Session, reservation: AtelierReservation) -> bool:
    """No persons, no note and no package: nothing left worth keeping."""
    return (
        reservation.persons == 0
        and reservation.note is None
        and not lines_by_reservation(db, [reservation.id]).get(reservation.id)
    )


def upsert_reservation(
    db: Session,
    user: User,
    festival: Festival,
    team_id: int,
    *,
    persons: object = KEEP,
    note: object = KEEP,
    lines: object = KEEP,
) -> str:
    """Change a team's reservation for a festival: its persons, note and/or
    whole package (pass KEEP to leave a part alone). Returns "created",
    "updated" or "unchanged". A reservation left without persons, note and
    package is removed. The changer is always the session user.
    """
    reservation, is_new = _get_or_create(db, user, festival, team_id)
    changed = False
    if persons is not KEEP and reservation.persons != persons:
        reservation.persons = persons
        changed = True
    if note is not KEEP:
        new_note = (note or "").strip() or None
        if reservation.note != new_note:
            reservation.note = new_note
            changed = True
    if lines is not KEEP and _set_lines(db, reservation, lines):
        changed = True

    if _is_empty(db, reservation):
        db.delete(reservation)
        db.flush()
        return "unchanged" if is_new else "updated"
    if is_new:
        return "created"
    if changed:
        reservation.updated_by = user.id
        reservation.updated_by_name = user.display_name
        return "updated"
    return "unchanged"


def upsert_line(db: Session, user: User, festival: Festival, team_id: int, article_id: int, quantity: int) -> str:
    """Add one article to a team's package for a festival, or change its
    quantity (the XLSX "Pakketlijnen" import). Never removes other lines.
    The quantity is always stored as PACKAGE_QUANTITY."""
    if quantity < 1:
        raise ReservationError("The quantity per person must be at least 1")
    quantity = PACKAGE_QUANTITY
    reservation, is_new = _get_or_create(db, user, festival, team_id)
    current = {line.article_id: line for line in lines_by_reservation(db, [reservation.id]).get(reservation.id, [])}
    line = current.get(article_id)
    _check_article(db, article_id, already_in_package=line is not None)
    if line is None:
        db.add(AtelierReservationLine(reservation_id=reservation.id, article_id=article_id, quantity_per_person=quantity))
    elif line.quantity_per_person == quantity:
        return "unchanged"
    else:
        line.quantity_per_person = quantity
    reservation.updated_by = user.id
    reservation.updated_by_name = user.display_name
    db.flush()
    return "created" if line is None else "updated"


# --- Copy from last year ---------------------------------------------------------


def previous_festival(db: Session, festival: Festival) -> Festival | None:
    """The same festival last season: the season right before this one,
    and a festival there whose name matches ignoring case, years and
    punctuation ("Rock Werchter 2025" ↔ "Rock Werchter 2026")."""
    season = previous_season_of(db, db.get(Season, festival.season_id))
    if season is None:
        return None
    wanted = normalize_festival_name(festival.name)
    candidates = db.scalars(select(Festival).where(Festival.season_id == season.id).order_by(Festival.start_date)).all()
    return next((candidate for candidate in candidates if normalize_festival_name(candidate.name) == wanted), None)


@dataclass
class CopyResult:
    """What "copy from last year" did."""

    teams_changed: int = 0
    # Package lines skipped because their article is no longer active.
    skipped_inactive: int = 0


def copy_from_previous_festival(db: Session, user: User, festival: Festival, team_ids: list[int]) -> CopyResult:
    """Copy last year's reservation of these teams into this festival: the
    package lines are added or updated (never removed, inactive articles
    skipped) and the persons are taken over only while this festival's
    number is still 0."""
    result = CopyResult()
    source = previous_festival(db, festival)
    if source is None:
        return result

    previous = reservations_by_team(db, source.id)
    previous_lines = lines_by_reservation(db, [row.id for row in previous.values()])
    for team_id in team_ids:
        old = previous.get(team_id)
        if old is None:
            continue
        reservation, _is_new = _get_or_create(db, user, festival, team_id)
        current = {line.article_id: line for line in lines_by_reservation(db, [reservation.id]).get(reservation.id, [])}
        changed = False
        for line in previous_lines.get(old.id, []):
            article = db.get(AtelierArticle, line.article_id)
            existing = current.get(line.article_id)
            if existing is None and not article.active:
                result.skipped_inactive += 1
                continue
            if existing is None:
                db.add(AtelierReservationLine(
                    reservation_id=reservation.id, article_id=line.article_id, quantity_per_person=PACKAGE_QUANTITY
                ))
                changed = True
            elif existing.quantity_per_person != PACKAGE_QUANTITY:
                existing.quantity_per_person = PACKAGE_QUANTITY
                changed = True
        if reservation.persons == 0 and old.persons > 0:
            reservation.persons = old.persons
            changed = True
        db.flush()
        if changed:
            reservation.updated_by = user.id
            reservation.updated_by_name = user.display_name
            result.teams_changed += 1
        elif _is_empty(db, reservation):
            # Nothing came over (e.g. only inactive articles): don't leave an empty row.
            db.delete(reservation)
            db.flush()
    return result
