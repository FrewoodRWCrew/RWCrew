# This is KarTracker's own router file. Unlike modules 4-9 (which just call
# the shared create_module_router() factory), KarTracker needs its own
# custom-roles-with-per-screen-permissions system, so its endpoints are
# written out in full here — see docs/module-custom-roles-pattern.md.
#
# This is the module's first development phase: only the Access Rights
# scaffold (screens/roles/permissions/users) exists so far. The cart
# registry ("Karlijst") and delivery planning endpoints get added here
# alongside their own screen keys once that phase is designed.

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_role import KarTrackerRole
from app.db.models.kartracker_role_permission import KarTrackerRolePermission
from app.db.models.kartracker_screen import KarTrackerScreen
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_2.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    user_can,
)
from app.modules.module_2.kar_import import build_kar_template_xlsx, export_karren_to_xlsx, import_karren_from_xlsx
from app.modules.module_2.kar_status_import import (
    build_kar_status_template_xlsx,
    export_kar_statuses_to_xlsx,
    import_kar_statuses_from_xlsx,
)
from app.schemas.kartracker import (
    CreateOrGrantUserRequest,
    KarCreateRequest,
    KarImportResponse,
    KarResponse,
    KarStatusCreateRequest,
    KarStatusImportResponse,
    KarStatusResponse,
    KarStatusUpdateRequest,
    KarTrackerUserSummaryResponse,
    KarUpdateRequest,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
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
    return MyPermissionsResponse(viewable_screen_keys=viewable_keys, creatable_screen_keys=creatable_keys)


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
