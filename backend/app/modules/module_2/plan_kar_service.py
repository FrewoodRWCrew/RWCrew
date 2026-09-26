# Shared "Plan a kar" write logic: storing which afleverlocatie a team
# delivers to at each festival of a season (KarTracker_kar_afleverlocaties).
# Used by KarTracker's own "Plan a kar" screen (module_2/router.py) and by
# Altsien Select's Ploeg Wizard (module_8/router.py), so both screens always
# write the exact same rows in the exact same way.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie


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
