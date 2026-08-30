# This file defines the "can this user do that?" checks used by every
# Tagscan endpoint. Tagscan doesn't use the shared, generic
# app/modules/common.py factory that modules 2-9 use, because it needs a
# richer permission model: custom roles with a separate view/create/edit/
# delete switch per screen, instead of one fixed admin/editor/reader role.

from typing import Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.module import Module
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.landing.deps import get_current_user

MODULE_KEY = "module-1"
MODULE_LABEL = "Tagscan"

# The four actions a role's permission on a screen can be checked for.
PermissionAction = Literal["view", "create", "edit", "delete"]


def require_module_access(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> User:
    """Only let the request through if the user has been granted access to
    Tagscan at all (super admins are not automatically exempt — matching
    every other module's behaviour, see app/shared/access.py).
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


def get_user_role(db: Session, user_id: int) -> TagscanUserRole | None:
    """Look up the calling user's current Tagscan role assignment, if any."""
    return db.scalar(select(TagscanUserRole).where(TagscanUserRole.user_id == user_id))


def get_permission_for_screen(db: Session, role_id: int, screen_id: int) -> TagscanRolePermission | None:
    """Look up one role's permissions row for one screen. Returns None if
    that role has never been given any permissions on that screen at all
    — which simply means "no access", the same as every flag being False.
    """
    return db.scalar(
        select(TagscanRolePermission).where(
            TagscanRolePermission.role_id == role_id, TagscanRolePermission.screen_id == screen_id
        )
    )


def user_can(db: Session, user: User, screen_key: str, action: PermissionAction) -> bool:
    """The actual yes/no permission check, reused by both
    require_screen_permission (below) and the "my permissions" endpoint.
    """
    if user.is_super_admin:
        # The site-wide super admin can always do anything in Tagscan —
        # this is what lets them bootstrap the module's very first role.
        return True

    screen = db.scalar(select(TagscanScreen).where(TagscanScreen.key == screen_key))
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
