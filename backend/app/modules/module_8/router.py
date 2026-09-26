# This is Altsien Select's (module-8) own router file. It used to call the
# shared, generic create_module_router() factory (see app/modules/common.py)
# for the "coming soon" placeholder; it now has its own custom-roles-with-
# per-screen-permissions system — the same one Intervention Requests
# (module-3) and KarTracker (module-2) have (see
# docs/module-custom-roles-pattern.md) — so every endpoint below is gated
# per-screen, per-action via require_screen_permission() from deps.py.
#
# The module itself is the "Ploeg Wizard": per team and per season, an
# Altsien Kernlid walks through a number of steps (see steps.py), and the
# result is shown on the "Ploegfiche" (screen + PDF). Only the progress of
# the steps and the special requests are stored in this module's own
# tables; the actual choices are written to the shared tables they belong
# to (MasterData_team_festival, KarTracker_kar_afleverlocaties, ...).

from datetime import datetime, timezone
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.altsien_select_request_status import AltsienSelectRequestStatus
from app.db.models.altsien_select_role import AltsienSelectRole
from app.db.models.altsien_select_role_permission import AltsienSelectRolePermission
from app.db.models.altsien_select_screen import AltsienSelectScreen
from app.db.models.altsien_select_special_request import AltsienSelectSpecialRequest
from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.altsien_select_user_role import AltsienSelectUserRole
from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.team_festival import TeamFestival
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_2.plan_kar_service import upsert_plan_kar_rows
from app.modules.module_8.dashboard import build_dashboard
from app.modules.module_8.deps import (
    MODULE_KEY,
    accessible_team_ids,
    ensure_season_editable,
    get_season_or_404,
    get_team_in_scope,
    get_user_role,
    require_module_access,
    require_screen_permission,
    season_is_editable_for,
    user_can,
)
from app.modules.module_8.ploegfiche_pdf import build_ploegfiche_pdf
from app.modules.module_8.service import (
    build_request_responses,
    build_team_state,
    build_team_summaries,
    clear_step,
    first_request_status,
    list_steps,
    selected_festivals_of,
)
from app.modules.module_8.steps import STEPS_BY_KEY, selected_festival_ids
from app.schemas.altsien_select import (
    CreateOrGrantUserRequest,
    DashboardResponse,
    MyPermissionsResponse,
    RequestStatusResponse,
    RequestStatusWriteRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    SaveAfleverlocatiesRequest,
    SaveFestivalsRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    SpecialRequestFollowUpRequest,
    SpecialRequestResponse,
    SpecialRequestWriteRequest,
    StepResponse,
    TeamStateResponse,
    TeamSummaryResponse,
    UserSummaryResponse,
)
from app.schemas.masterdata import SeasonResponse

router = APIRouter(prefix="/api/modules/module-8", tags=["Altsien Select"])

# The two "Akties" screens a Kernlid works in.
WIZARD_SCREEN = "altsienselect.wizard"
PLOEGFICHE_SCREEN = "altsienselect.ploegfiche"


