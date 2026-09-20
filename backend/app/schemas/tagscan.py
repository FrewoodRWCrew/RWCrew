# Schemas describing Tagscan's screens, custom roles, permissions, the
# read-only file browser over its incoming-CSV folder, and the
# TagManagement RFID tag registry.

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

RfidTagStatus = Literal["active", "inactive", "lost", "damaged", "retired"]

ScannerTechnology = Literal["Raspberry Pi 3", "Raspberry Pi 4", "Raspberry Pi 5", "Other"]


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


class RfidTagResponse(BaseModel):
    """One RFID tag, as shown on the TagManagement screen."""

    id: int
    epc_uid: str
    status: RfidTagStatus
    assigned_product_id: int | None
    assigned_serial_number: str | None
    date_registered: datetime
    date_assigned: date | None
    last_read_at: datetime | None
    last_reader_id: str | None
    last_location: str | None
    manufacturer: str | None
    batch_number: str | None
    notes_1: str | None
    notes_2: str | None
    notes_3: str | None
    notes_4: str | None
    notes_5: str | None


class RfidTagCreateRequest(BaseModel):
    """What's sent to register a brand-new RFID tag. Only the EPC/UID is
    required — every other field is optional, since a tag can be
    registered before it's assigned to a product or ever read by a
    reader.
    """

    epc_uid: str = Field(min_length=1, max_length=255)
    status: RfidTagStatus = "active"
    assigned_product_id: int | None = None
    assigned_serial_number: str | None = Field(default=None, max_length=255)
    date_assigned: date | None = None
    last_read_at: datetime | None = None
    last_reader_id: str | None = Field(default=None, max_length=255)
    last_location: str | None = Field(default=None, max_length=255)
    manufacturer: str | None = Field(default=None, max_length=255)
    batch_number: str | None = Field(default=None, max_length=255)
    notes_1: str | None = None
    notes_2: str | None = None
    notes_3: str | None = None
    notes_4: str | None = None
    notes_5: str | None = None

    @field_validator("epc_uid")
    @classmethod
    def _strip_epc_uid(cls, value: str) -> str:
        """A stray leading/trailing whitespace character (easy to pick up
        pasting from a spreadsheet) makes an otherwise-identical EPC
        silently fail to match against a scanned CSV line's own,
        already-stripped EPC — trim it here rather than ever storing it.
        """
        return value.strip()


class RfidTagUpdateRequest(RfidTagCreateRequest):
    """What's sent to update an existing tag — same shape as registering one."""


class ScannerResponse(BaseModel):
    """One registered scanner device, as shown on the Scanners screen."""

    id: int
    scanner: str
    type_id: int
    technology: ScannerTechnology
    location: str | None
    description: str | None
    info1: str | None
    info2: str | None
    info3: str | None
    # Device CSV-intake API key state — never the hash/plaintext itself,
    # just enough for the UI to show whether a key exists and was recently used.
    has_api_key: bool
    api_key_last_used_at: datetime | None


class ScannerCreateRequest(BaseModel):
    """What's sent to register a brand-new scanner device. scanner and
    type_id are required — a scanner must be named and classified before
    it can be registered.
    """

    scanner: str = Field(min_length=1, max_length=255)
    type_id: int
    technology: ScannerTechnology
    location: str | None = None
    description: str | None = None
    info1: str | None = None
    info2: str | None = None
    info3: str | None = None

    @field_validator("scanner")
    @classmethod
    def _strip_scanner(cls, value: str) -> str:
        """A stray leading/trailing whitespace character (easy to pick up
        pasting from a spreadsheet) makes an otherwise-identical scanner
        name silently fail to match against a scanned CSV line's own,
        already-stripped Scanner value — trim it here rather than ever
        storing it.
        """
        return value.strip()


class ScannerUpdateRequest(ScannerCreateRequest):
    """What's sent to update an existing scanner — same shape as registering one."""


class ScannerApiKeyResponse(BaseModel):
    """The brand-new plaintext API key for a scanner, returned exactly
    once at generation time — it can never be retrieved again afterward,
    only the hash is stored (see Scanner.api_key_hash).
    """

    api_key: str


class TagscanSettingsResponse(BaseModel):
    """TagScan's module-wide settings, as shown on the Settings screen."""

    receive_folder_path: str
    # Whether receive_folder_path is a DB-saved override, or just the
    # .env-configured default shown because nothing's been saved yet.
    is_override: bool


