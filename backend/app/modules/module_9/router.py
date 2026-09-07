# This is MasterData's own router file. Unlike the placeholder modules
# (which just call the shared create_module_router() factory), MasterData
# needs its own custom-roles-with-per-screen-permissions system — the
# same one built for TagScan (see app/modules/module_1/router.py) — plus
# the Season screen, its first actual piece of master data.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.altsien_kernlid import AltsienKernlid
from app.db.models.delivery_method import DeliveryMethod
from app.db.models.festival import Festival
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_limit import ProductLimit
from app.db.models.product_type import ProductType
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_kernlid import TeamKernlid
from app.db.models.team_location import TeamLocation
from app.db.models.team_task import TeamTask
from app.db.models.team_team_task import TeamTeamTask
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.db.models.warehouse import Warehouse
from app.modules.module_9.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    user_can,
)
from app.modules.module_9.masterdata_dashboard import build_dashboard_stats
from app.schemas.masterdata import (
    AltsienKernlidCreateRequest,
    AltsienKernlidResponse,
    AltsienKernlidUpdateRequest,
    CreateOrGrantUserRequest,
    DeliveryMethodCreateRequest,
    DeliveryMethodResponse,
    DeliveryMethodUpdateRequest,
    FestivalCreateRequest,
    FestivalResponse,
    FestivalUpdateRequest,
    MasterDataDashboardResponse,
    MasterDataUserSummaryResponse,
    MyPermissionsResponse,
    ProductCategoryCreateRequest,
    ProductCategoryResponse,
    ProductCategoryUpdateRequest,
    ProductCreateRequest,
    ProductLimitCreateRequest,
    ProductLimitResponse,
    ProductLimitUpdateRequest,
    ProductResponse,
    ProductTypeCreateRequest,
    ProductTypeResponse,
    ProductTypeUpdateRequest,
    ProductUpdateRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SeasonCreateRequest,
    SeasonResponse,
    SeasonUpdateRequest,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    TeamCreateRequest,
    TeamLocationCreateRequest,
    TeamLocationResponse,
    TeamLocationUpdateRequest,
    TeamResponse,
    TeamTaskCreateRequest,
    TeamTaskResponse,
    TeamTaskUpdateRequest,
    TeamUpdateRequest,
    WarehouseCreateRequest,
    WarehouseResponse,
    WarehouseUpdateRequest,
)

router = APIRouter(prefix="/api/modules/module-9", tags=["MasterData"])


