# This is KarTracker's own router file. Unlike modules 4-9 (which just call
# the shared create_module_router() factory), KarTracker needs its own
# custom-roles-with-per-screen-permissions system, so its endpoints are
# written out in full here — see docs/module-custom-roles-pattern.md.
#
# This is the module's first development phase: only the Access Rights
# scaffold (screens/roles/permissions/users) exists so far. The cart
# registry ("Karlijst") and delivery planning endpoints get added here
# alongside their own screen keys once that phase is designed.

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.altsien_kernlid import AltsienKernlid
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.db.models.festival import Festival
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_role import KarTrackerRole
from app.db.models.kartracker_role_permission import KarTrackerRolePermission
from app.db.models.kartracker_screen import KarTrackerScreen
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_2.afleverlocatie_import import (
    build_afleverlocatie_template_xlsx,
    export_afleverlocaties_to_xlsx,
    import_afleverlocaties_from_xlsx,
)
from app.modules.module_2.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    require_screen_view_or_create,
    user_can,
)
from app.modules.module_2.distributiepunt_import import (
    build_distributiepunt_template_xlsx,
    export_distributiepunten_to_xlsx,
    import_distributiepunten_from_xlsx,
)
from app.modules.module_2.karblad_pdf import (
    KarbladData,
    KarbladFestival,
    build_karbladen_pdf,
    build_request_url,
)
from app.modules.module_2.kar_import import build_kar_template_xlsx, export_karren_to_xlsx, import_karren_from_xlsx
from app.modules.module_2.kar_status_import import (
    build_kar_status_template_xlsx,
    export_kar_statuses_to_xlsx,
    import_kar_statuses_from_xlsx,
)
from app.modules.module_2.zone_import import build_zone_template_xlsx, export_zones_to_xlsx, import_zones_from_xlsx
from app.schemas.kartracker import (
    AfleverlocatieCreateRequest,
    AfleverlocatieImportResponse,
    AfleverlocatieResponse,
    AfleverlocatieUpdateRequest,
    CreateOrGrantUserRequest,
    DistributiepuntCreateRequest,
    DistributiepuntImportResponse,
    DistributiepuntResponse,
    DistributiepuntUpdateRequest,
    KarCreateRequest,
    KarImportResponse,
    KarMapAfleverlocatieRow,
    KarMapDistributiepuntRow,
    KarMapKarRow,
    KarMapResponse,
    KarPlanningFestivalResponse,
    KarPlanningPrintRequest,
    KarPlanningReportResponse,
    KarPlanningResponse,
    KarResponse,
    KarStatusCreateRequest,
    KarStatusImportResponse,
    KarStatusResponse,
    KarStatusUpdateRequest,
    KarTrackerGroundplanResponse,
    KarTrackerUserSummaryResponse,
    KarUpdateRequest,
    LeverdatumResponse,
    LeverdatumRow,
    LeverdatumSaveRequest,
    MyPermissionsResponse,
    PlanKarAfleverlocatieOption,
    PlanKarFestivalRow,
    PlanKarOption,
    PlanKarResponse,
    PlanKarSaveRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    ZoneCreateRequest,
    ZoneImportResponse,
    ZoneResponse,
    ZoneUpdateRequest,
)

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter(prefix="/api/modules/module-2", tags=["KarTracker"])


