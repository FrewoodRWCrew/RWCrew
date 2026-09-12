# Schemas describing KarTracker's screens, custom roles, and permissions —
# the "Access Rights" scaffold this module starts with — plus the Karlijst
# phase's KarStatus lookup and Kar (fleet registry) schemas. Delivery
# planning schemas get added here once that phase is designed.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ScreenResponse(BaseModel):
    """One screen registered in the KarTracker module."""

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
    """One KarTracker role, with its full permission matrix."""

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


class KarTrackerUserSummaryResponse(BaseModel):
    """One user who has access to KarTracker, and their current role (if any)."""

    user_id: int
    email: str
    display_name: str
    role_id: int | None
    role_name: str | None


class SetUserRoleRequest(BaseModel):
    """What's sent to assign (or, if null, remove) a user's KarTracker role."""

    role_id: int | None


class CreateOrGrantUserRequest(BaseModel):
    """What a KarTracker admin sends to give someone access to KarTracker.

    If no user with this email exists yet, one is created using
    display_name/password (both required in that case). Either way, the
    resulting user is granted access to KarTracker ONLY, and optionally
    assigned the given role in the same step.
    """

    email: EmailStr
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8)
    role_id: int | None = None


class MyPermissionsResponse(BaseModel):
    """Which KarTracker screens the calling user is allowed to view — used
    by the frontend to decide what to show in the sidebar, without it
    having to know the full permission-checking rules itself.
    """

    viewable_screen_keys: list[str]


class KarStatusResponse(BaseModel):
    """One status a kar can be in, as shown on the KarStatussen screen."""

    id: int
    name: str


class KarStatusCreateRequest(BaseModel):
    """What's sent to create a brand-new kar status."""

    name: str = Field(min_length=1, max_length=255)


class KarStatusUpdateRequest(BaseModel):
    """What's sent to rename an existing kar status — same shape as creating one."""

    name: str = Field(min_length=1, max_length=255)


class KarResponse(BaseModel):
    """One kar, as shown on the KarManagement screen."""

    id: int
    kar_nummer: str
    status_id: int
    team_id: int | None
    transport_type_id: int
    last_latitude: float | None
    last_longitude: float | None
    last_recorded_at: datetime | None


class KarCreateRequest(BaseModel):
    """What's sent to register a brand-new kar. status_id/transport_type_id
    must reference an existing row in their respective lookup tables
    (checked by the endpoint, not here); team_id, if given, must too.
    """

    kar_nummer: str = Field(min_length=1, max_length=50)
    status_id: int
    team_id: int | None = None
    transport_type_id: int
    last_latitude: float | None = None
    last_longitude: float | None = None
    last_recorded_at: datetime | None = None


class KarUpdateRequest(KarCreateRequest):
    """What's sent to update an existing kar — same shape as creating one."""


class KarImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk-import workbook. Unlike
    TagScan's tag import, there is no "updated" outcome — a kar_nummer that
    already exists is rejected as an error instead of being upserted.
    """

    row_number: int
    kar_nummer: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class KarImportResponse(BaseModel):
    """The full outcome of a bulk kar import — one result per row, in order."""

    results: list[KarImportRowResult]
