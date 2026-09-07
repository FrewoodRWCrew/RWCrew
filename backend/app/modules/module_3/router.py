# This is Intervention Requests' (module-3) own router file. It used to
# call the shared, generic create_module_router() factory (see
# app/modules/common.py) for a simple "does this user have access to
# module-3 at all" check; it now has its own custom-roles-with-per-screen-
# permissions system instead — the same one TagScan (module-1) and
# MasterData (module-9) already have (see
# docs/module-custom-roles-pattern.md) — so every endpoint below is gated
# per-screen, per-action via require_screen_permission() from deps.py.

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_requests_role import InterventionRequestsRole
from app.db.models.intervention_requests_role_permission import InterventionRequestsRolePermission
from app.db.models.intervention_requests_screen import InterventionRequestsScreen
from app.db.models.intervention_requests_user_role import InterventionRequestsUserRole
from app.db.models.intervention_status import InterventionStatus
from app.db.models.module import Module
from app.db.models.team import Team
from app.db.models.teamkar_member import TeamKarMember
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_3.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    user_can,
)
from app.modules.module_3.intervention_request_pdf import build_delivery_note_pdf
from app.modules.module_3.intervention_requests_dashboard import build_dashboard_stats
from app.modules.module_3.service import generate_request_number, list_teams_for_dropdown
from app.schemas.intervention_requests import (
    CreateOrGrantUserRequest,
    InterventionRequestCreateRequest,
    InterventionRequestResponse,
    InterventionRequestsDashboardResponse,
    InterventionRequestsTeamResponse,
    InterventionRequestsUserSummaryResponse,
    InterventionRequestUpdateRequest,
    InterventionStatusCreateRequest,
    InterventionStatusResponse,
    InterventionStatusUpdateRequest,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetTeamKarMembersRequest,
    SetUserRoleRequest,
    TeamKarMemberOptionResponse,
    TeamKarUserResponse,
)

router = APIRouter(prefix="/api/modules/module-3", tags=["Intervention Requests"])


def _content_disposition(filename: str) -> str:
    """A safe "Content-Disposition: attachment" header value for a
    filesystem-derived filename that's never been validated against HTTP
    header syntax — escapes `"`/`\\` so the name can't break out of the
    quoted-string form, and adds the RFC 5987 filename* fallback so a
    non-ASCII name still round-trips correctly in browsers that support it.
    (Same helper as app/modules/module_1/router.py's — kept local to this
    router rather than shared, matching how every other module-specific
    helper here stays self-contained.)
    """
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace("\\", "_").replace('"', "_")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


# --- Screens, Roles, Users (access-rights screens) ------------------------


def _build_role_response(db: Session, role: InterventionRequestsRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(InterventionRequestsScreen).order_by(InterventionRequestsScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(InterventionRequestsRolePermission).where(InterventionRequestsRolePermission.role_id == role.id)
        )
    }

    permission_rows = []
    for screen in screens:
        # If this role has never had its permissions set for this screen,
        # treat every action as "not allowed" rather than erroring out.
        permission = permissions_by_screen_id.get(screen.id)
        permission_rows.append(
            ScreenPermissionResponse(
                screen_id=screen.id,
                screen_key=screen.key,
                screen_label=screen.label,
                can_view=permission.can_view if permission else False,
                can_create=permission.can_create if permission else False,
                can_edit=permission.can_edit if permission else False,
                can_delete=permission.can_delete if permission else False,
            )
        )

    return RoleResponse(id=role.id, name=role.name, permissions=permission_rows)