def _build_role_response(db: Session, role: KarTrackerRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(KarTrackerScreen).order_by(KarTrackerScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(KarTrackerRolePermission).where(KarTrackerRolePermission.role_id == role.id)
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
    _user: User = Depends(require_screen_permission("kartracker.roles", "view")),
) -> list[KarTrackerScreen]:
    """List every registered KarTracker screen — used to build the columns
    of the permission-matrix grid in the UI.
    """
    return list(db.scalars(select(KarTrackerScreen).order_by(KarTrackerScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.roles", "view")),
) -> list[RoleResponse]:
    """List every KarTracker role, each with its full permission matrix."""
    roles = db.scalars(select(KarTrackerRole).order_by(KarTrackerRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = KarTrackerRole(name=payload.name)
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
    _user: User = Depends(require_screen_permission("kartracker.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(KarTrackerRole, role_id)
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
    _user: User = Depends(require_screen_permission("kartracker.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(KarTrackerRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(select(KarTrackerUserRole).where(KarTrackerUserRole.role_id == role_id))
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
    _user: User = Depends(require_screen_permission("kartracker.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(KarTrackerRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    valid_screen_ids = set(db.scalars(select(KarTrackerScreen.id)).all())
    for item in payload.permissions:
        if item.screen_id not in valid_screen_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screen not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(KarTrackerRolePermission).where(KarTrackerRolePermission.role_id == role_id)
        )
    }

    # A screen left out of the payload means "no permissions on that
    # screen" — delete its row rather than leaving stale permissions
    # behind, matching "no row = no access" and this endpoint's own
    # "entire permission matrix" contract.
    incoming_screen_ids = {item.screen_id for item in payload.permissions}
    for screen_id, existing in existing_permissions.items():
        if screen_id not in incoming_screen_ids:
            db.delete(existing)

    for item in payload.permissions:
        existing = existing_permissions.get(item.screen_id)
        if existing is not None:
            existing.can_view = item.can_view
            existing.can_create = item.can_create
            existing.can_edit = item.can_edit
            existing.can_delete = item.can_delete
        else:
            db.add(
                KarTrackerRolePermission(
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


def _build_user_summary(db: Session, user: User) -> KarTrackerUserSummaryResponse:
    user_role = get_user_role(db, user.id)
    role = db.get(KarTrackerRole, user_role.role_id) if user_role else None
    return KarTrackerUserSummaryResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id if role else None,
        role_name=role.name if role else None,
    )


@router.get("/users", response_model=list[KarTrackerUserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.users", "view")),
) -> list[KarTrackerUserSummaryResponse]:
    """List every user with access to KarTracker, and their current role."""
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    users_with_access = db.scalars(
        select(User)
        .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
        .where(UserModuleAccess.module_id == module.id)
        .order_by(User.display_name)
    ).all()
    return [_build_user_summary(db, user) for user in users_with_access]


@router.put("/users/{user_id}/role", response_model=KarTrackerUserSummaryResponse)
def set_user_role(
    user_id: int,
    payload: SetUserRoleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.users", "edit")),
) -> KarTrackerUserSummaryResponse:
    """Assign (or, if role_id is null, remove) a KarTracker role for a user
    who already has access to KarTracker.
    """
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(UserModuleAccess.user_id == user_id, UserModuleAccess.module_id == module.id)
    )
    if has_access is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to KarTracker")

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(KarTrackerRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(KarTrackerUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=KarTrackerUserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.users", "create")),
) -> KarTrackerUserSummaryResponse:
    """Give someone access to KarTracker, creating their account first if
    they don't already have one anywhere in RW Crew.

    This ALWAYS grants access to KarTracker only — never any other module —
    regardless of who calls it, which is what keeps a KarTracker admin (not
    just the super admin) safely able to onboard people on their own.
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
        role = db.get(KarTrackerRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(KarTrackerUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which KarTracker screens the current user can view
    and create on, so it knows what to show — sidebar links, and
    finer-grained controls like the Data Upload/Download screen's upload
    button — without duplicating the permission-checking rules itself.
    """
    screens = db.scalars(select(KarTrackerScreen)).all()
    viewable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "view")]
    creatable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "create")]
    editable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "edit")]
    return MyPermissionsResponse(
        viewable_screen_keys=viewable_keys,
        creatable_screen_keys=creatable_keys,
        editable_screen_keys=editable_keys,
    )


@router.get("/kar-statuses", response_model=list[KarStatusResponse])
def list_kar_statuses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karstatuses", "view")),
) -> list[KarTrackerKarStatus]:
    """List every kar status, for the KarStatussen screen and the
    KarManagement status dropdown alike.
    """
    return list(db.scalars(select(KarTrackerKarStatus).order_by(KarTrackerKarStatus.name)).all())


@router.post("/kar-statuses", response_model=KarStatusResponse, status_code=status.HTTP_201_CREATED)
def create_kar_status(
    payload: KarStatusCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karstatuses", "create")),
) -> KarTrackerKarStatus:
    """Create a brand-new kar status."""
    new_status = KarTrackerKarStatus(name=payload.name)
    db.add(new_status)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A kar status with this name already exists"
        ) from error

    db.refresh(new_status)
    return new_status


@router.put("/kar-statuses/{kar_status_id}", response_model=KarStatusResponse)
def rename_kar_status(
    kar_status_id: int,
    payload: KarStatusUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karstatuses", "edit")),
) -> KarTrackerKarStatus:
    """Rename an existing kar status."""
    kar_status = db.get(KarTrackerKarStatus, kar_status_id)
    if kar_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kar status not found")

    kar_status.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A kar status with this name already exists"
        ) from error

    db.refresh(kar_status)
    return kar_status


@router.delete("/kar-statuses/{kar_status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kar_status(
    kar_status_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karstatuses", "delete")),
) -> None:
    """Delete a kar status, as long as no kar is still using it."""
    kar_status = db.get(KarTrackerKarStatus, kar_status_id)
    if kar_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kar status not found")

    still_in_use = db.scalar(select(KarTrackerKar).where(KarTrackerKar.status_id == kar_status_id))
    if still_in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This kar status is still used by at least one kar"
        )

    db.delete(kar_status)
    db.commit()


def _validate_kar_lookup_ids(db: Session, status_id: int, transport_type_id: int, team_id: int | None) -> None:
    """Turn a bad status_id/transport_type_id/team_id into a friendly 404
    instead of letting the database reject it with a raw foreign-key error.
    team_id is optional, so it's only checked when one was actually given.
    """
    if db.get(KarTrackerKarStatus, status_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kar status not found")
    if db.get(Product, transport_type_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport type not found")
    if team_id is not None and db.get(Team, team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")


@router.get("/karren", response_model=list[KarResponse])
def list_karren(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karmanagement", "view")),
) -> list[KarTrackerKar]:
    """List every kar in the fleet registry."""
    return list(db.scalars(select(KarTrackerKar).order_by(KarTrackerKar.kar_nummer)).all())


@router.post("/karren", response_model=KarResponse, status_code=status.HTTP_201_CREATED)
def create_kar(
    payload: KarCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karmanagement", "create")),
) -> KarTrackerKar:
    """Register a brand-new kar."""
    _validate_kar_lookup_ids(db, payload.status_id, payload.transport_type_id, payload.team_id)

    new_kar = KarTrackerKar(**payload.model_dump())
    db.add(new_kar)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A kar with this kar number already exists"
        ) from error

    db.refresh(new_kar)
    return new_kar


@router.put("/karren/{kar_id}", response_model=KarResponse)
def update_kar(
    kar_id: int,
    payload: KarUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karmanagement", "edit")),
) -> KarTrackerKar:
    """Update an existing kar's details."""
    kar = db.get(KarTrackerKar, kar_id)
    if kar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kar not found")

    _validate_kar_lookup_ids(db, payload.status_id, payload.transport_type_id, payload.team_id)

    for field, value in payload.model_dump().items():
        setattr(kar, field, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A kar with this kar number already exists"
        ) from error

    db.refresh(kar)
    return kar


@router.delete("/karren/{kar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kar(
    kar_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karmanagement", "delete")),
) -> None:
    """Remove a kar from the fleet registry."""
    kar = db.get(KarTrackerKar, kar_id)
    if kar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kar not found")

    db.delete(kar)
    db.commit()


@router.get("/kar-planning", response_model=KarPlanningReportResponse)
def list_kar_planning(
    season_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karplanning", "view")),
) -> KarPlanningReportResponse:
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


@router.post("/kar-planning/print")
def print_kar_planning(
    payload: KarPlanningPrintRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karplanning", "view")),
) -> Response:
    """The Kar Planning "Print" button: one PDF page (a "karblad") per
    selected kar, in kar-number order. Each page lists, per active festival
    of the season, the afleverlocatie planned for the kar's team plus the
    festival's delivery/pick-up dates, and carries two QR codes (the kar
    number, and the public Intervention Request form prefilled for the team).
    A POST because the list of selected kar ids doesn't fit a URL.
    """
    season = db.get(Season, payload.season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")

    karren = db.execute(
        select(
            KarTrackerKar.kar_nummer,
            KarTrackerKar.team_id,
            Team.name.label("team_name"),
            Product.name.label("transport_type_name"),
        )
        .outerjoin(Team, Team.id == KarTrackerKar.team_id)
        .join(Product, Product.id == KarTrackerKar.transport_type_id)
        .where(KarTrackerKar.id.in_(payload.kar_ids))
        .order_by(KarTrackerKar.kar_nummer)
    ).all()
    if not karren:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No karren found")

    # The season's active festivals, earliest first (same order as the Kar
    # Planning columns), each with its optional delivery/pick-up dates.
    festival_rows = db.execute(
        select(Festival.id, Festival.name, KarTrackerLeverdatum.delivery_date, KarTrackerLeverdatum.pickup_date)
        .outerjoin(KarTrackerLeverdatum, KarTrackerLeverdatum.festival_id == Festival.id)
        .where(Festival.season_id == season.id, Festival.active.is_(True))
        .order_by(Festival.start_date, Festival.name)
    ).all()

    # (team_id, festival_id) -> planned location (with its zone and
    # distribution point), for the teams of the selected karren only.
    team_ids = {kar.team_id for kar in karren if kar.team_id is not None}
    plans: dict[tuple[int, int], dict[str, str | None]] = {}
    if team_ids and festival_rows:
        for plan in db.execute(
            select(
                KarTrackerKarAfleverlocatie.team_id,
                KarTrackerKarAfleverlocatie.festival_id,
                KarTrackerAfleverlocatie.name,
                KarTrackerAfleverlocatie.description,
                KarTrackerZone.name.label("zone_name"),
                KarTrackerDistributiepunt.name.label("distributiepunt_name"),
            )
            .join(
                KarTrackerAfleverlocatie,
                KarTrackerAfleverlocatie.id == KarTrackerKarAfleverlocatie.afleverlocatie_id,
            )
            .join(KarTrackerZone, KarTrackerZone.id == KarTrackerAfleverlocatie.zone_id)
            .join(
                KarTrackerDistributiepunt,
                KarTrackerDistributiepunt.id == KarTrackerAfleverlocatie.distributiepunt_id,
            )
            .where(
                KarTrackerKarAfleverlocatie.season_id == season.id,
                KarTrackerKarAfleverlocatie.team_id.in_(team_ids),
            )
        ):
            plans[(plan.team_id, plan.festival_id)] = {
                # "name — description", the same label the Kar Planning grid shows.
                "location": f"{plan.name} — {plan.description}" if plan.description else plan.name,
                "location_name": plan.name,
                "zone": plan.zone_name,
                "distributiepunt": plan.distributiepunt_name,
            }

    pages: list[KarbladData] = []
    for kar in karren:
        festivals: list[KarbladFestival] = []
        # The first festival with a planned location decides the page-level
        # zone, distribution point and the prefilled location of the QR link.
        first_plan: dict[str, str | None] | None = None
        for festival in festival_rows:
            plan = plans.get((kar.team_id, festival.id)) if kar.team_id is not None else None
            if plan is not None and first_plan is None:
                first_plan = plan
            festivals.append(
                KarbladFestival(
                    name=festival.name,
                    zone_name=plan["zone"] if plan else None,
                    location=plan["location"] if plan else None,
                    delivery_date=festival.delivery_date,
                    pickup_date=festival.pickup_date,
                )
            )
        pages.append(
            KarbladData(
                kar_nummer=kar.kar_nummer,
                team_name=kar.team_name,
                transport_type=kar.transport_type_name,
                festivals=festivals,
                aflever_zone=first_plan["zone"] if first_plan else None,
                distribution_point=first_plan["distributiepunt"] if first_plan else None,
                request_url=build_request_url(
                    payload.site_url,
                    payload.locale,
                    kar.team_id,
                    kar.kar_nummer,
                    first_plan["location_name"] if first_plan else None,
                    first_plan["zone"] if first_plan else None,
                ),
            )
        )

    pdf_bytes = build_karbladen_pdf(pages, season.name, payload.locale)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Karbladen_{date.today().isoformat()}.pdf"'},
    )


@router.get("/kar-map", response_model=KarMapResponse)
def list_kar_map(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karmap", "view")),
) -> KarMapResponse:
    """The Kar Map screen's data: every Kar/Afleverlocatie/Distributiepunt
    row, denormalized with the lookup names needed for each pin's popup.
    Gated by its own permission, independent of the underlying masterdata
    screens' own view permissions (same pattern as Kar Planning), so a role
    can be granted "see the map" without also getting CRUD rights on
    KarManagement/Afleverlocaties/Distributiepunten. Rows with no
    latitude/longitude are included too — the frontend excludes them from
    the map itself but still lists them in the side panel.
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


# The event site's ground plan is a single settings row (id=1), same
# "singleton" shape as Tagscan_settings — there is only ever one, upserted
# in place rather than versioned.
GROUNDPLAN_ROW_ID = 1
ALLOWED_GROUNDPLAN_CONTENT_TYPES = {"image/png", "image/jpeg"}
MAX_GROUNDPLAN_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB — plenty for a site map, keeps the row small.


def _groundplan_response(row: KarTrackerGroundplan | None) -> KarTrackerGroundplanResponse:
    if row is None:
        return KarTrackerGroundplanResponse(
            has_image=False, sw_latitude=None, sw_longitude=None, ne_latitude=None, ne_longitude=None
        )
    return KarTrackerGroundplanResponse(
        has_image=row.image_data is not None,
        sw_latitude=row.sw_latitude,
        sw_longitude=row.sw_longitude,
        ne_latitude=row.ne_latitude,
        ne_longitude=row.ne_longitude,
    )


@router.get("/groundplan", response_model=KarTrackerGroundplanResponse)
def get_groundplan(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_view_or_create("kartracker.karmap", "kartracker.groundplan")),
) -> KarTrackerGroundplanResponse:
    """The ground plan's current bounds/status — readable by anyone who can
    view either Kar Map (which overlays it) or the Grondplan screen itself.
    """
    return _groundplan_response(db.get(KarTrackerGroundplan, GROUNDPLAN_ROW_ID))


@router.get("/groundplan/image")
def get_groundplan_image(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_view_or_create("kartracker.karmap", "kartracker.groundplan")),
) -> Response:
    """The raw ground-plan image bytes, for direct use as an <img>/Leaflet
    ImageOverlay source. 404s until one has ever been uploaded.
    """
    row = db.get(KarTrackerGroundplan, GROUNDPLAN_ROW_ID)
    if row is None or row.image_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ground plan image set")
    return Response(content=row.image_data, media_type=row.image_content_type or "application/octet-stream")


@router.put("/groundplan", response_model=KarTrackerGroundplanResponse)
def update_groundplan(
    sw_latitude: float = Form(...),
    sw_longitude: float = Form(...),
    ne_latitude: float = Form(...),
    ne_longitude: float = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.groundplan", "edit")),
) -> KarTrackerGroundplanResponse:
    """Upsert the singleton ground-plan row. The image is optional on save
    so the corner coordinates can be recalibrated without re-uploading —
    only the coordinates are required on every save.
    """
    if sw_latitude >= ne_latitude or sw_longitude >= ne_longitude:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="South-west corner must be south and west of the north-east corner",
        )

    row = db.get(KarTrackerGroundplan, GROUNDPLAN_ROW_ID)
    if row is None:
        row = KarTrackerGroundplan(id=GROUNDPLAN_ROW_ID)
        db.add(row)

    if image is not None:
        if image.content_type not in ALLOWED_GROUNDPLAN_CONTENT_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be PNG or JPEG")
        # Read one byte past the limit so an oversized image is detected
        # without ever buffering an unbounded upload into memory.
        contents = image.file.read(MAX_GROUNDPLAN_IMAGE_BYTES + 1)
        if len(contents) > MAX_GROUNDPLAN_IMAGE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be smaller than 8 MB")
        row.image_data = contents
        row.image_content_type = image.content_type

    row.sw_latitude = sw_latitude
    row.sw_longitude = sw_longitude
    row.ne_latitude = ne_latitude
    row.ne_longitude = ne_longitude
    db.commit()

    return _groundplan_response(row)


# ---- Plan a kar ----------------------------------------------------------
# Per team, pick the afleverlocatie for every active festival of a season.
# KarTracker users don't necessarily have module-9 (master data)
# permissions, so the lookups the screen needs (teams, afleverlocaties,
# festivals) are served from here, gated by the screen's own permission —
# same approach as /kar-map.


@router.get("/plan-kar/teams", response_model=list[PlanKarOption])
def list_plan_kar_teams(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.plankar", "view")),
) -> list[PlanKarOption]:
    """The active teams offered in the team dropdown."""
    teams = db.execute(select(Team.id, Team.name).where(Team.active.is_(True)).order_by(Team.name)).all()
    return [PlanKarOption(id=team.id, name=team.name) for team in teams]


@router.get("/plan-kar/afleverlocaties", response_model=list[PlanKarAfleverlocatieOption])
def list_plan_kar_afleverlocaties(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.plankar", "view")),
) -> list[PlanKarAfleverlocatieOption]:
    """The active delivery locations offered in every row's dropdown, with
    their description so it can be shown next to the name.
    """
    locations = db.execute(
        select(KarTrackerAfleverlocatie.id, KarTrackerAfleverlocatie.name, KarTrackerAfleverlocatie.description)
        .where(KarTrackerAfleverlocatie.active.is_(True))
        .order_by(KarTrackerAfleverlocatie.name)
    ).all()
    return [
        PlanKarAfleverlocatieOption(id=location.id, name=location.name, description=location.description)
        for location in locations
    ]


@router.get("/plan-kar", response_model=PlanKarResponse)
def get_plan_kar(
    season_id: int,
    team_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.plankar", "view")),
) -> PlanKarResponse:
    """The matrix for one team in one season: every active festival of that
    season, each with the afleverlocatie already saved for it (or None).
    """
    if db.get(Season, season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    if db.get(Team, team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Outer join so festivals without a saved assignment still get a row.
    rows = db.execute(
        select(Festival.id, Festival.name, KarTrackerKarAfleverlocatie.afleverlocatie_id)
        .outerjoin(
            KarTrackerKarAfleverlocatie,
            (KarTrackerKarAfleverlocatie.festival_id == Festival.id)
            & (KarTrackerKarAfleverlocatie.season_id == season_id)
            & (KarTrackerKarAfleverlocatie.team_id == team_id),
        )
        .where(Festival.season_id == season_id, Festival.active.is_(True))
        .order_by(Festival.start_date, Festival.name)
    ).all()

    return PlanKarResponse(
        season_id=season_id,
        team_id=team_id,
        rows=[
            PlanKarFestivalRow(festival_id=row.id, festival_name=row.name, afleverlocatie_id=row.afleverlocatie_id)
            for row in rows
        ],
    )


@router.put("/plan-kar", response_model=PlanKarResponse)
def save_plan_kar(
    payload: PlanKarSaveRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.plankar", "edit")),
) -> PlanKarResponse:
    """Save the whole matrix for one team in one season. Each row is an
    upsert on (season, festival, team): an existing record is updated, a
    missing one inserted, and a row with no location clears its record.
    """
    if db.get(Season, payload.season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    team = db.get(Team, payload.team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if not team.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team is not active")

    # The same festival can't appear twice in one save.
    festival_ids = [row.festival_id for row in payload.rows]
    if len(set(festival_ids)) != len(festival_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A festival appears more than once")

    # Every festival must be an active one of this season.
    valid_festival_ids = set(
        db.scalars(
            select(Festival.id).where(
                Festival.id.in_(festival_ids), Festival.season_id == payload.season_id, Festival.active.is_(True)
            )
        ).all()
    )
    if valid_festival_ids != set(festival_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Every festival must be an active festival of the season"
        )

    # Every chosen location must exist and be active.
    location_ids = {row.afleverlocatie_id for row in payload.rows if row.afleverlocatie_id is not None}
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

    # Existing assignments for this team+season, keyed by festival.
    existing_by_festival = {
        record.festival_id: record
        for record in db.scalars(
            select(KarTrackerKarAfleverlocatie).where(
                KarTrackerKarAfleverlocatie.season_id == payload.season_id,
                KarTrackerKarAfleverlocatie.team_id == payload.team_id,
            )
        ).all()
    }

    for row in payload.rows:
        existing = existing_by_festival.get(row.festival_id)
        if row.afleverlocatie_id is None:
            # No location chosen: remove any earlier assignment.
            if existing is not None:
                db.delete(existing)
        elif existing is not None:
            # Already registered: update in place, never add a second line.
            existing.afleverlocatie_id = row.afleverlocatie_id
        else:
            db.add(
                KarTrackerKarAfleverlocatie(
                    season_id=payload.season_id,
                    festival_id=row.festival_id,
                    team_id=payload.team_id,
                    afleverlocatie_id=row.afleverlocatie_id,
                )
            )

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not save the plan") from error

    return get_plan_kar(payload.season_id, payload.team_id, db, _user)


# ---- Delivery Dates ------------------------------------------------------
# Per active festival of a season, one delivery date and one pick-up date,
# stored in "Festivals_leverdatum" (at most one row per festival).


@router.get("/leverdata", response_model=LeverdatumResponse)
def get_leverdata(
    season_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.leverdata", "view")),
) -> LeverdatumResponse:
    """Every active festival of the season, each with its saved dates (or None)."""
    if db.get(Season, season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")

    # Outer join so festivals without a saved row still get a line.
    rows = db.execute(
        select(Festival.id, Festival.name, KarTrackerLeverdatum.delivery_date, KarTrackerLeverdatum.pickup_date)
        .outerjoin(KarTrackerLeverdatum, KarTrackerLeverdatum.festival_id == Festival.id)
        .where(Festival.season_id == season_id, Festival.active.is_(True))
        .order_by(Festival.start_date, Festival.name)
    ).all()

    return LeverdatumResponse(
        season_id=season_id,
        rows=[
            LeverdatumRow(
                festival_id=row.id,
                festival_name=row.name,
                delivery_date=row.delivery_date,
                pickup_date=row.pickup_date,
            )
            for row in rows
        ],
    )


@router.put("/leverdata", response_model=LeverdatumResponse)
def save_leverdata(
    payload: LeverdatumSaveRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.leverdata", "edit")),
) -> LeverdatumResponse:
    """Save the whole table for one season. Each row is an upsert on the
    festival: an existing record is updated, a missing one inserted, and a
    row with no dates clears its record.
    """
    if db.get(Season, payload.season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")

    # The same festival can't appear twice in one save.
    festival_ids = [row.festival_id for row in payload.rows]
    if len(set(festival_ids)) != len(festival_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A festival appears more than once")

    # Every festival must be an active one of this season.
    valid_festival_ids = set(
        db.scalars(
            select(Festival.id).where(
                Festival.id.in_(festival_ids), Festival.season_id == payload.season_id, Festival.active.is_(True)
            )
        ).all()
    )
    if valid_festival_ids != set(festival_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Every festival must be an active festival of the season"
        )

    # The pick-up can't be before the delivery (only checkable when both are set).
    for row in payload.rows:
        if row.delivery_date and row.pickup_date and row.pickup_date < row.delivery_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="The pick-up date can't be before the delivery date"
            )

    # Existing records for these festivals, keyed by festival.
    existing_by_festival = {
        record.festival_id: record
        for record in db.scalars(
            select(KarTrackerLeverdatum).where(KarTrackerLeverdatum.festival_id.in_(festival_ids))
        ).all()
    }

    for row in payload.rows:
        existing = existing_by_festival.get(row.festival_id)
        if row.delivery_date is None and row.pickup_date is None:
            # No dates given: remove any earlier record.
            if existing is not None:
                db.delete(existing)
        elif existing is not None:
            # Already registered: update in place, never add a second line.
            existing.delivery_date = row.delivery_date
            existing.pickup_date = row.pickup_date
        else:
            db.add(
                KarTrackerLeverdatum(
                    festival_id=row.festival_id, delivery_date=row.delivery_date, pickup_date=row.pickup_date
                )
            )

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not save the delivery dates") from error

    return get_leverdata(payload.season_id, db, _user)


@router.get("/kar-import/template")
def download_kar_import_template(
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-registering new karren."""
    return Response(
        content=build_kar_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="kar-import-template.xlsx"'},
    )


@router.post("/kar-import", response_model=KarImportResponse)
def import_karren(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "create")),
) -> KarImportResponse:
    """Bulk-register new karren from an uploaded XLSX workbook. A row whose
    kar_nummer already exists is reported as an error, not upserted.
    """
    results = import_karren_from_xlsx(db, file.file.read())
    return KarImportResponse(results=results)


@router.get("/karren/export")
def export_karren(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The full KarTracker dataset (karren + kar statuses) as an XLSX workbook."""
    return Response(
        content=export_karren_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="kartracker-export.xlsx"'},
    )


@router.get("/kar-status-import/template")
def download_kar_status_import_template(
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-registering new kar statuses."""
    return Response(
        content=build_kar_status_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="kar-status-import-template.xlsx"'},
    )


@router.post("/kar-status-import", response_model=KarStatusImportResponse)
def import_kar_statuses(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "create")),
) -> KarStatusImportResponse:
    """Bulk-register new kar statuses from an uploaded XLSX workbook. A row
    naming a status that already exists is reported as an error, not upserted.
    """
    results = import_kar_statuses_from_xlsx(db, file.file.read())
    return KarStatusImportResponse(results=results)


