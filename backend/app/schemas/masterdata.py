# Schemas describing MasterData's screens, custom roles, permissions, and
# the Season screen (the first actual piece of master data it manages).

from pydantic import BaseModel, EmailStr, Field


class ScreenResponse(BaseModel):
    """One screen registered in the MasterData module."""

    id: int
    key: str
    label: str
    sort_order: int


class ScreenPermissionResponse(BaseModel):
    """One role's permissions on one specific screen, for display in the
    permission-matrix grid (includes the screen's own details so the
    frontend doesn't need a separate lookup).
    """

    screen_id: int
    screen_key: str
    screen_label: str
    can_view: bool
    can_create: bool
    can_edit: bool
    can_delete: bool


class RoleResponse(BaseModel):
    """One MasterData role, with its full permission matrix."""

    id: int
    name: str
    permissions: list[ScreenPermissionResponse]


class RoleCreateRequest(BaseModel):
    """What's sent to create a brand-new, empty (no permissions yet) role."""

    name: str = Field(min_length=1, max_length=255)


class RoleUpdateRequest(BaseModel):
    """What's sent to rename an existing role."""

    name: str = Field(min_length=1, max_length=255)


class ScreenPermissionUpdate(BaseModel):
    """One screen's permissions, as sent when saving a role's whole matrix."""

    screen_id: int
    can_view: bool = False
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False


class SetRolePermissionsRequest(BaseModel):
    """Replace a role's entire permission matrix in one call — the
    complete, current state of every screen's checkboxes, the same
    "send everything" pattern used by the site-wide access checkboxes.
    """

    permissions: list[ScreenPermissionUpdate]


class MasterDataUserSummaryResponse(BaseModel):
    """One user who has access to MasterData, and their current role (if any)."""

    user_id: int
    email: str
    display_name: str
    role_id: int | None
    role_name: str | None


class SetUserRoleRequest(BaseModel):
    """What's sent to assign (or, if null, remove) a user's MasterData role."""

    role_id: int | None


class CreateOrGrantUserRequest(BaseModel):
    """What a MasterData admin sends to give someone access to MasterData.

    If no user with this email exists yet, one is created using
    display_name/password (both required in that case). Either way, the
    resulting user is granted access to MasterData ONLY, and optionally
    assigned the given role in the same step.
    """

    email: EmailStr
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8)
    role_id: int | None = None


class MyPermissionsResponse(BaseModel):
    """Which MasterData screens the calling user is allowed to view — used
    by the frontend to decide what to show in the sidebar, without it
    having to know the full permission-checking rules itself.
    """

    viewable_screen_keys: list[str]


class SeasonResponse(BaseModel):
    """One season, as shown on the Season screen."""

    id: int
    name: str


class SeasonCreateRequest(BaseModel):
    """What's sent to create a brand-new season."""

    name: str = Field(min_length=1, max_length=255)


class SeasonUpdateRequest(BaseModel):
    """What's sent to rename an existing season."""

    name: str = Field(min_length=1, max_length=255)


class ProductResponse(BaseModel):
    """One product, as shown on the Products screen."""

    id: int
    name: str
    type: str | None
    warehouse: str | None
    warehouse_location: str | None
    category: str | None
    is_consumable: bool
    is_blocked: bool
    is_logistics_product: bool
    limit_mode: str | None
    description: str | None


class ProductCreateRequest(BaseModel):
    """What's sent to create a brand-new product. Only the name is
    required — every other field is optional, matching how loosely
    defined they currently are (plain text, no fixed value list yet).
    """

    name: str = Field(min_length=1, max_length=255)
    type: str | None = Field(default=None, max_length=255)
    warehouse: str | None = Field(default=None, max_length=255)
    warehouse_location: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    is_consumable: bool = False
    is_blocked: bool = False
    is_logistics_product: bool = False
    limit_mode: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ProductUpdateRequest(ProductCreateRequest):
    """What's sent to update an existing product — same shape as creating one."""
