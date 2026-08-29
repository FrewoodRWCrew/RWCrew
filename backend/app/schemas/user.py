# Schemas describing user accounts, used by the admin "manage users" and
# "manage access" screens.

from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    """What an admin sends us to create a brand-new user account."""

    email: EmailStr
    # The temporary password the admin sets for this new user. Kept short
    # here (min length only) — real strength rules can be tightened later.
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=255)
    is_super_admin: bool = False


class UserSummaryResponse(BaseModel):
    """A short summary of one user, used in admin list/table screens."""

    id: int
    email: str
    display_name: str
    is_super_admin: bool
    is_active: bool
    # Every module key (e.g. "module-1") this user currently has access to.
    accessible_module_keys: list[str]
