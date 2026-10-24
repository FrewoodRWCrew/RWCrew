# This is MasterData's own router file. Unlike the placeholder modules
# (which just call the shared create_module_router() factory), MasterData
# needs its own custom-roles-with-per-screen-permissions system — the
# same one built for TagScan (see app/modules/module_1/router.py) — plus
# the Season screen, its first actual piece of master data.

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.delivery_method import DeliveryMethod
from app.db.models.festival import Festival
from app.db.models.kartracker_speciale_levertoer import KarTrackerSpecialeLevertoer
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_kernlid import TeamKernlid
from app.db.models.team_location import TeamLocation
from app.db.models.team_responsible import TeamResponsible
from app.db.models.team_speciale_levertoer import TeamSpecialeLevertoer
from app.db.models.team_task import TeamTask
from app.db.models.team_team_task import TeamTeamTask
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_9.delivery_method_import import (
    build_delivery_method_template_xlsx,
    export_delivery_methods_to_xlsx,
    import_delivery_methods_from_xlsx,
)
from app.help.routes import register_help_route
from app.modules.module_9.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    screen_keys_allowed,
    user_can,
)
from app.modules.module_9.festival_import import (
    build_festival_template_xlsx,
    export_festivals_to_xlsx,
    import_festivals_from_xlsx,
)
from app.modules.module_9.masterdata_dashboard import build_dashboard_stats
from app.modules.module_9.season_import import (
    build_season_template_xlsx,
    export_seasons_to_xlsx,
    import_seasons_from_xlsx,
)
from app.modules.module_9.team_festival_import import (
    build_team_festival_template_xlsx,
    export_team_festivals_to_xlsx,
    import_team_festivals_from_xlsx,
)
from app.modules.module_9.team_import import build_team_template_xlsx, export_teams_to_xlsx, import_teams_from_xlsx
from app.modules.module_9.team_kernlid_import import (
    build_team_kernlid_template_xlsx,
    export_team_kernleden_to_xlsx,
    import_team_kernleden_from_xlsx,
)
from app.modules.module_9.team_location_import import (
    build_team_location_template_xlsx,
    export_team_locations_to_xlsx,
    import_team_locations_from_xlsx,
)
from app.modules.module_9.team_responsible_import import (
    build_team_responsible_template_xlsx,
    export_team_responsibles_to_xlsx,
    import_team_responsibles_from_xlsx,
)
from app.modules.module_9.team_responsible_service import (
    apply_team_responsible_fields,
    reopen_step_if_no_responsibles,
)
from app.modules.module_9.team_team_task_import import (
    build_team_team_task_template_xlsx,
    export_team_team_tasks_to_xlsx,
    import_team_team_tasks_from_xlsx,
)
from app.modules.module_9.team_task_import import (
    build_team_task_template_xlsx,
    export_team_tasks_to_xlsx,
    import_team_tasks_from_xlsx,
)
from app.schemas.masterdata import (
    CreateOrGrantUserRequest,
    DeliveryMethodCreateRequest,
    DeliveryMethodImportResponse,
    DeliveryMethodResponse,
    DeliveryMethodUpdateRequest,
    FestivalCreateRequest,
    FestivalImportResponse,
    FestivalResponse,
    FestivalUpdateRequest,
    MasterDataDashboardResponse,
    MasterDataUserSummaryResponse,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SeasonCreateRequest,
    SeasonImportResponse,
    SeasonResponse,
    SeasonUpdateRequest,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    SpecialTourOptionResponse,
    TeamCreateRequest,
    TeamImportResponse,
    TeamLinkImportResponse,
    TeamLocationCreateRequest,
    TeamLocationImportResponse,
    TeamLocationResponse,
    TeamLocationUpdateRequest,
    TeamResponsibleCreateRequest,
    TeamResponsibleOptionItem,
    TeamResponsibleOptionsResponse,
    TeamResponsibleResponse,
    TeamResponsibleUpdateRequest,
    TeamResponse,
    TeamTaskCreateRequest,
    TeamTaskImportResponse,
    TeamTaskResponse,
    TeamTaskUpdateRequest,
    TeamUpdateRequest,
)

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter(prefix="/api/modules/module-9", tags=["MasterData"])

# GET /help/pdf: the module's manual, with only the screens the user can view.
register_help_route(
    router,
    module_key=MODULE_KEY,
    require_access=require_module_access,
    viewable_screen_keys=lambda db, user: screen_keys_allowed(db, user, "view"),
)


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
    """Tell the frontend which MasterData screens the current user can view
    and create on, so it knows what to show — sidebar links, and
    finer-grained controls like the Data Upload/Download screen's upload
    button — without duplicating the permission-checking rules itself.
    """
    screens = db.scalars(select(MasterDataScreen)).all()
    viewable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "view")]
    creatable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "create")]
    return MyPermissionsResponse(viewable_screen_keys=viewable_keys, creatable_screen_keys=creatable_keys)


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
    new_season = Season(name=payload.name, periode_open=payload.periode_open)
    db.add(new_season)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A year with this name already exists") from error

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Year not found")

    season.name = payload.name
    season.periode_open = payload.periode_open
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A year with this name already exists") from error

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Year not found")

    db.delete(season)
    db.commit()