@router.get("/kar-statuses/export")
def export_kar_statuses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """Every kar status as an XLSX workbook."""
    return Response(
        content=export_kar_statuses_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="kartracker-statuses-export.xlsx"'},
    )


def _validate_altsien_kernlid_id(db: Session, altsien_kernlid_id: int | None) -> None:
    """Turn a bad altsien_kernlid_id into a friendly 404 instead of letting
    the database reject it with a raw foreign-key error. Optional, so only
    checked when one was actually given.
    """
    if altsien_kernlid_id is not None and db.get(AltsienKernlid, altsien_kernlid_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Altsien Kernlid not found")


@router.get("/distributiepunten", response_model=list[DistributiepuntResponse])
def list_distributiepunten(
    db: Session = Depends(get_db),
    _user: User = Depends(
        require_screen_view_or_create("kartracker.distributiepunten", "kartracker.afleverlocaties")
    ),
) -> list[KarTrackerDistributiepunt]:
    """List every distribution point."""
    return list(db.scalars(select(KarTrackerDistributiepunt).order_by(KarTrackerDistributiepunt.name)).all())


@router.post("/distributiepunten", response_model=DistributiepuntResponse, status_code=status.HTTP_201_CREATED)
def create_distributiepunt(
    payload: DistributiepuntCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.distributiepunten", "create")),
) -> KarTrackerDistributiepunt:
    """Register a brand-new distribution point."""
    _validate_altsien_kernlid_id(db, payload.altsien_kernlid_id)

    new_distributiepunt = KarTrackerDistributiepunt(**payload.model_dump())
    db.add(new_distributiepunt)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A distribution point with this name already exists"
        ) from error

    db.refresh(new_distributiepunt)
    return new_distributiepunt


