# "Leveringsvolgorde": the order of the delivery tour across the ground.
# Every active delivery location either has a position in the tour
# (KarTracker_afleverlocaties.terrein_positie = 1, 2, 3, ...) or none yet
# (NULL). The screen sends the whole tour at once; this file renumbers it.
# Inactive locations are never shown here and keep whatever they had.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_zone import KarTrackerZone
from app.schemas.kartracker import DeliveryOrderLocationResponse


class DeliveryOrderError(ValueError):
    """A tour that can't be saved (duplicate, unknown or inactive location)."""


def list_delivery_order(db: Session) -> list[DeliveryOrderLocationResponse]:
    """Every active delivery location with its zone and distributiepunt name:
    first the ones in the tour (by position), then the rest (by name).
    """
    rows = db.execute(
        select(KarTrackerAfleverlocatie, KarTrackerZone.name, KarTrackerDistributiepunt.name)
        .join(KarTrackerZone, KarTrackerZone.id == KarTrackerAfleverlocatie.zone_id)
        .join(KarTrackerDistributiepunt, KarTrackerDistributiepunt.id == KarTrackerAfleverlocatie.distributiepunt_id)
        .where(KarTrackerAfleverlocatie.active.is_(True))
    ).all()

    locations = [
        DeliveryOrderLocationResponse(
            id=location.id,
            name=location.name,
            description=location.description,
            zone_name=zone_name,
            distributiepunt_name=distributiepunt_name,
            terrein_positie=location.terrein_positie,
            latitude=location.latitude,
            longitude=location.longitude,
        )
        for location, zone_name, distributiepunt_name in rows
    ]
    # Sorted in Python so NULLs go last the same way on Postgres and SQLite.
    locations.sort(
        key=lambda row: (row.terrein_positie is None, row.terrein_positie or 0, row.name.lower())
    )
    return locations


def save_delivery_order(db: Session, afleverlocatie_ids: list[int]) -> None:
    """Give the listed locations position 1..n in that order and take every
    other active location out of the tour. Doesn't commit — the router does.
    """
    if len(set(afleverlocatie_ids)) != len(afleverlocatie_ids):
        raise DeliveryOrderError("A delivery location appears more than once in the tour")

    # Lock the active locations so two people saving at once can't mix their tours.
    active_locations = {
        location.id: location
        for location in db.scalars(
            select(KarTrackerAfleverlocatie).where(KarTrackerAfleverlocatie.active.is_(True)).with_for_update()
        ).all()
    }
    unknown = [location_id for location_id in afleverlocatie_ids if location_id not in active_locations]
    if unknown:
        raise DeliveryOrderError("Unknown or inactive delivery location in the tour")

    # Everyone out first, then the tour back in, numbered from 1.
    for location in active_locations.values():
        location.terrein_positie = None
    for position, location_id in enumerate(afleverlocatie_ids, start=1):
        active_locations[location_id].terrein_positie = position
    db.flush()
