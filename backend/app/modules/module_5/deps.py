# This file defines the "can this user do that?" checks used by every
# Atelier endpoint. Atelier doesn't use the shared, generic
# app/modules/common.py factory: like StockMaster (module_4/deps.py) it
# has custom roles with a separate view/create/edit/delete switch per
# screen (see docs/module-custom-roles-pattern.md).

from typing import Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.atelier_role_permission import AtelierRolePermission
from app.db.models.atelier_screen import AtelierScreen
from app.db.models.atelier_user_role import AtelierUserRole
from app.db.models.module import Module
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.landing.deps import get_current_user

MODULE_KEY = "module-5"
MODULE_LABEL = "Atelier"

# The four actions a role's permission on a screen can be checked for.
PermissionAction = Literal["view", "create", "edit", "delete"]


def require_module_access(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> User:
    """Only let the request through if the user has been granted access to
    Atelier at all (super admins are not automatically exempt —
    matching every other module's behaviour, see app/shared/access.py).
    """
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{MODULE_LABEL} module not found")

    has_access = db.scalar(
        select(UserModuleAccess).where(
            UserModuleAccess.user_id == current_user.id, UserModuleAccess.module_id == module.id
        )
    )
    if has_access is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No access to {MODULE_LABEL}")

    return current_user


def get_user_role(db: Session, user_id: int) -> AtelierUserRole | None:
    """Look up the user's current Atelier role assignment, if any."""
    return db.scalar(select(AtelierUserRole).where(AtelierUserRole.user_id == user_id))


def get_permission_for_screen(db: Session, role_id: int, screen_id: int) -> AtelierRolePermission | None:
    """Look up one role's permissions row for one screen. None simply means
    "no access", the same as every flag being False.
    """
    return db.scalar(
        select(AtelierRolePermission).where(
            AtelierRolePermission.role_id == role_id,
            AtelierRolePermission.screen_id == screen_id,
        )
    )


def user_can(db: Session, user: User, screen_key: str, action: PermissionAction) -> bool:
    """The actual yes/no permission check, reused by require_screen_permission
    (below), the "my permissions" endpoint.
    """
    if user.is_super_admin:
        # The site-wide super admin can always do anything in Atelier —
        # this is what lets them bootstrap the module's very first role.
        return True

    screen = db.scalar(select(AtelierScreen).where(AtelierScreen.key == screen_key))
    if screen is None:
        return False

    user_role = get_user_role(db, user.id)
    if user_role is None:
        return False

    permission = get_permission_for_screen(db, user_role.role_id, screen.id)
    if permission is None:
        return False

    return {
        "view": permission.can_view,
        "create": permission.can_create,
        "edit": permission.can_edit,
        "delete": permission.can_delete,
    }[action]


def screen_keys_allowed(db: Session, user: User, action: PermissionAction) -> list[str]:
    """The keys of every Atelier screen this user may perform `action`
    on — used by "my permissions" and by the help manual (only the screens
    the user can view get a chapter).
    """
    screens = db.scalars(select(AtelierScreen)).all()
    return [screen.key for screen in screens if user_can(db, user, screen.key, action)]


def require_screen_permission(screen_key: str, action: PermissionAction):
    """Build a dependency that only lets a request through if the caller
    can perform "action" on the screen identified by "screen_key".
    """

    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_module_access),
    ) -> User:
        if not user_can(db, current_user, screen_key, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Not allowed to {action} on {screen_key}"
            )
        return current_user

    return dependency


def require_view_on_any(*screen_keys: str):
    """Build a dependency that lets a request through when the caller may
    view at least one of these screens — for lists several screens need
    (e.g. the sizes for both Maten and the article form)."""

    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_module_access),
    ) -> User:
        if not any(user_can(db, current_user, key, "view") for key in screen_keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Not allowed to view on {' / '.join(screen_keys)}"
            )
        return current_user

    return dependency
