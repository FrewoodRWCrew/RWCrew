# This is Atelier's (module-5) own router file. It used to call the shared,
# generic create_module_router() factory (see app/modules/common.py) for the
# "coming soon" placeholder; it now has its own custom-roles-with-per-screen-
# permissions system — the same one StockMaster (module-4) and the other
# modules have (see docs/module-custom-roles-pattern.md) — so every endpoint
# below is gated per-screen, per-action.
#
# Atelier is where the atelier team hands out festival clothing (T-shirts,
# hoodies, ...) at the start of a shift and takes it back afterwards. This file
# holds the access-rights screens plus the lookups every screen shares; the
# masterdata screens live in masterdata_router.py.

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_role import AtelierRole
from app.db.models.atelier_role_permission import AtelierRolePermission
from app.db.models.atelier_screen import AtelierScreen
from app.db.models.atelier_user_role import AtelierUserRole
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.help.routes import register_help_route
from app.modules.module_5.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    screen_keys_allowed,
)
from app.schemas.atelier import (
    CreateOrGrantUserRequest,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    SeasonSummaryResponse,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    UserSummaryResponse,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

# GET /help/pdf: the module's manual, with only the screens the user can view.
register_help_route(
    router,
    module_key=MODULE_KEY,
    require_access=require_module_access,
    viewable_screen_keys=lambda db, user: screen_keys_allowed(db, user, "view"),
)


# --- Screens, Roles, Users (access-rights screens) ------------------------
# The same endpoints as every other custom-roles module (copied from
# module_4/router.py), on Atelier's own tables.


def _build_role_response(db: Session, role: AtelierRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(AtelierScreen).order_by(AtelierScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(AtelierRolePermission).where(AtelierRolePermission.role_id == role.id)
        )
    }

    permission_rows = []
    for screen in screens:
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
    _user: User = Depends(require_screen_permission("atelier.roles", "view")),
) -> list[AtelierScreen]:
    """List every registered Atelier screen — the rows of the
    permission matrix on the Roles screen.
    """
    return list(db.scalars(select(AtelierScreen).order_by(AtelierScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("atelier.roles", "view")),
) -> list[RoleResponse]:
    """List every Atelier role, each with its full permission matrix."""
    roles = db.scalars(select(AtelierRole).order_by(AtelierRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("atelier.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = AtelierRole(name=payload.name)
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
    _user: User = Depends(require_screen_permission("atelier.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(AtelierRole, role_id)
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
    _user: User = Depends(require_screen_permission("atelier.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(AtelierRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(select(AtelierUserRole).where(AtelierUserRole.role_id == role_id))
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
    _user: User = Depends(require_screen_permission("atelier.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(AtelierRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(AtelierRolePermission).where(AtelierRolePermission.role_id == role_id)
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
                AtelierRolePermission(
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
    """One user with their current Atelier role (if any)."""
    user_role = get_user_role(db, user.id)
    role = db.get(AtelierRole, user_role.role_id) if user_role else None
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
    _user: User = Depends(require_screen_permission("atelier.users", "view")),
) -> list[UserSummaryResponse]:
    """List every user with access to Atelier, and their current role."""
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
    _user: User = Depends(require_screen_permission("atelier.users", "edit")),
) -> UserSummaryResponse:
    """Assign (or, if role_id is null, remove) an Atelier role for a user
    who already has access to Atelier.
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to Atelier"
        )

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(AtelierRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(AtelierUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=UserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("atelier.users", "create")),
) -> UserSummaryResponse:
    """Give someone access to Atelier, creating their account first if
    they don't already have one anywhere in RW Crew. This ALWAYS grants
    access to Atelier only — never any other module.
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
        role = db.get(AtelierRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(AtelierUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which Atelier screens the current user can
    view / create on / edit / delete on, so it knows which menu items and
    buttons to show.
    """
    return MyPermissionsResponse(
        viewable_screen_keys=screen_keys_allowed(db, current_user, "view"),
        creatable_screen_keys=screen_keys_allowed(db, current_user, "create"),
        editable_screen_keys=screen_keys_allowed(db, current_user, "edit"),
        deletable_screen_keys=screen_keys_allowed(db, current_user, "delete"),
    )


# --- Lookups and pictures (every Atelier user) ---------------------------------


@router.get("/seasons", response_model=list[SeasonSummaryResponse])
def list_seasons(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[Season]:
    """Every season (open and closed) for the module's own season dropdown."""
    return list(db.scalars(select(Season).order_by(Season.name)).all())


@router.get("/articles/{article_id}/image")
def get_article_image(
    article_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> Response:
    """An article's picture — plain module access, so every Atelier screen
    can show it. Changing it lives in masterdata_router.py.
    """
    article = db.get(AtelierArticle, article_id)
    if article is None or article.image_data is None or article.image_content_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article has no image")
    return Response(content=article.image_data, media_type=article.image_content_type)