@router.get("/screens", response_model=list[ScreenResponse])
def list_screens(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.roles", "view")),
) -> list[InterventionRequestsScreen]:
    """List every registered Intervention Requests screen — used to build
    the columns of the permission-matrix grid in the UI.
    """
    return list(db.scalars(select(InterventionRequestsScreen).order_by(InterventionRequestsScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.roles", "view")),
) -> list[RoleResponse]:
    """List every Intervention Requests role, each with its full permission matrix."""
    roles = db.scalars(select(InterventionRequestsRole).order_by(InterventionRequestsRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = InterventionRequestsRole(name=payload.name)
    db.add(new_role)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A role with this name already exists") from error

    db.refresh(new_role)
    return _build_role_response(db, new_role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
def rename_role(
    role_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(InterventionRequestsRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    role.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A role with this name already exists") from error

    db.refresh(role)
    return _build_role_response(db, role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(InterventionRequestsRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(
        select(InterventionRequestsUserRole).where(InterventionRequestsUserRole.role_id == role_id)
    )
    if still_assigned is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This role is still assigned to at least one user"
        )

    db.delete(role)
    db.commit()


@router.put("/roles/{role_id}/permissions", response_model=RoleResponse)
def set_role_permissions(
    role_id: int,
    payload: SetRolePermissionsRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(InterventionRequestsRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(InterventionRequestsRolePermission).where(InterventionRequestsRolePermission.role_id == role_id)
        )
    }

    for item in payload.permissions:
        existing = existing_permissions.get(item.screen_id)
        if existing is not None:
            existing.can_view = item.can_view
            existing.can_create = item.can_create
            existing.can_edit = item.can_edit
            existing.can_delete = item.can_delete
        else:
            db.add(
                InterventionRequestsRolePermission(
                    role_id=role_id,
                    screen_id=item.screen_id,
                    can_view=item.can_view,
                    can_create=item.can_create,
                    can_edit=item.can_edit,
                    can_delete=item.can_delete,
                )
            )

    db.commit()
    return _build_role_response(db, role)


def _build_user_summary(db: Session, user: User) -> InterventionRequestsUserSummaryResponse:
    user_role = get_user_role(db, user.id)
    role = db.get(InterventionRequestsRole, user_role.role_id) if user_role else None
    return InterventionRequestsUserSummaryResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id if role else None,
        role_name=role.name if role else None,
    )


@router.get("/users", response_model=list[InterventionRequestsUserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.users", "view")),
) -> list[InterventionRequestsUserSummaryResponse]:
    """List every user with access to Intervention Requests, and their current role."""
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    users_with_access = db.scalars(
        select(User)
        .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
        .where(UserModuleAccess.module_id == module.id)
        .order_by(User.display_name)
    ).all()
    return [_build_user_summary(db, user) for user in users_with_access]


@router.put("/users/{user_id}/role", response_model=InterventionRequestsUserSummaryResponse)
def set_user_role(
    user_id: int,
    payload: SetUserRoleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.users", "edit")),
) -> InterventionRequestsUserSummaryResponse:
    """Assign (or, if role_id is null, remove) an Intervention Requests
    role for a user who already has access to Intervention Requests.
    """
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(UserModuleAccess.user_id == user_id, UserModuleAccess.module_id == module.id)
    )
    if has_access is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to Intervention Requests"
        )

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(InterventionRequestsRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(InterventionRequestsUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=InterventionRequestsUserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.users", "create")),
) -> InterventionRequestsUserSummaryResponse:
    """Give someone access to Intervention Requests, creating their account
    first if they don't already have one anywhere in RW Crew.

    This ALWAYS grants access to Intervention Requests only — never any
    other module — regardless of who calls it, which is what keeps an
    Intervention Requests admin (not just the super admin) safely able to
    onboard people on their own.
    """
    target_user = db.scalar(select(User).where(User.email == payload.email))

    if target_user is None:
        if not payload.display_name or not payload.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A name and password are required to create a new user",
            )
        target_user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            display_name=payload.display_name,
        )
        db.add(target_user)
        try:
            db.flush()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists"
            ) from error

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(
            UserModuleAccess.user_id == target_user.id, UserModuleAccess.module_id == module.id
        )
    )
    if has_access is None:
        db.add(UserModuleAccess(user_id=target_user.id, module_id=module.id))

    if payload.role_id is not None:
        role = db.get(InterventionRequestsRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(InterventionRequestsUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/dashboard", response_model=InterventionRequestsDashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> InterventionRequestsDashboardResponse:
    """Aggregate KPI stats for the module's landing page — gated only by
    plain module access, the same unconditional treatment TagScan's and
    MasterData's own dashboards get, since this is "always-visible landing
    content" rather than a specific, permission-gated screen.
    """
    return build_dashboard_stats(db)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which Intervention Requests screens the current
    user can view, so it knows what to show in the sidebar without
    duplicating the permission-checking rules itself.
    """
    screens = db.scalars(select(InterventionRequestsScreen)).all()
    viewable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "view")]
    return MyPermissionsResponse(viewable_screen_keys=viewable_keys)


# --- TeamKar (module-3's fixed-group masterdata screen) -------------------


def _build_teamkar_users(db: Session) -> list[TeamKarUserResponse]:
    """List EVERY user in the whole app (not just users with module-3
    access), each flagged with whether they're currently a TeamKar member.
    Reads Landing_users directly, the same way the super admin's "Manage
    Access" screen does (see app/landing/admin.py's list_users) — just
    gated by this module's own screen permission instead of super-admin.
    """
    member_user_ids = set(db.scalars(select(TeamKarMember.user_id)).all())
    users = db.scalars(select(User).order_by(User.display_name)).all()
    return [
        TeamKarUserResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_member=user.id in member_user_ids,
        )
        for user in users
    ]


@router.get("/teamkar/users", response_model=list[TeamKarUserResponse])
def list_teamkar_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.teamkar", "view")),
) -> list[TeamKarUserResponse]:
    """List every app user with their current TeamKar membership, for the
    TeamKar screen's table.
    """
    return _build_teamkar_users(db)


@router.put("/teamkar/users", response_model=list[TeamKarUserResponse])
def set_teamkar_members(
    payload: SetTeamKarMembersRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.teamkar", "edit")),
) -> list[TeamKarUserResponse]:
    """Replace TeamKar's entire membership with exactly the given user ids
    — the same "send everything" replace-all pattern as
    set_user_module_access (app/landing/admin.py).
    """
    unique_user_ids = set(payload.user_ids)
    if unique_user_ids:
        valid_count = db.scalar(select(func.count()).select_from(User).where(User.id.in_(unique_user_ids)))
        if valid_count != len(unique_user_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more user ids are unknown")

    db.execute(delete(TeamKarMember))
    db.flush()
    for user_id in unique_user_ids:
        db.add(TeamKarMember(user_id=user_id))

    db.commit()
    return _build_teamkar_users(db)


# --- Intervention Statuses (module-3's "MasterData" lookup screen) -------


@router.get("/intervention-statuses", response_model=list[InterventionStatusResponse])
def list_intervention_statuses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.statuses", "view")),
) -> list[InterventionStatus]:
    """List every status, for the Intervention Statuses screen's table."""
    return list(db.scalars(select(InterventionStatus).order_by(InterventionStatus.name)).all())


@router.post("/intervention-statuses", response_model=InterventionStatusResponse, status_code=status.HTTP_201_CREATED)
def create_intervention_status(
    payload: InterventionStatusCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.statuses", "create")),
) -> InterventionStatus:
    """Create a brand-new status."""
    new_status = InterventionStatus(name=payload.name, is_open=payload.is_open, color=payload.color)
    db.add(new_status)
    db.commit()
    db.refresh(new_status)
    return new_status


@router.put("/intervention-statuses/{status_id}", response_model=InterventionStatusResponse)
def update_intervention_status(
    status_id: int,
    payload: InterventionStatusUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.statuses", "edit")),
) -> InterventionStatus:
    """Update an existing status."""
    existing_status = db.get(InterventionStatus, status_id)
    if existing_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")

    existing_status.name = payload.name
    existing_status.is_open = payload.is_open
    existing_status.color = payload.color
    db.commit()
    db.refresh(existing_status)
    return existing_status


@router.delete("/intervention-statuses/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intervention_status(
    status_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.statuses", "delete")),
) -> None:
    """Delete a status."""
    existing_status = db.get(InterventionStatus, status_id)
    if existing_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")

    referenced_request = db.scalar(
        select(InterventionRequest.id).where(InterventionRequest.status_id == status_id)
    )
    if referenced_request is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This status is still assigned to at least one intervention request",
        )

    db.delete(existing_status)
    db.commit()


# --- Intervention Requests (module-3's "Actions" screen) -----------------


@router.get("/teams", response_model=list[InterventionRequestsTeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.requests", "view")),
) -> list[Team]:
    """List every MasterData team, for the "Ploeg" dropdown on the
    Intervention Requests screen. Reads MasterData_team directly and is
    gated only by Intervention Requests' own "requests" screen permission
    — not MasterData's "masterdata.teams" one — so a user can always pick
    a team here regardless of whether they also have a MasterData role.
    """
    return list_teams_for_dropdown(db)


@router.get("/teamkar/options", response_model=list[TeamKarMemberOptionResponse])
def list_teamkar_options(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.requests", "view")),
) -> list[TeamKarMemberOptionResponse]:
    """List current TeamKar members, for the "Team Kar" dropdown on the
    Intervention Requests screen. Gated only by Intervention Requests' own
    "requests" screen permission — not TeamKar's own admin permission —
    exactly like "teams" above, so a user can always pick a Team Kar member
    here regardless of whether they also have the TeamKar screen's permission.
    """
    members = db.execute(
        select(User.id, User.display_name)
        .join(TeamKarMember, TeamKarMember.user_id == User.id)
        .order_by(User.display_name)
    ).all()
    return [TeamKarMemberOptionResponse(id=row.id, display_name=row.display_name) for row in members]


@router.get("/intervention-requests", response_model=list[InterventionRequestResponse])
def list_intervention_requests(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.requests", "view")),
) -> list[InterventionRequest]:
    """List every intervention request, newest first."""
    return list(
        db.scalars(select(InterventionRequest).order_by(InterventionRequest.submitted_at.desc())).all()
    )


@router.post(
    "/intervention-requests", response_model=InterventionRequestResponse, status_code=status.HTTP_201_CREATED
)
def create_intervention_request(
    payload: InterventionRequestCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.requests", "create")),
) -> InterventionRequest:
    """Create a brand-new intervention request. request_number and
    submitted_at are computed here, never accepted from the client.
    """
    if db.get(InterventionStatus, payload.status_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    if payload.team_id is not None and db.get(Team, payload.team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if payload.team_cart_user_id is not None:
        is_member = db.scalar(select(TeamKarMember).where(TeamKarMember.user_id == payload.team_cart_user_id))
        if is_member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team Kar user not found")

    new_request = InterventionRequest(
        request_number=generate_request_number(db),
        **payload.model_dump(),
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request


@router.put("/intervention-requests/{request_id}", response_model=InterventionRequestResponse)
def update_intervention_request(
    request_id: int,
    payload: InterventionRequestUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.requests", "edit")),
) -> InterventionRequest:
    """Update every editable field of an existing intervention request
    (request_number/submitted_at stay fixed once set).
    """
    existing_request = db.get(InterventionRequest, request_id)
    if existing_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention request not found")

    if db.get(InterventionStatus, payload.status_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    if payload.team_id is not None and db.get(Team, payload.team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if payload.team_cart_user_id is not None:
        is_member = db.scalar(select(TeamKarMember).where(TeamKarMember.user_id == payload.team_cart_user_id))
        if is_member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team Kar user not found")

    for field, value in payload.model_dump().items():
        setattr(existing_request, field, value)

    db.commit()
    db.refresh(existing_request)
    return existing_request


@router.delete("/intervention-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intervention_request(
    request_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.requests", "delete")),
) -> None:
    """Delete an intervention request."""
    existing_request = db.get(InterventionRequest, request_id)
    if existing_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention request not found")

    db.delete(existing_request)
    db.commit()


@router.get("/intervention-requests/{request_id}/pdf")
def download_intervention_request_pdf(
    request_id: int,
    locale: str = "nl",
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("interventionrequests.requests", "view")),
) -> Response:
    """A printable delivery-note PDF for one intervention request — see
    intervention_request_pdf.build_delivery_note_pdf.
    """
    existing_request = db.get(InterventionRequest, request_id)
    if existing_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention request not found")

    team = db.get(Team, existing_request.team_id) if existing_request.team_id is not None else None
    team_name = team.name if team else (existing_request.team_name or "")
    pdf_bytes = build_delivery_note_pdf(existing_request, team_name=team_name, locale=locale)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(f"{existing_request.request_number}.pdf")},
    )