class TagscanSettingsUpdateRequest(BaseModel):
    """What's sent to save a new receive-folder-path override."""

    receive_folder_path: str = Field(min_length=1)

    @field_validator("receive_folder_path")
    @classmethod
    def _strip_path(cls, value: str) -> str:
        return value.strip()


class IntakeUploadResponse(BaseModel):
    """The result of one device CSV upload — "duplicate" is a success
    outcome (the file was already received earlier), not an error, so a
    retried upload after a dropped response is always safe.
    """

    status: Literal["received", "duplicate"]
    filename: str


class RfidTagImportRowResult(BaseModel):
    """What happened to one row of an uploaded CSV import."""

    row_number: int
    epc_uid: str | None
    outcome: Literal["created", "updated", "error"]
    detail: str | None


class RfidTagImportResponse(BaseModel):
    """The full outcome of a CSV import — one result per row, in order."""

    results: list[RfidTagImportRowResult]


class TagStatusBreakdownItem(BaseModel):
    """How many tags are in one status — one entry per fixed status value,
    for the dashboard's "Tags by Status" donut.
    """

    status: RfidTagStatus
    count: int


class TagWeeklyRegistrationItem(BaseModel):
    """How many tags were registered in one ISO week (Monday start), for
    the dashboard's "Tags Registered Over Time" chart.
    """

    week_start: date
    count: int


class TagTopProductItem(BaseModel):
    """One product and how many tags are currently assigned to it, for
    the dashboard's "Top Products by Tag Count" chart.
    """

    product_name: str
    tag_count: int


class TagDashboardResponse(BaseModel):
    """Aggregate KPI stats for TagScan's landing dashboard."""

    total_tags: int
    unreaded_tags_count: int
    assigned_tags: int
    unassigned_tags: int
    lost_or_damaged_tags: int
    registered_this_month: int
    status_breakdown: list[TagStatusBreakdownItem]
    registrations_by_week: list[TagWeeklyRegistrationItem]
    top_products: list[TagTopProductItem]


class TagHeaderDataResponse(BaseModel):
    """One CSV file logged by the "Tag Headerdata" screen's scan."""

    id: int
    filename: str
    created_at: datetime
    line_count: int
    # The raw "Scanner" CSV value for this file, and — when it matches a
    # registered Scanners device by name — a snapshot of that device's key
    # fields (null scanner_id means no match was found).
    scanner: str | None
    scanner_id: int | None
    scanner_name: str | None
    scanner_location: str | None
    scanner_technology: str | None
    # The file's "Mode" and "Action" CSV values (first non-empty per file).
    mode: str | None
    action: str | None


class TagHeaderDataScanFileResult(BaseModel):
    """What happened to one file found in "Unreaded Tags" during a scan."""

    filename: str
    outcome: Literal["logged", "skipped_duplicate", "error"]
    detail: str | None = None


class TagHeaderDataScanResponse(BaseModel):
    """The full outcome of one "Scan" action — one result per file found,
    plus the resulting up-to-date list of every logged file so the
    frontend can refresh its table from a single response.
    """

    results: list[TagHeaderDataScanFileResult]
    entries: list[TagHeaderDataResponse]


TagLineStatus = Literal["converted", "no_match", "cancelled"]


class TagLineDataResponse(BaseModel):
    """One CSV data line processed by a Tag Headerdata scan, enriched with
    a snapshot of its matched tag (if any), for the Tag Linedata screen.
    """

    id: int
    header_data_id: int
    # Denormalized from the header row via a join, so the screen doesn't
    # need a second fetch just to show which file a line came from.
    header_filename: str
    line_number: int
    scanner: str | None
    epc: str
    rssi: int | None
    antenna: int | None
    count: int | None
    last_seen: str | None
    # The line's own "Mode"/"Action" CSV value, or its file's header value.
    mode: str | None
    action: str | None
    rfid_tag_id: int | None
    assigned_product_name: str | None
    assigned_serial_number: str | None
    manufacturer: str | None
    batch_number: str | None
    # Which registered Scanners device the raw "scanner" text matched, if
    # any — null means no match was found (soft match).
    scanner_id: int | None
    scanner_name: str | None
    scanner_location: str | None
    scanner_technology: str | None
    status: TagLineStatus
    created_at: datetime


class TagLineDataSyncResponse(BaseModel):
    """The outcome of one "Synchro" action: how many lines' match against
    TagManagement actually changed, plus the resulting up-to-date list of
    every line so the frontend can refresh its table from one response.
    """

    updated_count: int
    entries: list[TagLineDataResponse]
