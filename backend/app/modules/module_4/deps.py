# This file defines the "can this user do that?" checks used by every
# StockMaster endpoint. StockMaster doesn't use the shared, generic
# app/modules/common.py factory: like Altsien Select (module_8/deps.py) it
# has custom roles with a separate view/create/edit/delete switch per
# screen (see docs/module-custom-roles-pattern.md). On top of that it
# decides whether a season is still open for bookings.

from typing import Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.stockmaster_role_permission import StockMasterRolePermission
from app.db.models.stockmaster_screen import StockMasterScreen
from app.db.models.stockmaster_user_role import StockMasterUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.landing.deps import get_current_user

MODULE_KEY = "module-4"
MODULE_LABEL = "StockMaster"

# The four actions a role's permission on a screen can be checked for.
PermissionAction = Literal["view", "create", "edit", "delete"]

# The switch-screen whose "edit" right allows booking in a closed season.
CLOSED_SEASON_SCREEN_KEY = "stockmaster.closedseason"


def require_module_access(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> User:
    """Only let the request through if the user has been granted access to
    StockMaster at all (super admins are not automatically exempt —
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


def get_user_role(db: Session, user_id: int) -> StockMasterUserRole | None:
    """Look up the user's current StockMaster role assignment, if any."""
    return db.scalar(select(StockMasterUserRole).where(StockMasterUserRole.user_id == user_id))


def get_permission_for_screen(db: Session, role_id: int, screen_id: int) -> StockMasterRolePermission | None:
    """Look up one role's permissions row for one screen. None simply means
    "no access", the same as every flag being False.
    """
    return db.scalar(
        select(StockMasterRolePermission).where(
            StockMasterRolePermission.role_id == role_id,
            StockMasterRolePermission.screen_id == screen_id,
        )
    )


def user_can(db: Session, user: User, screen_key: str, action: PermissionAction) -> bool:
    """The actual yes/no permission check, reused by require_screen_permission
    (below), the booking endpoints and the "my permissions" endpoint.
    """
    if user.is_super_admin:
        # The site-wide super admin can always do anything in StockMaster —
        # this is what lets them bootstrap the module's very first role.
        return True

    screen = db.scalar(select(StockMasterScreen).where(StockMasterScreen.key == screen_key))
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
    """The keys of every StockMaster screen this user may perform `action`
    on — used by "my permissions" and by the help manual (only the screens
    the user can view get a chapter).
    """
    screens = db.scalars(select(StockMasterScreen)).all()
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


def require_any_screen_permission(*checks: tuple[str, PermissionAction]):
    """Like require_screen_permission, but passes when the caller has at
    least one of the given (screen, action) rights — e.g. a kar's contents
    are needed both on "Karren" and on "Benodigdheden".
    """

    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_module_access),
    ) -> User:
        if not any(user_can(db, current_user, screen_key, action) for screen_key, action in checks):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return current_user

    return dependency


# --- Season lock -----------------------------------------------------------


def get_season_or_404(db: Session, season_id: int) -> Season:
    """Load a season, or answer 404."""
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="season_not_found")
    return season


def season_is_editable_for(db: Session, user: User, season: Season) -> bool:
    """Bookings can be made while the season's period is open; afterwards
    only by someone with "edit" on the closed-season switch-screen.
    """
    return season.periode_open or user_can(db, user, CLOSED_SEASON_SCREEN_KEY, "edit")


def ensure_season_editable(db: Session, user: User, season: Season) -> None:
    """Refuse a booking once the season's period is closed (see above)."""
    if not season_is_editable_for(db, user, season):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="season_closed")
