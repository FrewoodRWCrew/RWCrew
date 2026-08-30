# This is Tagscan's own router file. Unlike modules 2-9 (which just call
# the shared create_module_router() factory), Tagscan needs its own
# custom-roles-with-per-screen-permissions system, so its endpoints are
# written out in full here.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.tagscan_role import TagscanRole
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_1.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    user_can,
)
from app.modules.module_1.file_browser import (
    build_folder_tree,
    get_source_root,
    list_files,
    read_file_preview,
    resolve_safe_path,
)
from app.schemas.tagscan import (
    CreateOrGrantUserRequest,
    FileContentResponse,
    FileEntryResponse,
    FolderNode,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    TagscanUserSummaryResponse,
)

router = APIRouter(prefix="/api/modules/module-1", tags=["Tagscan"])


def _build_role_response(db: Session, role: TagscanRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(TagscanScreen).order_by(TagscanScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(select(TagscanRolePermission).where(TagscanRolePermission.role_id == role.id))
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


@router.get("/files/tree", response_model=FolderNode)
def get_folder_tree(
    _user: User = Depends(require_screen_permission("tagscan.dashboard", "view")),
) -> FolderNode:
    """The full folder structure of the CSV intake directory, for the
    Dashboard screen's folder-tree pane.
    """
    return build_folder_tree(get_source_root())


@router.get("/files", response_model=list[FileEntryResponse])
def get_folder_files(
    path: str = "",
    _user: User = Depends(require_screen_permission("tagscan.dashboard", "view")),
) -> list[FileEntryResponse]:
    """The files directly inside one folder of the CSV intake directory
    (not its subfolders), for the Dashboard screen's file-list pane.
    """
    folder = resolve_safe_path(path)
    if not folder.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return list_files(folder)


@router.get("/files/content", response_model=FileContentResponse)
def get_file_content(
    path: str,
    _user: User = Depends(require_screen_permission("tagscan.dashboard", "view")),
) -> FileContentResponse:
    """One file's text content, for the Dashboard screen's "notepad" preview pane."""
    file = resolve_safe_path(path)
    if not file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    content, truncated = read_file_preview(file)
    return FileContentResponse(path=path, content=content, truncated=truncated)


@router.get("/screens", response_model=list[ScreenResponse])
def list_screens(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.roles", "view")),
) -> list[TagscanScreen]:
    """List every registered Tagscan screen — used to build the columns of
    the permission-matrix grid in the UI.
    """
    return list(db.scalars(select(TagscanScreen).order_by(TagscanScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.roles", "view")),
) -> list[RoleResponse]:
    """List every Tagscan role, each with its full permission matrix."""
    roles = db.scalars(select(TagscanRole).order_by(TagscanRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = TagscanRole(name=payload.name)
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
    _user: User = Depends(require_screen_permission("tagscan.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(TagscanRole, role_id)
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
    _user: User = Depends(require_screen_permission("tagscan.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(TagscanRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(select(TagscanUserRole).where(TagscanUserRole.role_id == role_id))
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
    _user: User = Depends(require_screen_permission("tagscan.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(TagscanRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(select(TagscanRolePermission).where(TagscanRolePermission.role_id == role_id))
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
                TagscanRolePermission(
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


def _build_user_summary(db: Session, user: User) -> TagscanUserSummaryResponse:
    user_role = get_user_role(db, user.id)
    role = db.get(TagscanRole, user_role.role_id) if user_role else None
    return TagscanUserSummaryResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id if role else None,
        role_name=role.name if role else None,
    )


@router.get("/users", response_model=list[TagscanUserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.users", "view")),
) -> list[TagscanUserSummaryResponse]:
    """List every user with access to Tagscan, and their current role."""
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    users_with_access = db.scalars(
        select(User)
        .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
        .where(UserModuleAccess.module_id == module.id)
        .order_by(User.display_name)
    ).all()
    return [_build_user_summary(db, user) for user in users_with_access]


@router.put("/users/{user_id}/role", response_model=TagscanUserSummaryResponse)
def set_user_role(
    user_id: int,
    payload: SetUserRoleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.users", "edit")),
) -> TagscanUserSummaryResponse:
    """Assign (or, if role_id is null, remove) a Tagscan role for a user
    who already has access to Tagscan.
    """
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(UserModuleAccess.user_id == user_id, UserModuleAccess.module_id == module.id)
    )
    if has_access is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to Tagscan")

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(TagscanRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(TagscanUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=TagscanUserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.users", "create")),
) -> TagscanUserSummaryResponse:
    """Give someone access to Tagscan, creating their account first if
    they don't already have one anywhere in RW Crew.

    This ALWAYS grants access to Tagscan only — never any other module —
    regardless of who calls it, which is what keeps a Tagscan admin (not
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
        role = db.get(TagscanRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(TagscanUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which Tagscan screens the current user can view,
    so it knows what to show in the sidebar without duplicating the
    permission-checking rules itself.
    """
    screens = db.scalars(select(TagscanScreen)).all()
    viewable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "view")]
    return MyPermissionsResponse(viewable_screen_keys=viewable_keys)