def _validate_festival_lookup_ids(db: Session, payload: FestivalCreateRequest | FestivalUpdateRequest) -> None:
    """Make sure season_id actually exists, the same way
    _validate_product_lookup_ids() below checks type_id/warehouse_id/etc.
    — a bad id should surface as a clear 404, not an opaque FK IntegrityError.
    """
    if db.get(Season, payload.season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Year not found")


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


@router.get("/team-responsibles", response_model=list[TeamResponsibleResponse])
def list_team_responsibles(
    season_id: int | None = None,
    team_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-responsibles", "view")),
) -> list[TeamResponsible]:
    """List the responsible people ("Ploegverantwoordelijken"), optionally
    narrowed to one season and/or one team, sorted by team then name.
    """
    query = select(TeamResponsible).join(Team, Team.id == TeamResponsible.team_id)
    if season_id is not None:
        query = query.where(TeamResponsible.season_id == season_id)
    if team_id is not None:
        query = query.where(TeamResponsible.team_id == team_id)
    return list(db.scalars(query.order_by(Team.name, TeamResponsible.name)).all())


# Declared before the "/{team_responsible_id}" routes so "options" is never
# mistaken for an id.
@router.get("/team-responsibles/options", response_model=TeamResponsibleOptionsResponse)
def list_team_responsible_options(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-responsibles", "view")),
) -> TeamResponsibleOptionsResponse:
    """Every team and season, for the screen's dropdowns — served here so a
    user only needs this screen's own permission, not Teams/Season's too.
    """
    teams = db.scalars(select(Team).order_by(Team.name)).all()
    seasons = db.scalars(select(Season).order_by(Season.name)).all()
    return TeamResponsibleOptionsResponse(
        teams=[TeamResponsibleOptionItem(id=team.id, name=team.name) for team in teams],
        seasons=[TeamResponsibleOptionItem(id=season.id, name=season.name) for season in seasons],
    )


def _apply_team_responsible_payload(
    db: Session,
    team_responsible: TeamResponsible,
    payload: TeamResponsibleCreateRequest | TeamResponsibleUpdateRequest,
) -> None:
    """Check the chosen team/season exist (a clear 404 instead of an FK
    error), then copy every field from the payload onto the row.
    """
    if db.get(Team, payload.team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if db.get(Season, payload.season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Year not found")

    team_responsible.team_id = payload.team_id
    team_responsible.season_id = payload.season_id
    apply_team_responsible_fields(
        team_responsible,
        name=payload.name,
        email=str(payload.email),
        phone=payload.phone,
        comments=payload.comments,
    )


@router.post("/team-responsibles", response_model=TeamResponsibleResponse, status_code=status.HTTP_201_CREATED)
def create_team_responsible(
    payload: TeamResponsibleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-responsibles", "create")),
) -> TeamResponsible:
    """Add a responsible person to a team for a season."""
    new_team_responsible = TeamResponsible()
    _apply_team_responsible_payload(db, new_team_responsible, payload)
    db.add(new_team_responsible)
    db.commit()
    db.refresh(new_team_responsible)
    return new_team_responsible


@router.put("/team-responsibles/{team_responsible_id}", response_model=TeamResponsibleResponse)
def update_team_responsible(
    team_responsible_id: int,
    payload: TeamResponsibleUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-responsibles", "edit")),
) -> TeamResponsible:
    """Change every field of an existing responsible person."""
    team_responsible = db.get(TeamResponsible, team_responsible_id)
    if team_responsible is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team responsible not found")

    # Where the person was before, in case this moves them to another team/season.
    old_season_id, old_team_id = team_responsible.season_id, team_responsible.team_id
    _apply_team_responsible_payload(db, team_responsible, payload)
    if (old_season_id, old_team_id) != (team_responsible.season_id, team_responsible.team_id):
        reopen_step_if_no_responsibles(db, old_season_id, old_team_id)
    db.commit()
    db.refresh(team_responsible)
    return team_responsible


@router.delete("/team-responsibles/{team_responsible_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team_responsible(
    team_responsible_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.team-responsibles", "delete")),
) -> None:
    """Permanently delete a responsible person."""
    team_responsible = db.get(TeamResponsible, team_responsible_id)
    if team_responsible is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team responsible not found")

    db.delete(team_responsible)
    # The last one gone means Altsien Select's wizard step no longer holds.
    reopen_step_if_no_responsibles(db, team_responsible.season_id, team_responsible.team_id)
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
        kernlid = db.get(User, kernlid_id)
        if kernlid is None or not kernlid.is_altsien_kernlid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Altsien Kernlid not found")

    for tour_id in payload.special_tour_ids or []:
        if db.get(KarTrackerSpecialeLevertoer, tour_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Special delivery tour not found")


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


def _replace_team_special_tour_links(db: Session, team_id: int, tour_ids: list[int] | None) -> None:
    """Same replace-not-append logic as _replace_team_task_links, for
    MasterData_team_speciale_levertoer. None = the request left the field out:
    keep the team's current links.
    """
    if tour_ids is None:
        return
    db.execute(delete(TeamSpecialeLevertoer).where(TeamSpecialeLevertoer.team_id == team_id))
    for tour_id in dict.fromkeys(tour_ids):
        db.add(TeamSpecialeLevertoer(team_id=team_id, levertoer_id=tour_id))


def _team_to_response(db: Session, team: Team) -> TeamResponse:
    """Build a TeamResponse for one team by pulling its current task_ids/
    kernlid_ids from the two join tables — these aren't columns on Team
    itself.
    """
    task_ids = list(db.scalars(select(TeamTeamTask.team_task_id).where(TeamTeamTask.team_id == team.id)).all())
    kernlid_ids = list(
        db.scalars(select(TeamKernlid.altsien_kernlid_id).where(TeamKernlid.team_id == team.id)).all()
    )
    special_tour_ids = list(
        db.scalars(
            select(TeamSpecialeLevertoer.levertoer_id).where(TeamSpecialeLevertoer.team_id == team.id)
        ).all()
    )
    return TeamResponse(
        id=team.id,
        name=team.name,
        location_id=team.location_id,
        delivery_method_id=team.delivery_method_id,
        task_ids=sorted(task_ids),
        kernlid_ids=sorted(kernlid_ids),
        special_tour_ids=sorted(special_tour_ids),
        description=team.description,
        active=team.active,
    )


@router.get("/special-tours", response_model=list[SpecialTourOptionResponse])
def list_special_tour_options(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.teams", "view")),
) -> list[KarTrackerSpecialeLevertoer]:
    """Every KarTracker "Speciale levertoer", for the team fiche's "Levertoeren"
    field — gated by the Teams screen, so managing teams needs no KarTracker rights.
    """
    return list(
        db.scalars(select(KarTrackerSpecialeLevertoer).order_by(KarTrackerSpecialeLevertoer.name)).all()
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
        active=payload.active,
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
    _replace_team_special_tour_links(db, new_team.id, payload.special_tour_ids)

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
    team.active = payload.active

    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A team with this name already exists") from error

    _replace_team_task_links(db, team.id, payload.task_ids)
    _replace_team_kernlid_links(db, team.id, payload.kernlid_ids)
    _replace_team_special_tour_links(db, team.id, payload.special_tour_ids)

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


# --- Data Upload/Download: bulk XLSX import/export, one tile per table on
# the frontend's tile grid, all gated by the SAME "masterdata.dataupload"
# screen key regardless of table — never by each table's own screen key —
# mirroring KarTracker's own kar-import/kar-status-import endpoints.


@router.get("/season-import/template")
def download_season_import_template(
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing seasons."""
    return Response(
        content=build_season_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="year-import-template.xlsx"'},
    )


@router.post("/season-import", response_model=SeasonImportResponse)
def import_seasons(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "create")),
) -> SeasonImportResponse:
    """Bulk-import seasons from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_seasons_from_xlsx(db, file.file.read())
    return SeasonImportResponse(results=results)


@router.get("/seasons/export")
def export_seasons(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """Every season as an XLSX workbook."""
    return Response(
        content=export_seasons_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="masterdata-years-export.xlsx"'},
    )


@router.get("/team-location-import/template")
def download_team_location_import_template(
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing team locations."""
    return Response(
        content=build_team_location_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="team-location-import-template.xlsx"'},
    )


@router.post("/team-location-import", response_model=TeamLocationImportResponse)
def import_team_locations(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "create")),
) -> TeamLocationImportResponse:
    """Bulk-import team locations from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_team_locations_from_xlsx(db, file.file.read())
    return TeamLocationImportResponse(results=results)


@router.get("/team-locations/export")
def export_team_locations_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """Every team location as an XLSX workbook."""
    return Response(
        content=export_team_locations_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="masterdata-team-locations-export.xlsx"'},
    )


@router.get("/delivery-method-import/template")
def download_delivery_method_import_template(
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing delivery methods."""
    return Response(
        content=build_delivery_method_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="delivery-method-import-template.xlsx"'},
    )


@router.post("/delivery-method-import", response_model=DeliveryMethodImportResponse)
def import_delivery_methods(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "create")),
) -> DeliveryMethodImportResponse:
    """Bulk-import delivery methods from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_delivery_methods_from_xlsx(db, file.file.read())
    return DeliveryMethodImportResponse(results=results)


@router.get("/delivery-methods/export")
def export_delivery_methods_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """Every delivery method as an XLSX workbook."""
    return Response(
        content=export_delivery_methods_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="masterdata-delivery-methods-export.xlsx"'},
    )


@router.get("/team-task-import/template")
def download_team_task_import_template(
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing team tasks."""
    return Response(
        content=build_team_task_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="team-task-import-template.xlsx"'},
    )


@router.post("/team-task-import", response_model=TeamTaskImportResponse)
def import_team_tasks(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "create")),
) -> TeamTaskImportResponse:
    """Bulk-import team tasks from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_team_tasks_from_xlsx(db, file.file.read())
    return TeamTaskImportResponse(results=results)


@router.get("/team-tasks/export")
def export_team_tasks_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """Every team task as an XLSX workbook."""
    return Response(
        content=export_team_tasks_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="masterdata-team-tasks-export.xlsx"'},
    )


@router.get("/festival-import/template")
def download_festival_import_template(
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing festivals."""
    return Response(
        content=build_festival_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="festival-import-template.xlsx"'},
    )


@router.post("/festival-import", response_model=FestivalImportResponse)
def import_festivals(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "create")),
) -> FestivalImportResponse:
    """Bulk-import festivals from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_festivals_from_xlsx(db, file.file.read())
    return FestivalImportResponse(results=results)


@router.get("/festivals/export")
def export_festivals_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """Every festival as an XLSX workbook."""
    return Response(
        content=export_festivals_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="masterdata-festivals-export.xlsx"'},
    )


@router.get("/team-import/template")
def download_team_import_template(
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing teams. Only
    covers Team's own fields — its links have their own tiles.
    """
    return Response(
        content=build_team_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="team-import-template.xlsx"'},
    )


@router.post("/team-import", response_model=TeamImportResponse)
def import_teams(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "create")),
) -> TeamImportResponse:
    """Bulk-import teams from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_teams_from_xlsx(db, file.file.read())
    return TeamImportResponse(results=results)


@router.get("/teams/export")
def export_teams_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
) -> Response:
    """Every team's own fields as an XLSX workbook (its links have their own exports)."""
    return Response(
        content=export_teams_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="masterdata-teams-export.xlsx"'},
    )


# --- Data Upload/Download for the team links and Ploegverantwoordelijken:
# the same three endpoints per table (template, upload, export) and the same
# rights as the other tiles, registered in one go since they only differ in
# their path and functions.


def _register_team_link_upload(path: str, export_path: str, label: str, template_fn, import_fn, export_fn) -> None:
    """Add GET /<path>/template, POST /<path> and GET /<export_path> for one table."""

    def download_template(
        _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
    ) -> Response:
        return Response(
            content=template_fn(),
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{path}-template.xlsx"'},
        )

    def upload(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        _user: User = Depends(require_screen_permission("masterdata.dataupload", "create")),
    ) -> TeamLinkImportResponse:
        return TeamLinkImportResponse(results=import_fn(db, file.file.read()))

    def export(
        db: Session = Depends(get_db),
        _user: User = Depends(require_screen_permission("masterdata.dataupload", "view")),
    ) -> Response:
        return Response(
            content=export_fn(db),
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="masterdata-{export_path}-export.xlsx"'},
        )

    router.add_api_route(
        f"/{path}/template", download_template, methods=["GET"], summary=f"{label}: XLSX upload template"
    )
    router.add_api_route(
        f"/{path}", upload, methods=["POST"], response_model=TeamLinkImportResponse, summary=f"{label}: XLSX upload"
    )
    router.add_api_route(f"/{export_path}/export", export, methods=["GET"], summary=f"{label}: XLSX export")


_register_team_link_upload(
    "team-task-link-import",
    "team-task-links",
    "Tasks per team",
    build_team_team_task_template_xlsx,
    import_team_team_tasks_from_xlsx,
    export_team_team_tasks_to_xlsx,
)
_register_team_link_upload(
    "team-kernlid-import",
    "team-kernleden",
    "Kernleden per team",
    build_team_kernlid_template_xlsx,
    import_team_kernleden_from_xlsx,
    export_team_kernleden_to_xlsx,
)
_register_team_link_upload(
    "team-festival-import",
    "team-festivals",
    "Festivals per team",
    build_team_festival_template_xlsx,
    import_team_festivals_from_xlsx,
    export_team_festivals_to_xlsx,
)
_register_team_link_upload(
    "team-responsible-import",
    "team-responsibles",
    "Ploegverantwoordelijken",
    build_team_responsible_template_xlsx,
    import_team_responsibles_from_xlsx,
    export_team_responsibles_to_xlsx,
)
