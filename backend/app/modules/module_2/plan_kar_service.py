# Shared "Plan a kar" write logic: storing which afleverlocatie a team
# delivers to at each festival of a season (KarTracker_kar_afleverlocaties).
# Used by KarTracker's own "Plan a kar" screen (module_2/router.py) and by
# Altsien Select's Ploeg Wizard (module_8/router.py), so both screens always
# write the exact same rows in the exact same way. Also decides which
# festivals a team has to plan (its own ones, see festivals_for_team).

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.team_festival import TeamFestival


def festivals_by_team(db: Session, season_id: int) -> tuple[list[Festival], dict[int, list[Festival]]]:
    """All active festivals of the season (in calendar order), plus per team
    the active festivals it picked in Altsien Select (MasterData_team_festival).
    Teams that picked none are simply missing from the dict.
    """
    festivals = list(
        db.scalars(
            select(Festival)
            .where(Festival.season_id == season_id, Festival.active.is_(True))
            .order_by(Festival.start_date, Festival.name)
        ).all()
    )
    active_ids = {festival.id for festival in festivals}

    # One query for every team's picks of this season; inactive festivals drop out.
    picked: dict[int, set[int]] = {}
    for team_id, festival_id in db.execute(
        select(TeamFestival.team_id, TeamFestival.festival_id).where(TeamFestival.season_id == season_id)
    ).all():
        if festival_id in active_ids:
            picked.setdefault(team_id, set()).add(festival_id)

    # Keep the calendar order of the full list.
    per_team = {
        team_id: [festival for festival in festivals if festival.id in ids] for team_id, ids in picked.items()
    }
    return festivals, per_team


def festivals_for_team(db: Session, season_id: int, team_id: int) -> tuple[list[Festival], bool]:
    """The festivals a team has to plan a delivery location for: the ones it
    picked in Altsien Select or, while it picked none yet, every active
    festival of the season. The flag says whether that fallback was used.
    """
    festivals, per_team = festivals_by_team(db, season_id)
    if team_id in per_team:
        return per_team[team_id], False
    return festivals, True


def upsert_plan_kar_rows(
    db: Session, season_id: int, team_id: int, rows: list[tuple[int, int | None]]
) -> None:
    """Apply (festival_id, afleverlocatie_id) pairs for one team in one
    season. Each pair is an upsert on (season, festival, team): an existing
    record is updated, a missing one inserted, and a pair with no location
    removes its record. Validation and the commit are left to the caller.
    """
    # Existing assignments for this team+season, keyed by festival.
    existing_by_festival = {
        record.festival_id: record
        for record in db.scalars(
            select(KarTrackerKarAfleverlocatie).where(
                KarTrackerKarAfleverlocatie.season_id == season_id,
                KarTrackerKarAfleverlocatie.team_id == team_id,
            )
        ).all()
    }

    for festival_id, afleverlocatie_id in rows:
        existing = existing_by_festival.get(festival_id)
        if afleverlocatie_id is None:
            # No location chosen: remove any earlier assignment.
            if existing is not None:
                db.delete(existing)
        elif existing is not None:
            # Already registered: update in place, never add a second line.
            existing.afleverlocatie_id = afleverlocatie_id
        else:
            db.add(
                KarTrackerKarAfleverlocatie(
                    season_id=season_id,
                    festival_id=festival_id,
                    team_id=team_id,
                    afleverlocatie_id=afleverlocatie_id,
                )
            )