@router.put("/distributiepunten/{distributiepunt_id}", response_model=DistributiepuntResponse)
def update_distributiepunt(
    distributiepunt_id: int,
    payload: DistributiepuntUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.distributiepunten", "edit")),
) -> KarTrackerDistributiepunt:
    """Update an existing distribution point's details."""
    distributiepunt = db.get(KarTrackerDistributiepunt, distributiepunt_id)
    if distributiepunt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distribution point not found")

    _validate_altsien_kernlid_id(db, payload.altsien_kernlid_id)

    for field, value in payload.model_dump().items():
        setattr(distributiepunt, field, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A distribution point with this name already exists"
        ) from error

    db.refresh(distributiepunt)
    return distributiepunt


@router.delete("/distributiepunten/{distributiepunt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_distributiepunt(
    distributiepunt_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.distributiepunten", "delete")),
) -> None:
    """Remove a distribution point from the master data."""
    distributiepunt = db.get(KarTrackerDistributiepunt, distributiepunt_id)
    if distributiepunt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distribution point not found")

    still_in_use = db.scalar(
        select(KarTrackerAfleverlocatie).where(
            KarTrackerAfleverlocatie.distributiepunt_id == distributiepunt_id
        )
    )
    if still_in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This distribution point is still used by at least one delivery location",
        )

    db.delete(distributiepunt)
    db.commit()