def _build_role_response(db: Session, role: MasterDataRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(MasterDataScreen).order_by(MasterDataScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(MasterDataRolePermission).where(MasterDataRolePermission.role_id == role.id)
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
    _user: User = Depends(require_screen_permission("masterdata.roles", "view")),
) -> list[MasterDataScreen]:
    """List every registered MasterData screen — used to build the columns
    of the permission-matrix grid in the UI.
    """
    return list(db.scalars(select(MasterDataScreen).order_by(MasterDataScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.roles", "view")),
) -> list[RoleResponse]:
    """List every MasterData role, each with its full permission matrix."""
    roles = db.scalars(select(MasterDataRole).order_by(MasterDataRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = MasterDataRole(name=payload.name)
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
    _user: User = Depends(require_screen_permission("masterdata.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(MasterDataRole, role_id)
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
    _user: User = Depends(require_screen_permission("masterdata.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(MasterDataRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(select(MasterDataUserRole).where(MasterDataUserRole.role_id == role_id))
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
    _user: User = Depends(require_screen_permission("masterdata.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(MasterDataRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(MasterDataRolePermission).where(MasterDataRolePermission.role_id == role_id)
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
                MasterDataRolePermission(
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


def _build_user_summary(db: Session, user: User) -> MasterDataUserSummaryResponse:
    user_role = get_user_role(db, user.id)
    role = db.get(MasterDataRole, user_role.role_id) if user_role else None
    return MasterDataUserSummaryResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id if role else None,
        role_name=role.name if role else None,
    )


@router.get("/users", response_model=list[MasterDataUserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.users", "view")),
) -> list[MasterDataUserSummaryResponse]:
    """List every user with access to MasterData, and their current role."""
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    users_with_access = db.scalars(
        select(User)
        .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
        .where(UserModuleAccess.module_id == module.id)
        .order_by(User.display_name)
    ).all()
    return [_build_user_summary(db, user) for user in users_with_access]


@router.put("/users/{user_id}/role", response_model=MasterDataUserSummaryResponse)
def set_user_role(
    user_id: int,
    payload: SetUserRoleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.users", "edit")),
) -> MasterDataUserSummaryResponse:
    """Assign (or, if role_id is null, remove) a MasterData role for a
    user who already has access to MasterData.
    """
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(UserModuleAccess.user_id == user_id, UserModuleAccess.module_id == module.id)
    )
    if has_access is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to MasterData")

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(MasterDataRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(MasterDataUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=MasterDataUserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.users", "create")),
) -> MasterDataUserSummaryResponse:
    """Give someone access to MasterData, creating their account first if
    they don't already have one anywhere in RW Crew.

    This ALWAYS grants access to MasterData only — never any other module
    — regardless of who calls it, which is what keeps a MasterData admin
    (not just the super admin) safely able to onboard people on their own.
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
        role = db.get(MasterDataRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(MasterDataUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/dashboard", response_model=MasterDataDashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> MasterDataDashboardResponse:
    """Aggregate KPI stats for MasterData's "Masterdata Overview" landing
    page — gated only by plain module access, not a specific screen
    permission, matching TagScan's own dashboard (it's always-visible
    landing content, not a gated screen).
    """
    return build_dashboard_stats(db)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which MasterData screens the current user can
    view, so it knows what to show in the sidebar without duplicating the
    permission-checking rules itself.
    """
    screens = db.scalars(select(MasterDataScreen)).all()
    viewable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "view")]
    return MyPermissionsResponse(viewable_screen_keys=viewable_keys)


@router.get("/seasons", response_model=list[SeasonResponse])
def list_seasons(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.season", "view")),
) -> list[Season]:
    """List every season, for the Season screen's table."""
    return list(db.scalars(select(Season).order_by(Season.name)).all())


@router.post("/seasons", response_model=SeasonResponse, status_code=status.HTTP_201_CREATED)
def create_season(
    payload: SeasonCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.season", "create")),
) -> Season:
    """Create a brand-new season."""
    new_season = Season(name=payload.name)
    db.add(new_season)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A season with this name already exists") from error

    db.refresh(new_season)
    return new_season


@router.put("/seasons/{season_id}", response_model=SeasonResponse)
def update_season(
    season_id: int,
    payload: SeasonUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.season", "edit")),
) -> Season:
    """Rename an existing season."""
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")

    season.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A season with this name already exists") from error

    db.refresh(season)
    return season


@router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_season(
    season_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.season", "delete")),
) -> None:
    """Permanently delete a season."""
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")

    db.delete(season)
    db.commit()


def _validate_festival_lookup_ids(db: Session, payload: FestivalCreateRequest | FestivalUpdateRequest) -> None:
    """Make sure season_id actually exists, the same way
    _validate_product_lookup_ids() below checks type_id/warehouse_id/etc.
    — a bad id should surface as a clear 404, not an opaque FK IntegrityError.
    """
    if db.get(Season, payload.season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")


@router.get("/festivals", response_model=list[FestivalResponse])
def list_festivals(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.festival", "view")),
) -> list[Festival]:
    """List every festival, for the Festivals screen's table."""
    return list(db.scalars(select(Festival).order_by(Festival.name)).all())


@router.post("/festivals", response_model=FestivalResponse, status_code=status.HTTP_201_CREATED)
def create_festival(
    payload: FestivalCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.festival", "create")),
) -> Festival:
    """Create a brand-new festival."""
    _validate_festival_lookup_ids(db, payload)
    new_festival = Festival(**payload.model_dump())
    db.add(new_festival)
    db.commit()
    db.refresh(new_festival)
    return new_festival


@router.put("/festivals/{festival_id}", response_model=FestivalResponse)
def update_festival(
    festival_id: int,
    payload: FestivalUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.festival", "edit")),
) -> Festival:
    """Update every field of an existing festival."""
    festival = db.get(Festival, festival_id)
    if festival is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival not found")

    _validate_festival_lookup_ids(db, payload)
    for field, value in payload.model_dump().items():
        setattr(festival, field, value)
    db.commit()
    db.refresh(festival)
    return festival


@router.delete("/festivals/{festival_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_festival(
    festival_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.festival", "delete")),
) -> None:
    """Permanently delete a festival."""
    festival = db.get(Festival, festival_id)
    if festival is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival not found")

    db.delete(festival)
    db.commit()


@router.get("/team-locations", response_model=list[TeamLocationResponse])
def list_team_locations(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-location", "view")),
) -> list[TeamLocation]:
    """List every team location, for the Team Location screen's table."""
    return list(db.scalars(select(TeamLocation).order_by(TeamLocation.location)).all())


@router.post("/team-locations", response_model=TeamLocationResponse, status_code=status.HTTP_201_CREATED)
def create_team_location(
    payload: TeamLocationCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-location", "create")),
) -> TeamLocation:
    """Create a brand-new team location."""
    new_team_location = TeamLocation(location=payload.location)
    db.add(new_team_location)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A team location with this name already exists"
        ) from error

    db.refresh(new_team_location)
    return new_team_location


@router.put("/team-locations/{team_location_id}", response_model=TeamLocationResponse)
def update_team_location(
    team_location_id: int,
    payload: TeamLocationUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-location", "edit")),
) -> TeamLocation:
    """Rename an existing team location."""
    team_location = db.get(TeamLocation, team_location_id)
    if team_location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team location not found")

    team_location.location = payload.location
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A team location with this name already exists"
        ) from error

    db.refresh(team_location)
    return team_location


@router.delete("/team-locations/{team_location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team_location(
    team_location_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-location", "delete")),
) -> None:
    """Permanently delete a team location."""
    team_location = db.get(TeamLocation, team_location_id)
    if team_location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team location not found")

    db.delete(team_location)
    db.commit()


@router.get("/delivery-methods", response_model=list[DeliveryMethodResponse])
def list_delivery_methods(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.delivery-method", "view")),
) -> list[DeliveryMethod]:
    """List every delivery method, for the Delivery Method screen's table."""
    return list(db.scalars(select(DeliveryMethod).order_by(DeliveryMethod.delivery_method)).all())


@router.post("/delivery-methods", response_model=DeliveryMethodResponse, status_code=status.HTTP_201_CREATED)
def create_delivery_method(
    payload: DeliveryMethodCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.delivery-method", "create")),
) -> DeliveryMethod:
    """Create a brand-new delivery method."""
    new_delivery_method = DeliveryMethod(delivery_method=payload.delivery_method)
    db.add(new_delivery_method)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A delivery method with this name already exists"
        ) from error

    db.refresh(new_delivery_method)
    return new_delivery_method


@router.put("/delivery-methods/{delivery_method_id}", response_model=DeliveryMethodResponse)
def update_delivery_method(
    delivery_method_id: int,
    payload: DeliveryMethodUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.delivery-method", "edit")),
) -> DeliveryMethod:
    """Rename an existing delivery method."""
    delivery_method = db.get(DeliveryMethod, delivery_method_id)
    if delivery_method is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery method not found")

    delivery_method.delivery_method = payload.delivery_method
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A delivery method with this name already exists"
        ) from error

    db.refresh(delivery_method)
    return delivery_method


@router.delete("/delivery-methods/{delivery_method_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_method(
    delivery_method_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.delivery-method", "delete")),
) -> None:
    """Permanently delete a delivery method."""
    delivery_method = db.get(DeliveryMethod, delivery_method_id)
    if delivery_method is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery method not found")

    db.delete(delivery_method)
    db.commit()


@router.get("/team-tasks", response_model=list[TeamTaskResponse])
def list_team_tasks(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-tasks", "view")),
) -> list[TeamTask]:
    """List every team task, for the Team Tasks screen's table."""
    return list(db.scalars(select(TeamTask).order_by(TeamTask.team_tasks)).all())


@router.post("/team-tasks", response_model=TeamTaskResponse, status_code=status.HTTP_201_CREATED)
def create_team_task(
    payload: TeamTaskCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-tasks", "create")),
) -> TeamTask:
    """Create a brand-new team task."""
    new_team_task = TeamTask(team_tasks=payload.team_tasks)
    db.add(new_team_task)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A team task with this name already exists"
        ) from error

    db.refresh(new_team_task)
    return new_team_task


@router.put("/team-tasks/{team_task_id}", response_model=TeamTaskResponse)
def update_team_task(
    team_task_id: int,
    payload: TeamTaskUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-tasks", "edit")),
) -> TeamTask:
    """Rename an existing team task."""
    team_task = db.get(TeamTask, team_task_id)
    if team_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team task not found")

    team_task.team_tasks = payload.team_tasks
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A team task with this name already exists"
        ) from error

    db.refresh(team_task)
    return team_task


@router.delete("/team-tasks/{team_task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team_task(
    team_task_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-tasks", "delete")),
) -> None:
    """Permanently delete a team task."""
    team_task = db.get(TeamTask, team_task_id)
    if team_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team task not found")

    db.delete(team_task)
    db.commit()


@router.get("/altsien-kernleden", response_model=list[AltsienKernlidResponse])
def list_altsien_kernleden(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.altsien-kernleden", "view")),
) -> list[AltsienKernlid]:
    """List every Altsien Kernleden contact, for its screen's table."""
    return list(db.scalars(select(AltsienKernlid).order_by(AltsienKernlid.name, AltsienKernlid.first_name)).all())


@router.post("/altsien-kernleden", response_model=AltsienKernlidResponse, status_code=status.HTTP_201_CREATED)
def create_altsien_kernlid(
    payload: AltsienKernlidCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.altsien-kernleden", "create")),
) -> AltsienKernlid:
    """Create a brand-new Altsien Kernleden contact."""
    new_contact = AltsienKernlid(**payload.model_dump())
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return new_contact


@router.put("/altsien-kernleden/{altsien_kernlid_id}", response_model=AltsienKernlidResponse)
def update_altsien_kernlid(
    altsien_kernlid_id: int,
    payload: AltsienKernlidUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.altsien-kernleden", "edit")),
) -> AltsienKernlid:
    """Update every field of an existing Altsien Kernleden contact."""
    contact = db.get(AltsienKernlid, altsien_kernlid_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Altsien Kernleden contact not found")

    for field, value in payload.model_dump().items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/altsien-kernleden/{altsien_kernlid_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_altsien_kernlid(
    altsien_kernlid_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.altsien-kernleden", "delete")),
) -> None:
    """Delete an Altsien Kernleden contact."""
    contact = db.get(AltsienKernlid, altsien_kernlid_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Altsien Kernleden contact not found")

    db.delete(contact)
    db.commit()


def _validate_team_lookup_ids(db: Session, payload: TeamCreateRequest | TeamUpdateRequest) -> None:
    """Make sure location_id/delivery_method_id (if given) and every id in
    task_ids/kernlid_ids actually exist, the same way
    _validate_product_lookup_ids() below checks type_id/warehouse_id/etc. —
    a bad id should surface as a clear 404, not an opaque FK IntegrityError.
    """
    if payload.location_id is not None and db.get(TeamLocation, payload.location_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team location not found")
    if payload.delivery_method_id is not None and db.get(DeliveryMethod, payload.delivery_method_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery method not found")

    for task_id in payload.task_ids:
        if db.get(TeamTask, task_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team task not found")

    for kernlid_id in payload.kernlid_ids:
        if db.get(AltsienKernlid, kernlid_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Altsien Kernleden contact not found")


def _replace_team_task_links(db: Session, team_id: int, task_ids: list[int]) -> None:
    """Make MasterData_team_team_task's rows for this team match task_ids
    exactly: delete every existing row for this team, then insert one row
    per id in task_ids. Called inside the same commit as the rest of a
    create/update so it either all lands or all rolls back together.
    """
    db.execute(delete(TeamTeamTask).where(TeamTeamTask.team_id == team_id))
    for task_id in dict.fromkeys(task_ids):
        db.add(TeamTeamTask(team_id=team_id, team_task_id=task_id))


def _replace_team_kernlid_links(db: Session, team_id: int, kernlid_ids: list[int]) -> None:
    """Same replace-not-append logic as _replace_team_task_links, for
    MasterData_team_kernlid.
    """
    db.execute(delete(TeamKernlid).where(TeamKernlid.team_id == team_id))
    for kernlid_id in dict.fromkeys(kernlid_ids):
        db.add(TeamKernlid(team_id=team_id, altsien_kernlid_id=kernlid_id))


def _team_to_response(db: Session, team: Team) -> TeamResponse:
    """Build a TeamResponse for one team by pulling its current task_ids/
    kernlid_ids from the two join tables — these aren't columns on Team
    itself.
    """
    task_ids = list(db.scalars(select(TeamTeamTask.team_task_id).where(TeamTeamTask.team_id == team.id)).all())
    kernlid_ids = list(
        db.scalars(select(TeamKernlid.altsien_kernlid_id).where(TeamKernlid.team_id == team.id)).all()
    )
    return TeamResponse(
        id=team.id,
        name=team.name,
        location_id=team.location_id,
        delivery_method_id=team.delivery_method_id,
        task_ids=sorted(task_ids),
        kernlid_ids=sorted(kernlid_ids),
        description=team.description,
    )


@router.get("/teams", response_model=list[TeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.teams", "view")),
) -> list[TeamResponse]:
    """List every team, for the Teams screen's table."""
    teams = list(db.scalars(select(Team).order_by(Team.name)).all())
    return [_team_to_response(db, team) for team in teams]


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.teams", "create")),
) -> TeamResponse:
    """Create a brand-new team."""
    _validate_team_lookup_ids(db, payload)

    new_team = Team(
        name=payload.name,
        location_id=payload.location_id,
        delivery_method_id=payload.delivery_method_id,
        description=payload.description,
    )
    db.add(new_team)
    try:
        # Flush (not commit) so new_team.id is assigned and the uniqueness
        # check surfaces now, before the join-row inserts below — everything
        # still lands in a single transaction, committed together at the end.
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A team with this name already exists") from error

    _replace_team_task_links(db, new_team.id, payload.task_ids)
    _replace_team_kernlid_links(db, new_team.id, payload.kernlid_ids)

    db.commit()
    db.refresh(new_team)
    return _team_to_response(db, new_team)


@router.put("/teams/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    payload: TeamUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.teams", "edit")),
) -> TeamResponse:
    """Update every field of an existing team, replacing its task/kernlid links."""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    _validate_team_lookup_ids(db, payload)

    team.name = payload.name
    team.location_id = payload.location_id
    team.delivery_method_id = payload.delivery_method_id
    team.description = payload.description

    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A team with this name already exists") from error

    _replace_team_task_links(db, team.id, payload.task_ids)
    _replace_team_kernlid_links(db, team.id, payload.kernlid_ids)

    db.commit()
    db.refresh(team)
    return _team_to_response(db, team)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.teams", "delete")),
) -> None:
    """Permanently delete a team (its join-table rows cascade via ondelete=CASCADE)."""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    db.delete(team)
    db.commit()


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.products", "view")),
) -> list[Product]:
    """List every product, for the Products screen's table."""
    return list(db.scalars(select(Product).order_by(Product.name)).all())


def _validate_product_lookup_ids(db: Session, payload: ProductCreateRequest | ProductUpdateRequest) -> None:
    """Make sure any type_id/warehouse_id/category_id/limit_id given
    actually exists, the same way set_user_role() below checks role_id
    exists before assigning it — otherwise a bad id would only surface as
    an opaque foreign-key IntegrityError instead of a clear 404.
    """
    if payload.type_id is not None and db.get(ProductType, payload.type_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")
    if payload.warehouse_id is not None and db.get(Warehouse, payload.warehouse_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    if payload.category_id is not None and db.get(ProductCategory, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")
    if payload.limit_id is not None and db.get(ProductLimit, payload.limit_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product limit not found")


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.products", "create")),
) -> Product:
    """Create a brand-new product."""
    _validate_product_lookup_ids(db, payload)

    new_product = Product(**payload.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.products", "edit")),
) -> Product:
    """Update every field of an existing product."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    _validate_product_lookup_ids(db, payload)

    for field, value in payload.model_dump().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.products", "delete")),
) -> None:
    """Permanently delete a product."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    db.delete(product)
    db.commit()


@router.get("/product-types", response_model=list[ProductTypeResponse])
def list_product_types(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-types", "view")),
) -> list[ProductType]:
    """List every product type, for the Type screen's table."""
    return list(db.scalars(select(ProductType).order_by(ProductType.name)).all())


@router.post("/product-types", response_model=ProductTypeResponse, status_code=status.HTTP_201_CREATED)
def create_product_type(
    payload: ProductTypeCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-types", "create")),
) -> ProductType:
    """Create a brand-new product type."""
    new_product_type = ProductType(name=payload.name)
    db.add(new_product_type)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product type with this name already exists"
        ) from error

    db.refresh(new_product_type)
    return new_product_type


@router.put("/product-types/{product_type_id}", response_model=ProductTypeResponse)
def update_product_type(
    product_type_id: int,
    payload: ProductTypeUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-types", "edit")),
) -> ProductType:
    """Rename an existing product type."""
    product_type = db.get(ProductType, product_type_id)
    if product_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")

    product_type.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product type with this name already exists"
        ) from error

    db.refresh(product_type)
    return product_type


@router.delete("/product-types/{product_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_type(
    product_type_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-types", "delete")),
) -> None:
    """Permanently delete a product type, as long as no product is using it."""
    product_type = db.get(ProductType, product_type_id)
    if product_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")

    still_used = db.scalar(select(Product).where(Product.type_id == product_type_id))
    if still_used is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This product type is still used by at least one product")

    db.delete(product_type)
    db.commit()


@router.get("/warehouses", response_model=list[WarehouseResponse])
def list_warehouses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.warehouses", "view")),
) -> list[Warehouse]:
    """List every warehouse, for the Magazijn screen's table."""
    return list(db.scalars(select(Warehouse).order_by(Warehouse.name)).all())


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.warehouses", "create")),
) -> Warehouse:
    """Create a brand-new warehouse."""
    new_warehouse = Warehouse(name=payload.name)
    db.add(new_warehouse)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A warehouse with this name already exists"
        ) from error

    db.refresh(new_warehouse)
    return new_warehouse


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.warehouses", "edit")),
) -> Warehouse:
    """Rename an existing warehouse."""
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    warehouse.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A warehouse with this name already exists"
        ) from error

    db.refresh(warehouse)
    return warehouse


@router.delete("/warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.warehouses", "delete")),
) -> None:
    """Permanently delete a warehouse, as long as no product is using it."""
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    still_used = db.scalar(select(Product).where(Product.warehouse_id == warehouse_id))
    if still_used is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This warehouse is still used by at least one product")

    db.delete(warehouse)
    db.commit()


@router.get("/product-categories", response_model=list[ProductCategoryResponse])
def list_product_categories(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-categories", "view")),
) -> list[ProductCategory]:
    """List every product category, for the Categorie screen's table."""
    return list(db.scalars(select(ProductCategory).order_by(ProductCategory.name)).all())


@router.post("/product-categories", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_product_category(
    payload: ProductCategoryCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-categories", "create")),
) -> ProductCategory:
    """Create a brand-new product category."""
    new_product_category = ProductCategory(name=payload.name)
    db.add(new_product_category)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product category with this name already exists"
        ) from error

    db.refresh(new_product_category)
    return new_product_category


@router.put("/product-categories/{product_category_id}", response_model=ProductCategoryResponse)
def update_product_category(
    product_category_id: int,
    payload: ProductCategoryUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-categories", "edit")),
) -> ProductCategory:
    """Rename an existing product category."""
    product_category = db.get(ProductCategory, product_category_id)
    if product_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")

    product_category.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product category with this name already exists"
        ) from error

    db.refresh(product_category)
    return product_category


