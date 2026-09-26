# The phone's slice of Intervention Requests (module-3): only the "KPI
# overzicht" and the "Akties" (requests) screen. MasterData (statuses,
# TeamKar) and Access Rights (roles, users) are deliberately NOT here, and
# neither are deleting a request or its PDF — those stay web-only.
#
# Every endpoint reuses module-3's own permission checks (app/modules/
# module_3/deps.py), so a user can do exactly what their web role allows.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_status import InterventionStatus
from app.db.models.team import Team
from app.db.models.teamkar_member import TeamKarMember
from app.db.models.user import User
from app.mobile.schemas import MobileModule3LookupsResponse, MobileModule3PermissionsResponse
from app.mobile.version_gate import require_supported_app_version
from app.modules.module_3.deps import require_module_access, require_screen_permission, user_can
from app.modules.module_3.intervention_requests_dashboard import build_dashboard_stats
from app.modules.module_3.service import generate_request_number, list_teams_for_dropdown
from app.schemas.intervention_requests import (
    InterventionRequestCreateRequest,
    InterventionRequestResponse,
    InterventionRequestsDashboardResponse,
    InterventionRequestsTeamResponse,
    InterventionRequestUpdateRequest,
    InterventionStatusResponse,
    TeamKarMemberOptionResponse,
)

# The one web screen ("Akties" > Interventieaanvragen) all of this maps to.
REQUESTS_SCREEN = "interventionrequests.requests"

router = APIRouter(
    prefix="/api/mobile/v1/module-3",
    tags=["mobile-module-3"],
    dependencies=[Depends(require_supported_app_version)],
)


def _list_teamkar_members(db: Session) -> list[TeamKarMemberOptionResponse]:
    """The current TeamKar members, for the "Team kar" dropdown."""
    rows = db.execute(
        select(User.id, User.display_name)
        .join(TeamKarMember, TeamKarMember.user_id == User.id)
        .order_by(User.display_name)
    ).all()
    return [TeamKarMemberOptionResponse(id=row.id, display_name=row.display_name) for row in rows]


def _validate_references(
    db: Session, payload: InterventionRequestCreateRequest | InterventionRequestUpdateRequest
) -> None:
    """Check the status / team / TeamKar member a request points to really
    exist (the same rules as the web create/update endpoints).
    """
    if db.get(InterventionStatus, payload.status_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    if payload.team_id is not None and db.get(Team, payload.team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if payload.team_cart_user_id is not None:
        is_member = db.scalar(select(TeamKarMember).where(TeamKarMember.user_id == payload.team_cart_user_id))
        if is_member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team Kar user not found")


@router.get("/permissions", response_model=MobileModule3PermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MobileModule3PermissionsResponse:
    """What this user may do on the requests screen (view / create / edit)."""
    return MobileModule3PermissionsResponse(
        can_view_requests=user_can(db, current_user, REQUESTS_SCREEN, "view"),
        can_create_requests=user_can(db, current_user, REQUESTS_SCREEN, "create"),
        can_edit_requests=user_can(db, current_user, REQUESTS_SCREEN, "edit"),
    )


@router.get("/dashboard", response_model=InterventionRequestsDashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> InterventionRequestsDashboardResponse:
    """The KPI overview numbers, gated only by module access like on the web."""
    return build_dashboard_stats(db)


@router.get("/lookups", response_model=MobileModule3LookupsResponse)
def get_lookups(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REQUESTS_SCREEN, "view")),
) -> MobileModule3LookupsResponse:
    """The statuses, teams and TeamKar members for the request form.

    Gated by the requests screen's own permission (not the MasterData
    "statuses" screen), so anyone who can see requests can always name and
    pick a status, exactly like the web's teams/TeamKar dropdown endpoints.
    """
    statuses = db.scalars(select(InterventionStatus).order_by(InterventionStatus.name)).all()
    return MobileModule3LookupsResponse(
        statuses=[InterventionStatusResponse.model_validate(item, from_attributes=True) for item in statuses],
        teams=[
            InterventionRequestsTeamResponse.model_validate(item, from_attributes=True)
            for item in list_teams_for_dropdown(db)
        ],
        teamkar_members=_list_teamkar_members(db),
    )


@router.get("/intervention-requests", response_model=list[InterventionRequestResponse])
def list_intervention_requests(
    open_only: bool = False,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REQUESTS_SCREEN, "view")),
) -> list[InterventionRequest]:
    """Every request, newest first; open_only=true keeps only requests
    whose status is an "open" one (the web screen's default filter).
    """
    statement = select(InterventionRequest).order_by(InterventionRequest.submitted_at.desc())
    if open_only:
        statement = statement.join(InterventionStatus, InterventionRequest.status_id == InterventionStatus.id).where(
            InterventionStatus.is_open
        )
    return list(db.scalars(statement).all())


@router.get("/intervention-requests/{request_id}", response_model=InterventionRequestResponse)
def get_intervention_request(
    request_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REQUESTS_SCREEN, "view")),
) -> InterventionRequest:
    """One request, for the phone's detail/edit screen."""
    existing_request = db.get(InterventionRequest, request_id)
    if existing_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention request not found")
    return existing_request


@router.post(
    "/intervention-requests", response_model=InterventionRequestResponse, status_code=status.HTTP_201_CREATED
)
def create_intervention_request(
    payload: InterventionRequestCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REQUESTS_SCREEN, "create")),
) -> InterventionRequest:
    """Create a request. Its number and timestamp are set here, never by the app."""
    _validate_references(db, payload)

    new_request = InterventionRequest(request_number=generate_request_number(db), **payload.model_dump())
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request


@router.put("/intervention-requests/{request_id}", response_model=InterventionRequestResponse)
def update_intervention_request(
    request_id: int,
    payload: InterventionRequestUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REQUESTS_SCREEN, "edit")),
) -> InterventionRequest:
    """Update every editable field (number and timestamp stay fixed)."""
    existing_request = db.get(InterventionRequest, request_id)
    if existing_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention request not found")

    _validate_references(db, payload)

    for field, value in payload.model_dump().items():
        setattr(existing_request, field, value)

    db.commit()
    db.refresh(existing_request)
    return existing_request