@router.get("/distributiepunt-import/template")
def download_distributiepunt_import_template(
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-registering new distribution points."""
    return Response(
        content=build_distributiepunt_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="distributiepunt-import-template.xlsx"'},
    )


@router.post("/distributiepunt-import", response_model=DistributiepuntImportResponse)
def import_distributiepunten(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "create")),
) -> DistributiepuntImportResponse:
    """Bulk-register new distribution points from an uploaded XLSX
    workbook. A row whose name already exists is reported as an error,
    not upserted.
    """
    results = import_distributiepunten_from_xlsx(db, file.file.read())
    return DistributiepuntImportResponse(results=results)


@router.get("/distributiepunten/export")
def export_distributiepunten(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The full Distributiepunten dataset as an XLSX workbook."""
    return Response(
        content=export_distributiepunten_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="distributiepunten-export.xlsx"'},
    )


@router.get("/zones", response_model=list[ZoneResponse])
def list_zones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_view_or_create("kartracker.zones", "kartracker.afleverlocaties")),
) -> list[KarTrackerZone]:
    """List every zone."""
    return list(db.scalars(select(KarTrackerZone).order_by(KarTrackerZone.name)).all())


@router.post("/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: ZoneCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.zones", "create")),
) -> KarTrackerZone:
    """Create a brand-new zone."""
    new_zone = KarTrackerZone(name=payload.name)
    db.add(new_zone)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A zone with this name already exists") from error

    db.refresh(new_zone)
    return new_zone


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
def rename_zone(
    zone_id: int,
    payload: ZoneUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.zones", "edit")),
) -> KarTrackerZone:
    """Rename an existing zone."""
    zone = db.get(KarTrackerZone, zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    zone.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A zone with this name already exists") from error

    db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.zones", "delete")),
) -> None:
    """Delete a zone, as long as no delivery location is still using it."""
    zone = db.get(KarTrackerZone, zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    still_in_use = db.scalar(select(KarTrackerAfleverlocatie).where(KarTrackerAfleverlocatie.zone_id == zone_id))
    if still_in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This zone is still used by at least one delivery location"
        )

    db.delete(zone)
    db.commit()


