# Schemas describing Tagscan's screens, custom roles, permissions, and the
# read-only file browser over its incoming-CSV folder.

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ScreenResponse(BaseModel):
    """One screen registered in the Tagscan module."""

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
    """One Tagscan role, with its full permission matrix."""

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


class TagscanUserSummaryResponse(BaseModel):
    """One user who has access to Tagscan, and their current role (if any)."""

    user_id: int
    email: str
    display_name: str
    role_id: int | None
    role_name: str | None


class SetUserRoleRequest(BaseModel):
    """What's sent to assign (or, if null, remove) a user's Tagscan role."""

    role_id: int | None


class CreateOrGrantUserRequest(BaseModel):
    """What a Tagscan admin sends to give someone access to Tagscan.

    If no user with this email exists yet, one is created using
    display_name/password (both required in that case). Either way, the
    resulting user is granted access to Tagscan ONLY, and optionally
    assigned the given role in the same step.
    """

    email: EmailStr
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8)
    role_id: int | None = None


class MyPermissionsResponse(BaseModel):
    """Which Tagscan screens the calling user is allowed to view — used by
    the frontend to decide what to show in the sidebar, without it having
    to know the full permission-checking rules itself.
    """

    viewable_screen_keys: list[str]


class FolderNode(BaseModel):
    """One folder in the CSV intake directory's tree, with its subfolders
    nested inside — used for the Dashboard screen's folder-tree pane.
    """

    name: str
    # Empty string for the root folder itself; otherwise a "/"-separated
    # path relative to the configured source folder.
    path: str
    children: list["FolderNode"] = Field(default_factory=list)


class FileEntryResponse(BaseModel):
    """One file inside a folder, for the Dashboard screen's file-list pane."""

    name: str
    path: str
    size_bytes: int
    modified_at: datetime


class FileContentResponse(BaseModel):
    """One file's text content, for the Dashboard screen's "notepad" preview pane."""

    path: str
    content: str
    # True if the file was larger than the preview cap and only partially read.
    truncated: bool
