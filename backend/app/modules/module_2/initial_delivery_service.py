# "Initiële leverplanning" (Planningsanalyses group): which karren have to be
# delivered where at the start of the season, grouped per distributiepunt and
# within it per delivery location, in the order of the delivery tour
# (KarTracker_afleverlocaties.terrein_positie, set on "Leveringsvolgorde").
#
# A kar's initial location is the afleverlocatie planned ("Plan a kar") for
# its team at the team's first festival of the season: the earliest of the
# festivals it picked in Altsien Select or, while it picked none, the earliest
# active festival of the season (same rule as plan_kar_service.festivals_for_team).
# Karren without a team, or whose team planned nothing there, are left out.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.product import Product
from app.db.models.team import Team
from app.modules.module_2.plan_kar_service import festivals_by_team
from app.schemas.kartracker import (
    InitialDeliveryDistributiepuntGroup,
    InitialDeliveryKarRow,
    InitialDeliveryLocationGroup,
    InitialDeliveryResponse,
)


def build_initial_delivery(db: Session, season_id: int) -> InitialDeliveryResponse:
    """Per distributiepunt, every delivery location under it that receives
    karren at the start, in tour order (locations without a position last, by
    name), with its karren (by kar number). Distributiepunten follow the tour
    too: ordered by their first location. Plus the overall total.
    """
    # The season's active festivals (calendar order) and each team's picks.
    festivals, per_team = festivals_by_team(db, season_id)
    if not festivals:
        return InitialDeliveryResponse(distributiepunten=[], total=0)
    season_first = festivals[0]

    def first_festival(team_id: int) -> Festival:
        """The team's first festival: its earliest pick, else the season's first."""
        picked = per_team.get(team_id)
        return picked[0] if picked else season_first

    # Every location planned this season, keyed by (team, festival).
    planned: dict[tuple[int, int], int] = {
        (plan.team_id, plan.festival_id): plan.afleverlocatie_id
        for plan in db.scalars(
            select(KarTrackerKarAfleverlocatie).where(KarTrackerKarAfleverlocatie.season_id == season_id)
        ).all()
    }

    # The delivery date of each festival, where "Leverdata" has one.
    delivery_dates = {
        row.festival_id: row.delivery_date
        for row in db.scalars(
            select(KarTrackerLeverdatum).where(
                KarTrackerLeverdatum.festival_id.in_([festival.id for festival in festivals])
            )
        ).all()
    }

    # Every kar with a team, with the names shown on screen.
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
        .order_by(KarTrackerKar.kar_nummer)
    ).all()

    # Put each kar under the location planned for its team's first festival.
    karren_by_location: dict[int, list[InitialDeliveryKarRow]] = {}
    for kar in kar_rows:
        festival = first_festival(kar.team_id)
        location_id = planned.get((kar.team_id, festival.id))
        if location_id is None:
            continue
        karren_by_location.setdefault(location_id, []).append(
            InitialDeliveryKarRow(
                id=kar.id,
                kar_nummer=kar.kar_nummer,
                team_name=kar.team_name,
                transport_type_name=kar.transport_type_name,
                status_name=kar.status_name,
                festival_name=festival.name,
                delivery_date=delivery_dates.get(festival.id),
            )
        )

    # The locations that receive karren, with their zone and distributiepunt.
    location_rows = db.execute(
        select(KarTrackerAfleverlocatie, KarTrackerZone.name, KarTrackerDistributiepunt)
        .join(KarTrackerZone, KarTrackerZone.id == KarTrackerAfleverlocatie.zone_id)
        .join(KarTrackerDistributiepunt, KarTrackerDistributiepunt.id == KarTrackerAfleverlocatie.distributiepunt_id)
        .where(KarTrackerAfleverlocatie.id.in_(list(karren_by_location)))
    ).all()
    # Tour order, sorted in Python so NULLs go last the same way on Postgres
    # and SQLite (same ordering as the Leveringsvolgorde screen).
    location_rows = sorted(
        location_rows,
        key=lambda row: (row[0].terrein_positie is None, row[0].terrein_positie or 0, row[0].name.lower()),
    )

    # Walk the locations in tour order: a distributiepunt's group is created
    # at its first location, so the groups come out in tour order as well.
    groups: dict[int, InitialDeliveryDistributiepuntGroup] = {}
    for location, zone_name, distributiepunt in location_rows:
        group = groups.get(distributiepunt.id)
        if group is None:
            group = groups[distributiepunt.id] = InitialDeliveryDistributiepuntGroup(
                id=distributiepunt.id,
                name=distributiepunt.name,
                count=0,
                latitude=distributiepunt.latitude,
                longitude=distributiepunt.longitude,
                locations=[],
            )
        karren = karren_by_location[location.id]
        group.locations.append(
            InitialDeliveryLocationGroup(
                id=location.id,
                name=location.name,
                description=location.description,
                zone_name=zone_name,
                terrein_positie=location.terrein_positie,
                active=location.active,
                latitude=location.latitude,
                longitude=location.longitude,
                karren=karren,
            )
        )
        group.count += len(karren)

    return InitialDeliveryResponse(
        distributiepunten=list(groups.values()),
        total=sum(group.count for group in groups.values()),
    )