def require_wizard_or_ploegfiche_view(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> User:
    """Lookups both Akties screens need (seasons, the team list) are
    allowed for whoever can view at least one of them.
    """
    if not (
        user_can(db, current_user, WIZARD_SCREEN, "view") or user_can(db, current_user, PLOEGFICHE_SCREEN, "view")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view the Ploeg Wizard")
    return current_user


# --- Screens, Roles, Users (access-rights screens) ------------------------


def _build_role_response(db: Session, role: AltsienSelectRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(AltsienSelectScreen).order_by(AltsienSelectScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(AltsienSelectRolePermission).where(AltsienSelectRolePermission.role_id == role.id)
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
    _user: User = Depends(require_screen_permission("altsienselect.roles", "view")),
) -> list[AltsienSelectScreen]:
    """List every registered Altsien Select screen — used to build
    the columns of the permission-matrix grid in the UI.
    """
    return list(db.scalars(select(AltsienSelectScreen).order_by(AltsienSelectScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.roles", "view")),
) -> list[RoleResponse]:
    """List every Altsien Select role, each with its full permission matrix."""
    roles = db.scalars(select(AltsienSelectRole).order_by(AltsienSelectRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = AltsienSelectRole(name=payload.name)
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
    _user: User = Depends(require_screen_permission("altsienselect.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(AltsienSelectRole, role_id)
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
    _user: User = Depends(require_screen_permission("altsienselect.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(AltsienSelectRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(
        select(AltsienSelectUserRole).where(AltsienSelectUserRole.role_id == role_id)
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
    _user: User = Depends(require_screen_permission("altsienselect.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(AltsienSelectRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(AltsienSelectRolePermission).where(AltsienSelectRolePermission.role_id == role_id)
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
                AltsienSelectRolePermission(
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


def _build_user_summary(db: Session, user: User) -> UserSummaryResponse:
    user_role = get_user_role(db, user.id)
    role = db.get(AltsienSelectRole, user_role.role_id) if user_role else None
    return UserSummaryResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id if role else None,
        role_name=role.name if role else None,
    )


@router.get("/users", response_model=list[UserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.users", "view")),
) -> list[UserSummaryResponse]:
    """List every user with access to Altsien Select, and their current role."""
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    users_with_access = db.scalars(
        select(User)
        .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
        .where(UserModuleAccess.module_id == module.id)
        .order_by(User.display_name)
    ).all()
    return [_build_user_summary(db, user) for user in users_with_access]


@router.put("/users/{user_id}/role", response_model=UserSummaryResponse)
def set_user_role(
    user_id: int,
    payload: SetUserRoleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.users", "edit")),
) -> UserSummaryResponse:
    """Assign (or, if role_id is null, remove) an Altsien Select
    role for a user who already has access to Altsien Select.
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to Altsien Select"
        )

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(AltsienSelectRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(AltsienSelectUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=UserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.users", "create")),
) -> UserSummaryResponse:
    """Give someone access to Altsien Select, creating their account
    first if they don't already have one anywhere in RW Crew.

    This ALWAYS grants access to Altsien Select only — never any
    other module — regardless of who calls it, which is what keeps an
    Altsien Select admin (not just the super admin) safely able to
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
        role = db.get(AltsienSelectRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(AltsienSelectUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which Altsien Select screens the current
    user can view, so it knows what to show in the sidebar without
    duplicating the permission-checking rules itself.
    """
    screens = db.scalars(select(AltsienSelectScreen)).all()
    viewable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "view")]
    return MyPermissionsResponse(viewable_screen_keys=viewable_keys)




@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    season_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> DashboardResponse:
    """The KPI screen (module landing page) for one season — gated only by
    plain module access, like every other module's dashboard. The figures
    only cover the teams the caller can see.
    """
    if season_id is not None:
        get_season_or_404(db, season_id)
    return build_dashboard(db, season_id, accessible_team_ids(db, current_user))


# --- Lookups shared by the Akties screens ---------------------------------


@router.get("/seasons", response_model=list[SeasonResponse])
def list_seasons(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[Season]:
    """Every season, newest name first — the module's own season dropdown
    (unlike the header's selector it also lists closed seasons, so earlier
    choices stay viewable on the Ploegfiche).
    """
    return list(db.scalars(select(Season).order_by(Season.name.desc())).all())


@router.get("/steps", response_model=list[StepResponse])
def get_steps(_user: User = Depends(require_module_access)) -> list[StepResponse]:
    """The wizard's steps, in order (see steps.py)."""
    return list_steps()


@router.get("/teams", response_model=list[TeamSummaryResponse])
def list_teams(
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_wizard_or_ploegfiche_view),
) -> list[TeamSummaryResponse]:
    """The teams the caller may open, each with its wizard progress."""
    get_season_or_404(db, season_id)
    return build_team_summaries(db, season_id, accessible_team_ids(db, current_user))


# --- Ploeg Wizard ---------------------------------------------------------


@router.get("/wizard/{team_id}", response_model=TeamStateResponse)
def get_wizard_state(
    team_id: int,
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "view")),
) -> TeamStateResponse:
    """Everything the wizard needs for one team in one season."""
    season = get_season_or_404(db, season_id)
    team = get_team_in_scope(db, current_user, team_id)
    return build_team_state(db, current_user, season, team)


def _load_for_change(db: Session, user: User, team_id: int, season_id: int):
    """Common checks before any wizard change: team in scope, season
    exists and is still open for this user.
    """
    season = get_season_or_404(db, season_id)
    team = get_team_in_scope(db, user, team_id)
    ensure_season_editable(db, user, season)
    return season, team


@router.put("/wizard/{team_id}/festivals", response_model=TeamStateResponse)
def save_festivals(
    team_id: int,
    payload: SaveFestivalsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "edit")),
) -> TeamStateResponse:
    """Step 1: replace the festivals the team is active at. A festival
    that is deselected also loses its Plan a kar delivery location.
    """
    season, team = _load_for_change(db, current_user, team_id, payload.season_id)

    wanted_ids = set(payload.festival_ids)
    current_links = {link.festival_id: link for link in selected_festivals_of(db, season.id, team.id)}

    # Newly added festivals must be active festivals of this season (ones
    # already linked may stay, even if they were deactivated since).
    added_ids = wanted_ids - set(current_links)
    if added_ids:
        valid_ids = set(
            db.scalars(
                select(Festival.id).where(
                    Festival.id.in_(added_ids), Festival.season_id == season.id, Festival.active.is_(True)
                )
            ).all()
        )
        if valid_ids != added_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Every festival must be an active festival of the season",
            )

    # Remove deselected festivals, and their delivery location with them.
    removed_ids = set(current_links) - wanted_ids
    for festival_id in removed_ids:
        db.delete(current_links[festival_id])
    if removed_ids:
        db.execute(
            delete(KarTrackerKarAfleverlocatie).where(
                KarTrackerKarAfleverlocatie.season_id == season.id,
                KarTrackerKarAfleverlocatie.team_id == team.id,
                KarTrackerKarAfleverlocatie.festival_id.in_(removed_ids),
            )
        )
    for festival_id in added_ids:
        db.add(TeamFestival(season_id=season.id, team_id=team.id, festival_id=festival_id))

    # A changed selection invalidates the steps built on top of it; the
    # user confirms them again in the wizard.
    if added_ids or removed_ids:
        clear_step(db, season.id, team.id, "afleverlocaties")
        if not wanted_ids:
            clear_step(db, season.id, team.id, "festivals")

    db.commit()
    return build_team_state(db, current_user, season, team)


@router.put("/wizard/{team_id}/afleverlocaties", response_model=TeamStateResponse)
def save_afleverlocaties(
    team_id: int,
    payload: SaveAfleverlocatiesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "edit")),
) -> TeamStateResponse:
    """Step 2: the delivery location per selected festival, written to
    KarTracker's "Plan a kar" table (the same rows its screen shows).
    """
    season, team = _load_for_change(db, current_user, team_id, payload.season_id)

    # Only festivals chosen in step 1, each at most once.
    festival_ids = [row.festival_id for row in payload.rows]
    if len(set(festival_ids)) != len(festival_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A festival appears more than once")
    if not set(festival_ids) <= selected_festival_ids(db, season.id, team.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Every festival must first be selected in step 1"
        )

    # Every chosen location must exist and be active.
    location_ids = {row.afleverlocatie_id for row in payload.rows if row.afleverlocatie_id is not None}
    if location_ids:
        valid_location_ids = set(
            db.scalars(
                select(KarTrackerAfleverlocatie.id).where(
                    KarTrackerAfleverlocatie.id.in_(location_ids), KarTrackerAfleverlocatie.active.is_(True)
                )
            ).all()
        )
        if valid_location_ids != location_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Every delivery location must exist and be active"
            )

    upsert_plan_kar_rows(db, season.id, team.id, [(row.festival_id, row.afleverlocatie_id) for row in payload.rows])

    # Clearing a location means the step no longer holds.
    if any(row.afleverlocatie_id is None for row in payload.rows):
        clear_step(db, season.id, team.id, "afleverlocaties")

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not save the locations") from error
    return build_team_state(db, current_user, season, team)


@router.post("/wizard/{team_id}/steps/{step_key}/complete", response_model=TeamStateResponse)
def complete_step(
    team_id: int,
    step_key: str,
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "edit")),
) -> TeamStateResponse:
    """Mark a step as done, after checking its completion rule."""
    season, team = _load_for_change(db, current_user, team_id, season_id)
    step = STEPS_BY_KEY.get(step_key)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")

    if step.completion_check is not None:
        problem = step.completion_check(db, season.id, team.id)
        if problem is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    existing = db.scalar(
        select(AltsienSelectStepProgress).where(
            AltsienSelectStepProgress.season_id == season.id,
            AltsienSelectStepProgress.team_id == team.id,
            AltsienSelectStepProgress.step_key == step_key,
        )
    )
    if existing is None:
        db.add(
            AltsienSelectStepProgress(
                season_id=season.id, team_id=team.id, step_key=step_key, completed_by_user_id=current_user.id
            )
        )
    else:
        # Confirming again refreshes who/when.
        existing.completed_at = datetime.now(timezone.utc)
        existing.completed_by_user_id = current_user.id
    db.commit()
    return build_team_state(db, current_user, season, team)


@router.delete("/wizard/{team_id}/steps/{step_key}/complete", response_model=TeamStateResponse)
def reopen_step(
    team_id: int,
    step_key: str,
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "edit")),
) -> TeamStateResponse:
    """Mark a step as not done again."""
    season, team = _load_for_change(db, current_user, team_id, season_id)
    if step_key not in STEPS_BY_KEY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    clear_step(db, season.id, team.id, step_key)
    db.commit()
    return build_team_state(db, current_user, season, team)


# --- Special requests (from the wizard) -----------------------------------


def _get_team_request(db: Session, team_id: int, request_id: int) -> AltsienSelectSpecialRequest:
    """Load one request that belongs to the given team, or 404."""
    request = db.get(AltsienSelectSpecialRequest, request_id)
    if request is None or request.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return request


def _ensure_request_still_new(db: Session, request: AltsienSelectSpecialRequest) -> None:
    """Once the organisation picked a request up, the Kernlid can no
    longer change or withdraw it from the wizard.
    """
    first_status = first_request_status(db)
    if first_status is None or request.status_id != first_status.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This request is already being handled"
        )


def _single_request_response(db: Session, user: User, request: AltsienSelectSpecialRequest, season: Season):
    """One request's response, as seen by this user."""
    return build_request_responses(db, user, [request], season_is_editable_for(db, user, season))[0]


@router.post(
    "/wizard/{team_id}/requests", response_model=SpecialRequestResponse, status_code=status.HTTP_201_CREATED
)
def create_special_request(
    team_id: int,
    season_id: int,
    payload: SpecialRequestWriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "edit")),
) -> SpecialRequestResponse:
    """Add a special request; it starts in the first status (New)."""
    season, team = _load_for_change(db, current_user, team_id, season_id)
    first_status = first_request_status(db)
    if first_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No request statuses have been defined yet"
        )
    request = AltsienSelectSpecialRequest(
        season_id=season.id,
        team_id=team.id,
        text=payload.text.strip(),
        status_id=first_status.id,
        created_by_user_id=current_user.id,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return _single_request_response(db, current_user, request, season)


@router.put("/wizard/{team_id}/requests/{request_id}", response_model=SpecialRequestResponse)
def update_special_request(
    team_id: int,
    request_id: int,
    payload: SpecialRequestWriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "edit")),
) -> SpecialRequestResponse:
    """Change a request's text while it is still New."""
    request = _get_team_request(db, team_id, request_id)
    season, _team = _load_for_change(db, current_user, team_id, request.season_id)
    _ensure_request_still_new(db, request)
    request.text = payload.text.strip()
    db.commit()
    db.refresh(request)
    return _single_request_response(db, current_user, request, season)


