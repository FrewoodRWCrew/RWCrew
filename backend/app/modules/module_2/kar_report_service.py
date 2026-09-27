# Shared read-only KarTracker reports: the "Kar Planning" report, the "Kar
# Map" data and the ground plans overlaid on that map. Used by KarTracker's
# own web screens (module_2/router.py) and by the phone app's KarTracker
# (app/mobile/module_2_router.py), so both always show exactly the same data.

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.product import Product
from app.db.models.team import Team
from app.schemas.kartracker import (
    KarMapAfleverlocatieRow,
    KarMapDistributiepuntRow,
    KarMapKarRow,
    KarMapResponse,
    KarPlanningFestivalResponse,
    KarPlanningReportResponse,
    KarPlanningResponse,
)


def build_kar_planning_report(db: Session, season_id: int | None) -> KarPlanningReportResponse:
    """The read-only Kar Planning report: KarManagement joined with its
    status/team/transport-type lookups. Team is an outer join since a kar
    can be unassigned; status and transport type are required, so those
    stay inner joins.

    When `season_id` is given, every active festival of that season becomes
    an extra column carrying the afleverlocatie planned (via "Plan a kar")
    for the kar's team at that festival. Without it there are no festival
    columns.
    """
    rows = db.execute(
        select(
            KarTrackerKar.id,
            KarTrackerKar.kar_nummer,
            KarTrackerKar.team_id,
            KarTrackerKarStatus.name.label("status_name"),
            Team.name.label("team_name"),
            Product.name.label("transport_type_name"),
            KarTrackerKar.last_latitude,
            KarTrackerKar.last_longitude,
        )
        .join(KarTrackerKarStatus, KarTrackerKarStatus.id == KarTrackerKar.status_id)
        .outerjoin(Team, Team.id == KarTrackerKar.team_id)
        .join(Product, Product.id == KarTrackerKar.transport_type_id)
        .order_by(KarTrackerKar.kar_nummer)
    ).all()

    festivals: list[KarPlanningFestivalResponse] = []
    # (team_id, festival_id) -> name of the afleverlocatie planned there.
    planned_locations: dict[tuple[int, int], str] = {}
    if season_id is not None:
        # One column per active festival of the season, earliest first (the
        # same ordering "Plan a kar" uses).
        festival_rows = db.execute(
            select(Festival.id, Festival.name)
            .where(Festival.season_id == season_id, Festival.active.is_(True))
            .order_by(Festival.start_date, Festival.name)
        ).all()
        festivals = [KarPlanningFestivalResponse(id=row.id, name=row.name) for row in festival_rows]

        # Everything planned for that season, restricted to the columns above.
        # The location's name is shown even if it was deactivated since — the
        # plan still refers to it.
        for plan in db.execute(
            select(
                KarTrackerKarAfleverlocatie.team_id,
                KarTrackerKarAfleverlocatie.festival_id,
                KarTrackerAfleverlocatie.name,
                KarTrackerAfleverlocatie.description,
            )
            .join(
                KarTrackerAfleverlocatie,
                KarTrackerAfleverlocatie.id == KarTrackerKarAfleverlocatie.afleverlocatie_id,
            )
            .where(
                KarTrackerKarAfleverlocatie.season_id == season_id,
                KarTrackerKarAfleverlocatie.festival_id.in_([festival.id for festival in festivals]),
            )
        ):
            # Shown as "name — description" (just the name when there is no
            # description), the same label "Plan a kar" uses in its dropdown.
            planned_locations[(plan.team_id, plan.festival_id)] = (
                f"{plan.name} — {plan.description}" if plan.description else plan.name
            )

    return KarPlanningReportResponse(
        festivals=festivals,
        rows=[
            KarPlanningResponse(
                id=row.id,
                kar_nummer=row.kar_nummer,
                status_name=row.status_name,
                team_name=row.team_name,
                transport_type_name=row.transport_type_name,
                # A kar's locations come from its team; a kar without a team
                # has nothing planned.
                afleverlocaties={
                    festival.id: planned_locations[(row.team_id, festival.id)]
                    for festival in festivals
                    if (row.team_id, festival.id) in planned_locations
                },
                geolocation=(
                    f"{row.last_latitude}, {row.last_longitude}"
                    if row.last_latitude is not None and row.last_longitude is not None
                    else None
                ),
            )
            for row in rows
        ],
    )