@router.get("/zone-import/template")
def download_zone_import_template(
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-registering new zones."""
    return Response(
        content=build_zone_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="zone-import-template.xlsx"'},
    )


@router.post("/zone-import", response_model=ZoneImportResponse)
def import_zones(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "create")),
) -> ZoneImportResponse:
    """Bulk-register new zones from an uploaded XLSX workbook. A row naming
    a zone that already exists is reported as an error, not upserted.
    """
    results = import_zones_from_xlsx(db, file.file.read())
    return ZoneImportResponse(results=results)


@router.get("/zones/export")
def export_zones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """Every zone as an XLSX workbook."""
    return Response(
        content=export_zones_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="zones-export.xlsx"'},
    )


def _validate_afleverlocatie_lookup_ids(db: Session, zone_id: int, distributiepunt_id: int, altsien_kernlid_id: int | None) -> None:
    """Turn a bad zone_id/distributiepunt_id/altsien_kernlid_id into a
    friendly 404 instead of letting the database reject it with a raw
    foreign-key error. altsien_kernlid_id is optional, so it's only
    checked when one was actually given.
    """
    if db.get(KarTrackerZone, zone_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    if db.get(KarTrackerDistributiepunt, distributiepunt_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distribution point not found")
    _validate_altsien_kernlid_id(db, altsien_kernlid_id)


@router.get("/afleverlocaties", response_model=list[AfleverlocatieResponse])
def list_afleverlocaties(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.afleverlocaties", "view")),
) -> list[KarTrackerAfleverlocatie]:
    """List every delivery location."""
    return list(db.scalars(select(KarTrackerAfleverlocatie).order_by(KarTrackerAfleverlocatie.name)).all())


@router.post("/afleverlocaties", response_model=AfleverlocatieResponse, status_code=status.HTTP_201_CREATED)
def create_afleverlocatie(
    payload: AfleverlocatieCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.afleverlocaties", "create")),
) -> KarTrackerAfleverlocatie:
    """Register a brand-new delivery location."""
    _validate_afleverlocatie_lookup_ids(db, payload.zone_id, payload.distributiepunt_id, payload.altsien_kernlid_id)

    new_afleverlocatie = KarTrackerAfleverlocatie(**payload.model_dump())
    db.add(new_afleverlocatie)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A delivery location with this name already exists"
        ) from error

    db.refresh(new_afleverlocatie)
    return new_afleverlocatie


@router.put("/afleverlocaties/{afleverlocatie_id}", response_model=AfleverlocatieResponse)
def update_afleverlocatie(
    afleverlocatie_id: int,
    payload: AfleverlocatieUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.afleverlocaties", "edit")),
) -> KarTrackerAfleverlocatie:
    """Update an existing delivery location's details."""
    afleverlocatie = db.get(KarTrackerAfleverlocatie, afleverlocatie_id)
    if afleverlocatie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery location not found")

    _validate_afleverlocatie_lookup_ids(db, payload.zone_id, payload.distributiepunt_id, payload.altsien_kernlid_id)

    for field, value in payload.model_dump().items():
        setattr(afleverlocatie, field, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A delivery location with this name already exists"
        ) from error

    db.refresh(afleverlocatie)
    return afleverlocatie


@router.delete("/afleverlocaties/{afleverlocatie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_afleverlocatie(
    afleverlocatie_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.afleverlocaties", "delete")),
) -> None:
    """Remove a delivery location from the master data."""
    afleverlocatie = db.get(KarTrackerAfleverlocatie, afleverlocatie_id)
    if afleverlocatie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery location not found")

    # A location still referenced by a "Plan a kar" assignment can't be
    # removed — deactivating it is the way to retire it.
    still_planned = db.scalar(
        select(KarTrackerKarAfleverlocatie).where(KarTrackerKarAfleverlocatie.afleverlocatie_id == afleverlocatie_id)
    )
    if still_planned is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This delivery location is still used by a kar plan; deactivate it instead",
        )

    db.delete(afleverlocatie)
    db.commit()


@router.get("/afleverlocatie-import/template")
def download_afleverlocatie_import_template(
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-registering new delivery locations."""
    return Response(
        content=build_afleverlocatie_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="afleverlocatie-import-template.xlsx"'},
    )


@router.post("/afleverlocatie-import", response_model=AfleverlocatieImportResponse)
def import_afleverlocaties(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "create")),
) -> AfleverlocatieImportResponse:
    """Bulk-register new delivery locations from an uploaded XLSX workbook.
    A row whose name already exists is reported as an error, not upserted.
    """
    results = import_afleverlocaties_from_xlsx(db, file.file.read())
    return AfleverlocatieImportResponse(results=results)


@router.get("/afleverlocaties/export")
def export_afleverlocaties(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.dataupload", "view")),
) -> Response:
    """The full Afleverlocatie dataset as an XLSX workbook."""
    return Response(
        content=export_afleverlocaties_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="afleverlocaties-export.xlsx"'},
    )