@router.delete("/wizard/{team_id}/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_special_request(
    team_id: int,
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "edit")),
) -> None:
    """Withdraw a request while it is still New."""
    request = _get_team_request(db, team_id, request_id)
    _load_for_change(db, current_user, team_id, request.season_id)
    _ensure_request_still_new(db, request)
    db.delete(request)
    db.commit()


# --- Ploegfiche -----------------------------------------------------------


@router.get("/ploegfiche/{team_id}", response_model=TeamStateResponse)
def get_ploegfiche(
    team_id: int,
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(PLOEGFICHE_SCREEN, "view")),
) -> TeamStateResponse:
    """The complete overview of one team's choices in one season."""
    season = get_season_or_404(db, season_id)
    team = get_team_in_scope(db, current_user, team_id)
    return build_team_state(db, current_user, season, team)


@router.get("/ploegfiche/{team_id}/pdf")
def get_ploegfiche_pdf(
    team_id: int,
    season_id: int,
    locale: Literal["nl", "en"] = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(PLOEGFICHE_SCREEN, "view")),
) -> Response:
    """The Ploegfiche as a PDF with the Altsien logo, opened inline in a
    new browser tab (the user can print or save it from there).
    """
    season = get_season_or_404(db, season_id)
    team = get_team_in_scope(db, current_user, team_id)
    pdf_bytes = build_ploegfiche_pdf(build_team_state(db, current_user, season, team), locale)
    filename = f"Ploegfiche {team.name} {season.name}.pdf"
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace("\\", "_").replace('"', "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"},
    )


