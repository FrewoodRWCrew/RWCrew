# Small helper functions for working out module access, shared by several
# routers (auth "who am I" endpoint, the admin access screen, and the
# per-module placeholder pages).

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.module import Module
from app.db.models.user_module_access import UserModuleAccess


def get_accessible_module_keys(db: Session, user_id: int) -> list[str]:
    """Return the keys of every module this user is currently allowed to open.

    A module only counts if it is switched on site-wide (Module.is_active)
    AND the user has an explicit access grant from the super admin. This
    applies equally to the super admin themselves — being super admin only
    grants the power to hand out access via the "Manage Access" screen, it
    does not automatically open every module's tile. If the super admin
    wants to open a module, they grant themselves access the same way they
    would for anyone else.
    """
    statement = (
        select(Module.key)
        .join(UserModuleAccess, UserModuleAccess.module_id == Module.id)
        .where(UserModuleAccess.user_id == user_id, Module.is_active.is_(True))
    )

    return list(db.scalars(statement).all())