@router.delete("/product-categories/{product_category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_category(
    product_category_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-categories", "delete")),
) -> None:
    """Permanently delete a product category, as long as no product is using it."""
    product_category = db.get(ProductCategory, product_category_id)
    if product_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")

    still_used = db.scalar(select(Product).where(Product.category_id == product_category_id))
    if still_used is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This product category is still used by at least one product"
        )

    db.delete(product_category)
    db.commit()


@router.get("/product-limits", response_model=list[ProductLimitResponse])
def list_product_limits(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-limits", "view")),
) -> list[ProductLimit]:
    """List every limit option, for the Limiet screen's table."""
    return list(db.scalars(select(ProductLimit).order_by(ProductLimit.name)).all())


@router.post("/product-limits", response_model=ProductLimitResponse, status_code=status.HTTP_201_CREATED)
def create_product_limit(
    payload: ProductLimitCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-limits", "create")),
) -> ProductLimit:
    """Create a brand-new limit option."""
    new_product_limit = ProductLimit(name=payload.name)
    db.add(new_product_limit)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A limit option with this name already exists"
        ) from error

    db.refresh(new_product_limit)
    return new_product_limit


@router.put("/product-limits/{product_limit_id}", response_model=ProductLimitResponse)
def update_product_limit(
    product_limit_id: int,
    payload: ProductLimitUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-limits", "edit")),
) -> ProductLimit:
    """Rename an existing limit option."""
    product_limit = db.get(ProductLimit, product_limit_id)
    if product_limit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product limit not found")

    product_limit.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A limit option with this name already exists"
        ) from error

    db.refresh(product_limit)
    return product_limit


@router.delete("/product-limits/{product_limit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_limit(
    product_limit_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.product-limits", "delete")),
) -> None:
    """Permanently delete a limit option, as long as no product is using it."""
    product_limit = db.get(ProductLimit, product_limit_id)
    if product_limit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product limit not found")

    still_used = db.scalar(select(Product).where(Product.limit_id == product_limit_id))
    if still_used is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This limit option is still used by at least one product")

    db.delete(product_limit)
    db.commit()
