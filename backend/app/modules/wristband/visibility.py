# Which counters a wristband scan shows up at. A team normally has Atelier
# products or Walkies products, not both, so a counter only shows the scans of
# teams with reservations there: a reservation with a package at any festival
# of the season. Walkies has no reservations or counter yet (stage 2): it adds
# its own rule to counter_rules here.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.atelier_reservation import AtelierReservation
from app.db.models.atelier_reservation_line import AtelierReservationLine
from app.db.models.festival import Festival
from app.db.models.season import Season
from app.db.models.wristband_scan import WristbandScan

ATELIER = "atelier"


def default_season_id(db: Session) -> int | None:
    """The season used when the screen doesn't say one: the last open one,
    else the last one (the same choice as Atelier's season dropdown)."""
    seasons = sorted(db.scalars(select(Season)).all(), key=lambda season: season.name)
    open_seasons = [season for season in seasons if season.periode_open]
    chosen = (open_seasons or seasons or [None])[-1]
    return chosen.id if chosen else None


def atelier_team_ids(db: Session, season_id: int | None) -> set[int]:
    """The teams with a package at any festival of the season."""
    if season_id is None:
        return set()
    return set(
        db.scalars(
            select(AtelierReservation.team_id)
            .join(AtelierReservationLine, AtelierReservationLine.reservation_id == AtelierReservation.id)
            .join(Festival, Festival.id == AtelierReservation.festival_id)
            .where(Festival.season_id == season_id)
        ).all()
    )


def counter_rules(db: Session) -> dict[str, set[int]]:
    """Per counter, the teams it shows in the default season."""
    return {ATELIER: atelier_team_ids(db, default_season_id(db))}


def visible_at(scan: WristbandScan, rules: dict[str, set[int]]) -> list[str]:
    """The counters where this scan waits; only a "new" scan waits anywhere. A
    scan without a matched team passes every rule (see waiting_scans)."""
    if scan.status != "new":
        return []
    return [counter for counter, team_ids in rules.items() if scan.team_id is None or scan.team_id in team_ids]
