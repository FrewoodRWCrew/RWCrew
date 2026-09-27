# The phone's slice of KarTracker (module-2), the screens of the web's
# "Acties" group that make sense in the field:
# - "KarScan", a light version of the web's "Manuele kar beweging": the
#   deliverer scans the QR code on a kar (it holds the kar number), picks
#   the kar's new status, and the phone's GPS position is logged with it.
# - "Kar Planning", read-only (its PDF "Print" stays web-only).
# - "Kar Map", read-only, with the ground plans overlaid.
# Kar Management, MasterData, Access Rights and deleting a logged movement
# stay web-only.
#
# Every endpoint reuses module-2's own permission checks (app/modules/
# module_2/deps.py) on the matching web screen, so a user can do exactly
# what their web role allows there. The data comes from the same services
# as the web screens (kar_action_service.py, kar_report_service.py).

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.user import User
from app.mobile.schemas import MobileKarScanResponse, MobileModule2PermissionsResponse, MobileSeasonResponse
from app.mobile.version_gate import require_supported_app_version
from app.modules.module_2.deps import require_module_access, require_screen_permission, user_can
from app.modules.module_2.kar_action_service import list_kar_actions, log_kar_action
from app.modules.module_2.kar_report_service import (
    build_kar_map,
    build_kar_planning_report,
    get_groundplan_or_404,
    list_groundplans,
)
from app.schemas.kartracker import (
    KarActionCreateRequest,
    KarActionKarOption,
    KarActionResponse,
    KarMapResponse,
    KarPlanningReportResponse,
    KarTrackerGroundplanResponse,
    PlanKarOption,
)

# The web screens all of this maps to.
ACTIONS_SCREEN = "kartracker.actions"  # "Manuele kar beweging" (KarScan)
KARPLANNING_SCREEN = "kartracker.karplanning"
KARMAP_SCREEN = "kartracker.karmap"

# How many earlier movements of the scanned kar the phone shows.
RECENT_ACTIONS_LIMIT = 5

router = APIRouter(
    prefix="/api/mobile/v1/module-2",
    tags=["mobile-module-2"],
    dependencies=[Depends(require_supported_app_version)],
)


@router.get("/permissions", response_model=MobileModule2PermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MobileModule2PermissionsResponse:
    """What this user may do in the phone's KarTracker, so the app only
    shows the menu items and buttons the web roles allow.
    """
    return MobileModule2PermissionsResponse(
        can_view_actions=user_can(db, current_user, ACTIONS_SCREEN, "view"),
        can_create_actions=user_can(db, current_user, ACTIONS_SCREEN, "create"),
        can_view_karplanning=user_can(db, current_user, KARPLANNING_SCREEN, "view"),
        can_view_karmap=user_can(db, current_user, KARMAP_SCREEN, "view"),
    )


@router.get("/kar-statuses", response_model=list[PlanKarOption])
def list_kar_statuses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ACTIONS_SCREEN, "view")),
) -> list[PlanKarOption]:
    """The status dropdown, gated by the movement screen itself (like the
    web's /kar-actions/lookups) so no KarStatussen rights are needed.
    """
    rows = db.execute(
        select(KarTrackerKarStatus.id, KarTrackerKarStatus.name).order_by(KarTrackerKarStatus.name)
    ).all()
    return [PlanKarOption(id=row.id, name=row.name) for row in rows]


@router.get("/karren/by-nummer/{kar_nummer}", response_model=MobileKarScanResponse)
def get_kar_by_nummer(
    kar_nummer: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ACTIONS_SCREEN, "view")),
) -> MobileKarScanResponse:
    """The kar whose QR code was scanned, plus its last few movements.

    The scanned text is trimmed and matched case-insensitively, so a QR code
    printed as "b001 " still finds kar "B001".
    """
    wanted = kar_nummer.strip().lower()
    row = db.execute(
        select(KarTrackerKar.id, KarTrackerKar.kar_nummer, KarTrackerKar.team_id, Team.name, KarTrackerKar.status_id)
        .outerjoin(Team, Team.id == KarTrackerKar.team_id)
        .where(func.lower(KarTrackerKar.kar_nummer) == wanted)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kar not found")

    return MobileKarScanResponse(
        kar=KarActionKarOption(
            id=row.id, kar_nummer=row.kar_nummer, team_id=row.team_id, team_name=row.name, status_id=row.status_id
        ),
        recent_actions=list_kar_actions(db, row.id, RECENT_ACTIONS_LIMIT),
    )


@router.post("/kar-actions", response_model=KarActionResponse, status_code=status.HTTP_201_CREATED)
def create_kar_action(
    payload: KarActionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(ACTIONS_SCREEN, "create")),
) -> KarActionResponse:
    """Log one kar movement, exactly like the web's Save button: the team and
    timestamp are set here, and the kar's latest status/location follow.
    """
    return log_kar_action(db, payload, current_user)


# ---- Kar Planning ------------------------------------------------------------


@router.get("/seasons", response_model=list[MobileSeasonResponse])
def list_open_seasons(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KARPLANNING_SCREEN, "view")),
) -> list[MobileSeasonResponse]:
    """The open seasons (the same ones the web header's season selector
    offers), newest first, for the Kar Planning season dropdown.
    """
    seasons = db.scalars(select(Season).where(Season.periode_open.is_(True)).order_by(Season.name.desc())).all()
    return [MobileSeasonResponse(id=season.id, name=season.name) for season in seasons]


@router.get("/kar-planning", response_model=KarPlanningReportResponse)
def get_kar_planning(
    season_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KARPLANNING_SCREEN, "view")),
) -> KarPlanningReportResponse:
    """The Kar Planning report, identical to the web's; with a season, one
    planned afleverlocatie per active festival of it.
    """
    return build_kar_planning_report(db, season_id)


# ---- Kar Map -----------------------------------------------------------------


@router.get("/kar-map", response_model=KarMapResponse)
def get_kar_map(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KARMAP_SCREEN, "view")),
) -> KarMapResponse:
    """Every kar, afleverlocatie and distributiepunt for the map, identical
    to the web's Kar Map data (rows without coordinates included).
    """
    return build_kar_map(db)


@router.get("/groundplans", response_model=list[KarTrackerGroundplanResponse])
def get_groundplans(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KARMAP_SCREEN, "view")),
) -> list[KarTrackerGroundplan]:
    """The ground plans overlaid on the Kar Map: name and corner coordinates."""
    return list_groundplans(db)


@router.get("/groundplans/{groundplan_id}/image")
def get_groundplan_image(
    groundplan_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KARMAP_SCREEN, "view")),
) -> Response:
    """One ground plan's image bytes (PNG or JPEG)."""
    groundplan = get_groundplan_or_404(db, groundplan_id)
    return Response(content=groundplan.image_data, media_type=groundplan.image_content_type)
