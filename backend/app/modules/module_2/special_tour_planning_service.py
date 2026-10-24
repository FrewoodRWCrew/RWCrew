# "Speciale levertoeren-planning" (Planningsanalyses group): for a chosen
# festival and one or more special delivery tours (KarTracker "Speciale
# levertoeren", e.g. "Kleine wastoer", "Ijsblokken"), which karren the tour
# passes by and where they stand: the tour's stops = the delivery locations in
# the order of the delivery tour (terrein_positie from "Leveringsvolgorde"
# first, the rest by name), numbered 1..n, each with its karren. Unlike
# "Initiële leverplanning" there are no distributiepunten: the tour passes by
# the karren, nothing is picked up.
#
# A kar is listed when its team is linked to at least one selected tour (team
# fiche, MasterData_team_speciale_levertoer), the team takes part in the
# festival (its picks in Altsien Select or, while it picked none, every active
# festival of the season — same rule as plan_kar_service.festivals_for_team)
# and has a location planned there ("Plan a kar"). A kar on two selected
# tours is listed once, with both tour names.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_speciale_levertoer import KarTrackerSpecialeLevertoer
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.product import Product
from app.db.models.team import Team
from app.db.models.team_speciale_levertoer import TeamSpecialeLevertoer
from app.modules.module_2.plan_kar_service import festivals_by_team
from app.schemas.kartracker import (
    InitialDeliveryKarRow,
    KarMovesFestival,
    SpecialTourOption,
    SpecialTourPlanningResponse,
    SpecialTourStop,
)


class SpecialTourPlanningError(Exception):
    """A selection that can't be worked out; `code` says why:
    "unknown_festival" (not an active festival of the season) or
    "unknown_tour" (one of the tour ids doesn't exist).
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def build_special_tour_planning(
    db: Session, season_id: int, festival_id: int | None, tour_ids: list[int]
) -> SpecialTourPlanningResponse:
    """The season's festivals and the active tours (for the filters) and, when
    a festival and at least one tour are given, the tour's stops in tour order
    with the karren those tours pass by at that festival. Raises
    SpecialTourPlanningError for an unknown festival or tour.
    """
    # The season's active festivals (calendar order) and each team's picks.
    festivals, per_team = festivals_by_team(db, season_id)
    festival_options = [
        KarMovesFestival(id=festival.id, name=festival.name, start_date=festival.start_date)
        for festival in festivals
    ]

    # Every tour by id; only the active ones are offered in the filter.
    all_tours = {tour.id: tour for tour in db.scalars(select(KarTrackerSpecialeLevertoer)).all()}
    tour_options = sorted(
        (SpecialTourOption(id=tour.id, name=tour.name) for tour in all_tours.values() if tour.active),
        key=lambda option: option.name.lower(),
    )
    tour_ids = list(dict.fromkeys(tour_ids))

    def response(**overrides) -> SpecialTourPlanningResponse:
        """The response with the filter data, plus the given result fields."""
        values = {"delivery_date": None, "locations": [], "total": 0, **overrides}
        return SpecialTourPlanningResponse(
            festivals=festival_options, tours=tour_options, festival_id=festival_id, tour_ids=tour_ids, **values
        )

    # Without a festival or a tour there is nothing to show yet: only the filters.
    if festival_id is None or not tour_ids:
        return response()
    festival = next((item for item in festivals if item.id == festival_id), None)
    if festival is None:
        raise SpecialTourPlanningError("unknown_festival")
    if any(tour_id not in all_tours for tour_id in tour_ids):
        raise SpecialTourPlanningError("unknown_tour")

    # Per team, the names of the selected tours that pass by it (by name).
    tours_per_team: dict[int, list[str]] = {}
    for link in db.scalars(select(TeamSpecialeLevertoer).where(TeamSpecialeLevertoer.levertoer_id.in_(tour_ids))):
        tours_per_team.setdefault(link.team_id, []).append(all_tours[link.levertoer_id].name)
    for names in tours_per_team.values():
        names.sort(key=str.lower)

    def takes_part(team_id: int) -> bool:
        """Whether the team plays this festival (no picks = every festival)."""
        picked = per_team.get(team_id)
        return picked is None or any(item.id == festival_id for item in picked)

    # The location planned for each of those teams at the festival.
    planned: dict[int, int] = {
        plan.team_id: plan.afleverlocatie_id
        for plan in db.scalars(
            select(KarTrackerKarAfleverlocatie).where(
                KarTrackerKarAfleverlocatie.season_id == season_id,
                KarTrackerKarAfleverlocatie.festival_id == festival_id,
                KarTrackerKarAfleverlocatie.team_id.in_(list(tours_per_team)),
            )
        ).all()
        if takes_part(plan.team_id)
    }

    # The festival's delivery date, where "Leverdata" has one.
    delivery_date = db.scalar(
        select(KarTrackerLeverdatum.delivery_date).where(KarTrackerLeverdatum.festival_id == festival_id)
    )

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
        .where(KarTrackerKar.team_id.in_(list(planned)))
        .order_by(KarTrackerKar.kar_nummer)
    ).all()

    # Put each kar under its team's planned location.
    karren_by_location: dict[int, list[InitialDeliveryKarRow]] = {}
    for kar in kar_rows:
        karren_by_location.setdefault(planned[kar.team_id], []).append(
            InitialDeliveryKarRow(
                id=kar.id,
                kar_nummer=kar.kar_nummer,
                team_name=kar.team_name,
                transport_type_name=kar.transport_type_name,
                status_name=kar.status_name,
                festival_name=festival.name,
                delivery_date=delivery_date,
                tour_names=tours_per_team[kar.team_id],
            )
        )

    # The locations with karren, with their zone, in tour order (sorted in
    # Python so NULLs go last the same way on Postgres and SQLite), numbered 1..n.
    location_rows = sorted(
        db.execute(
            select(KarTrackerAfleverlocatie, KarTrackerZone.name)
            .join(KarTrackerZone, KarTrackerZone.id == KarTrackerAfleverlocatie.zone_id)
            .where(KarTrackerAfleverlocatie.id.in_(list(karren_by_location)))
        ).all(),
        key=lambda row: (row[0].terrein_positie is None, row[0].terrein_positie or 0, row[0].name.lower()),
    )
    stops = [
        SpecialTourStop(
            stop=number,
            id=location.id,
            name=location.name,
            description=location.description,
            zone_name=zone_name,
            terrein_positie=location.terrein_positie,
            active=location.active,
            latitude=location.latitude,
            longitude=location.longitude,
            karren=karren_by_location[location.id],
        )
        for number, (location, zone_name) in enumerate(location_rows, start=1)
    ]
    return response(
        delivery_date=delivery_date,
        locations=stops,
        total=sum(len(stop.karren) for stop in stops),
    )
