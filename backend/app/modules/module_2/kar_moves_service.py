# "Verplaatsingen tussen festivals" (Planningsanalyses group): for a chosen
# festival A ("Van") -> festival B ("Naar") of a season, which karren have to
# be moved on the ground because their team's planned delivery location
# ("Plan a kar", KarTracker_kar_afleverlocatie) differs between the two.
#
# A kar is listed when it has a team that takes part in both festivals (its
# picks in Altsien Select or, while it picked none, every active festival of
# the season — same rule as plan_kar_service.festivals_for_team), the team
# has a location planned at A *and* at B, and those two locations differ.
# The karren are grouped per pick-up location (the one at A) in the order of
# the delivery tour (KarTracker_afleverlocaties.terrein_positie, set on
# "Leveringsvolgorde"); each kar row says where it goes (the one at B).

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.product import Product
from app.db.models.team import Team
from app.modules.module_2.plan_kar_service import festivals_by_team
from app.schemas.kartracker import (
    KarMovesFestival,
    KarMovesKarRow,
    KarMovesLocation,
    KarMovesLocationGroup,
    KarMovesResponse,
)


class KarMovesError(Exception):
    """A festival pair that can't be compared; `code` says why:
    "unknown_festival" (not an active festival of the season) or
    "same_festival" (Van and Naar are the same).
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _tour_order(location: KarMovesLocation) -> tuple:
    """Tour order: positioned locations by position, then the rest by name.
    Sorted in Python so NULLs go last the same way on Postgres and SQLite.
    """
    return (location.terrein_positie is None, location.terrein_positie or 0, location.name.lower())


def build_kar_moves(
    db: Session, season_id: int, from_festival_id: int | None, to_festival_id: int | None
) -> KarMovesResponse:
    """The season's festivals and, when both festivals are given, the karren
    to move from A to B grouped per pick-up location in tour order (karren by
    kar number). Raises KarMovesError for a pair that can't be compared.
    """
    # The season's active festivals (calendar order) and each team's picks.
    festivals, per_team = festivals_by_team(db, season_id)
    festival_options = [
        KarMovesFestival(id=festival.id, name=festival.name, start_date=festival.start_date)
        for festival in festivals
    ]

    # Without a pair there is nothing to compare yet: only the dropdowns.
    if from_festival_id is None or to_festival_id is None:
        return KarMovesResponse(
            festivals=festival_options,
            from_festival_id=from_festival_id,
            to_festival_id=to_festival_id,
            to_delivery_date=None,
            locations=[],
            total=0,
        )
    active_ids = {festival.id for festival in festivals}
    if from_festival_id not in active_ids or to_festival_id not in active_ids:
        raise KarMovesError("unknown_festival")
    if from_festival_id == to_festival_id:
        raise KarMovesError("same_festival")

    def takes_part(team_id: int) -> bool:
        """Whether the team plays both festivals (no picks = every festival)."""
        picked = per_team.get(team_id)
        if picked is None:
            return True
        picked_ids = {festival.id for festival in picked}
        return from_festival_id in picked_ids and to_festival_id in picked_ids

    # The locations planned for each team at A and at B.
    planned_from: dict[int, int] = {}
    planned_to: dict[int, int] = {}
    for plan in db.scalars(
        select(KarTrackerKarAfleverlocatie).where(
            KarTrackerKarAfleverlocatie.season_id == season_id,
            KarTrackerKarAfleverlocatie.festival_id.in_([from_festival_id, to_festival_id]),
        )
    ).all():
        target = planned_from if plan.festival_id == from_festival_id else planned_to
        target[plan.team_id] = plan.afleverlocatie_id

    # The teams whose karren move: in both festivals, planned at both, different place.
    moves: dict[int, tuple[int, int]] = {
        team_id: (from_id, planned_to[team_id])
        for team_id, from_id in planned_from.items()
        if team_id in planned_to and planned_to[team_id] != from_id and takes_part(team_id)
    }

    # Every location involved (pick-up and destination), with its zone.
    location_ids = {location_id for pair in moves.values() for location_id in pair}
    locations = {
        location.id: KarMovesLocation(
            id=location.id,
            name=location.name,
            description=location.description,
            zone_name=zone_name,
            terrein_positie=location.terrein_positie,
            active=location.active,
            latitude=location.latitude,
            longitude=location.longitude,
        )
        for location, zone_name in db.execute(
            select(KarTrackerAfleverlocatie, KarTrackerZone.name)
            .join(KarTrackerZone, KarTrackerZone.id == KarTrackerAfleverlocatie.zone_id)
            .where(KarTrackerAfleverlocatie.id.in_(list(location_ids)))
        ).all()
    }

    # The karren of those teams, with the names shown on screen.
    kar_rows = db.execute(
        select(
            KarTrackerKar.id,
            KarTrackerKar.kar_nummer,
            KarTrackerKar.team_id,
            Team.name.label("team_name"),
            Product.name.label("transport_type_name"),
            KarTrackerKarStatus.name.label("status_name"),
        )
        .join(Team, Team.id == KarTrackerKar.team_id)
        .join(Product, Product.id == KarTrackerKar.transport_type_id)
        .join(KarTrackerKarStatus, KarTrackerKarStatus.id == KarTrackerKar.status_id)
        .where(KarTrackerKar.team_id.in_(list(moves)))
        .order_by(KarTrackerKar.kar_nummer)
    ).all()

    # Put each kar under its pick-up location, with its destination.
    karren_by_location: dict[int, list[KarMovesKarRow]] = {}
    for kar in kar_rows:
        from_id, to_id = moves[kar.team_id]
        karren_by_location.setdefault(from_id, []).append(
            KarMovesKarRow(
                id=kar.id,
                kar_nummer=kar.kar_nummer,
                team_name=kar.team_name,
                transport_type_name=kar.transport_type_name,
                status_name=kar.status_name,
                to_location=locations[to_id],
            )
        )

    # The pick-up locations in tour order.
    groups = [
        KarMovesLocationGroup(**locations[location_id].model_dump(), karren=karren)
        for location_id, karren in karren_by_location.items()
    ]
    groups.sort(key=_tour_order)

    # The delivery date of the "Naar" festival, where "Leverdata" has one.
    to_delivery_date = db.scalar(
        select(KarTrackerLeverdatum.delivery_date).where(KarTrackerLeverdatum.festival_id == to_festival_id)
    )

    return KarMovesResponse(
        festivals=festival_options,
        from_festival_id=from_festival_id,
        to_festival_id=to_festival_id,
        to_delivery_date=to_delivery_date,
        locations=groups,
        total=sum(len(group.karren) for group in groups),
    )
