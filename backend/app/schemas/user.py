# Schemas describing user accounts, used by the admin "manage users" and
# "manage access" screens.

from pydantic import BaseModel, EmailStr, Field, field_validator


def _blank_to_none(value: str | None) -> str | None:
    """Trim a phone number; an empty/whitespace-only one means "no phone"."""
    if value is None:
        return None
    value = value.strip()
    return value or None


class UserCreateRequest(BaseModel):
    """What an admin sends us to create a brand-new user account."""

    email: EmailStr
    # The temporary password the admin sets for this new user. Kept short
    # here (min length only) — real strength rules can be tightened later.
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=255)
    is_super_admin: bool = False
    is_altsien_kernlid: bool = False
    phone: str | None = Field(default=None, max_length=255)

    _trim_phone = field_validator("phone")(_blank_to_none)


class UserUpdateRequest(BaseModel):
    """What an admin sends us to change a user's flags/phone. Only the
    fields that are present are changed."""

    is_super_admin: bool | None = None
    is_altsien_kernlid: bool | None = None
    # Sending an empty string clears the phone number.
    phone: str | None = Field(default=None, max_length=255)

    _trim_phone = field_validator("phone")(_blank_to_none)


class AltsienKernlidResponse(BaseModel):
    """One flagged user, as offered in the Teams/Distributiepunt/Afleverlocatie pickers."""

    id: int
    display_name: str
    email: str
    phone: str | None


class UserSummaryResponse(BaseModel):
    """A short summary of one user, used in admin list/table screens."""

    id: int
    email: str
    display_name: str
    is_super_admin: bool
    is_altsien_kernlid: bool
    phone: str | None
    is_active: bool
    # Every module key (e.g. "module-1") this user currently has access to.
    accessible_module_keys: list[str]