def build_kar_map(db: Session) -> KarMapResponse:
    """The Kar Map screen's data: every Kar/Afleverlocatie/Distributiepunt
    row, denormalized with the lookup names needed for each pin's popup.
    Rows with no latitude/longitude are included too — the client excludes
    them from the map itself but still lists them.
    """
    kar_rows = db.execute(
        select(
            KarTrackerKar.id,
            KarTrackerKar.kar_nummer,
            KarTrackerKarStatus.name.label("status_name"),
            Team.name.label("team_name"),
            KarTrackerKar.last_latitude,
            KarTrackerKar.last_longitude,
        )
        .join(KarTrackerKarStatus, KarTrackerKarStatus.id == KarTrackerKar.status_id)
        .outerjoin(Team, Team.id == KarTrackerKar.team_id)
        .order_by(KarTrackerKar.kar_nummer)
    ).all()

    afleverlocatie_rows = db.execute(
        select(
            KarTrackerAfleverlocatie.id,
            KarTrackerAfleverlocatie.name,
            KarTrackerAfleverlocatie.description,
            KarTrackerZone.name.label("zone_name"),
            KarTrackerDistributiepunt.name.label("distributiepunt_name"),
            KarTrackerAfleverlocatie.latitude,
            KarTrackerAfleverlocatie.longitude,
        )
        .join(KarTrackerZone, KarTrackerZone.id == KarTrackerAfleverlocatie.zone_id)
        .join(KarTrackerDistributiepunt, KarTrackerDistributiepunt.id == KarTrackerAfleverlocatie.distributiepunt_id)
        .order_by(KarTrackerAfleverlocatie.name)
    ).all()

    distributiepunt_rows = db.execute(
        select(
            KarTrackerDistributiepunt.id,
            KarTrackerDistributiepunt.name,
            KarTrackerDistributiepunt.terrein_positie,
            KarTrackerDistributiepunt.latitude,
            KarTrackerDistributiepunt.longitude,
        ).order_by(KarTrackerDistributiepunt.name)
    ).all()

    return KarMapResponse(
        karren=[
            KarMapKarRow(
                id=row.id,
                kar_nummer=row.kar_nummer,
                status_name=row.status_name,
                team_name=row.team_name,
                latitude=row.last_latitude,
                longitude=row.last_longitude,
            )
            for row in kar_rows
        ],
        afleverlocaties=[
            KarMapAfleverlocatieRow(
                id=row.id,
                name=row.name,
                description=row.description,
                zone_name=row.zone_name,
                distributiepunt_name=row.distributiepunt_name,
                latitude=row.latitude,
                longitude=row.longitude,
            )
            for row in afleverlocatie_rows
        ],
        distributiepunten=[
            KarMapDistributiepuntRow(
                id=row.id,
                name=row.name,
                terrein_positie=row.terrein_positie,
                latitude=row.latitude,
                longitude=row.longitude,
            )
            for row in distributiepunt_rows
        ],
    )


def list_groundplans(db: Session) -> list[KarTrackerGroundplan]:
    """Every ground plan's name and bounds, in name order."""
    return list(
        db.scalars(select(KarTrackerGroundplan).order_by(KarTrackerGroundplan.name, KarTrackerGroundplan.id)).all()
    )


def get_groundplan_or_404(db: Session, groundplan_id: int) -> KarTrackerGroundplan:
    """One ground plan, or a 404 when it doesn't exist."""
    groundplan = db.get(KarTrackerGroundplan, groundplan_id)
    if groundplan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ground plan not found")
    return groundplan
