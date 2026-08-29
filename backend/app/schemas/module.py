# Schemas describing modules and module-level roles.

from pydantic import BaseModel

from app.db.models.module_role import ModuleRoleName


class ModuleResponse(BaseModel):
    """One module/tile, as shown on the landing page."""

    key: str
    name: str
    sort_order: int


class SetUserAccessRequest(BaseModel):
    """What the super admin sends to set exactly which modules a user can open.

    The list is the COMPLETE set of module keys this user should have
    access to afterwards — any module not in the list is removed, any
    module in the list that wasn't already granted is added. This keeps
    the "Manage Access" checkbox grid simple: it always sends the full,
    current state of the checkboxes for one user.
    """

    module_keys: list[str]


class ModuleRoleAssignmentResponse(BaseModel):
    """One user's role within one specific module."""

    user_id: int
    email: str
    display_name: str
    role: ModuleRoleName | None


class SetModuleRoleRequest(BaseModel):
    """What a module's own admin sends to set (or remove) a user's role."""

    # None means "remove this user's role in this module".
    role: ModuleRoleName | None