# --- Request follow-up (organisation) -------------------------------------


@router.get("/requests", response_model=list[SpecialRequestResponse])
def list_special_requests(
    season_id: int,
    status_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission("altsienselect.requests", "view")),
) -> list[SpecialRequestResponse]:
    """Every special request of the season (optionally one status), oldest
    first so the longest-waiting ones come on top.
    """
    get_season_or_404(db, season_id)
    query = select(AltsienSelectSpecialRequest).where(AltsienSelectSpecialRequest.season_id == season_id)
    if status_id is not None:
        query = query.where(AltsienSelectSpecialRequest.status_id == status_id)
    requests = db.scalars(
        query.order_by(AltsienSelectSpecialRequest.created_at, AltsienSelectSpecialRequest.id)
    ).all()
    # "editable_by_me" is about the Kernlid's wizard edit; not relevant here.
    return build_request_responses(db, current_user, list(requests), season_editable=False)


@router.put("/requests/{request_id}", response_model=SpecialRequestResponse)
def follow_up_special_request(
    request_id: int,
    payload: SpecialRequestFollowUpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission("altsienselect.requests", "edit")),
) -> SpecialRequestResponse:
    """The organisation sets a request's status and its answer."""
    request = db.get(AltsienSelectSpecialRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if db.get(AltsienSelectRequestStatus, payload.status_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")

    request.status_id = payload.status_id
    note = (payload.organisation_note or "").strip()
    request.organisation_note = note or None
    db.commit()
    db.refresh(request)
    return build_request_responses(db, current_user, [request], season_editable=False)[0]


# --- Request statuses (MasterData) ----------------------------------------


@router.get("/request-statuses", response_model=list[RequestStatusResponse])
def list_request_statuses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[AltsienSelectRequestStatus]:
    """Every status, in order. Readable with plain module access, since the
    follow-up screen's dropdown and filters need it too.
    """
    return list(
        db.scalars(
            select(AltsienSelectRequestStatus).order_by(
                AltsienSelectRequestStatus.sort_order, AltsienSelectRequestStatus.name
            )
        ).all()
    )


def _save_status(db: Session, target: AltsienSelectRequestStatus) -> AltsienSelectRequestStatus:
    """Commit a new/changed status, turning a duplicate name into a 409."""
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A status with this name already exists"
        ) from error
    db.refresh(target)
    return target


@router.post("/request-statuses", response_model=RequestStatusResponse, status_code=status.HTTP_201_CREATED)
def create_request_status(
    payload: RequestStatusWriteRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.statuses", "create")),
) -> AltsienSelectRequestStatus:
    """Create a brand-new status."""
    new_status = AltsienSelectRequestStatus(
        name=payload.name.strip(), is_open=payload.is_open, color=payload.color, sort_order=payload.sort_order
    )
    db.add(new_status)
    return _save_status(db, new_status)


@router.put("/request-statuses/{status_id}", response_model=RequestStatusResponse)
def update_request_status(
    status_id: int,
    payload: RequestStatusWriteRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.statuses", "edit")),
) -> AltsienSelectRequestStatus:
    """Update an existing status."""
    existing_status = db.get(AltsienSelectRequestStatus, status_id)
    if existing_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    existing_status.name = payload.name.strip()
    existing_status.is_open = payload.is_open
    existing_status.color = payload.color
    existing_status.sort_order = payload.sort_order
    return _save_status(db, existing_status)


@router.delete("/request-statuses/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request_status(
    status_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("altsienselect.statuses", "delete")),
) -> None:
    """Delete a status that no request uses anymore."""
    existing_status = db.get(AltsienSelectRequestStatus, status_id)
    if existing_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    if db.scalar(
        select(AltsienSelectSpecialRequest.id).where(AltsienSelectSpecialRequest.status_id == status_id)
    ) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This status is still assigned to at least one request"
        )
    db.delete(existing_status)
    db.commit()
