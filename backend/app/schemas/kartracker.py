# Schemas describing KarTracker's screens, custom roles, and permissions —
# the "Access Rights" scaffold this module starts with — plus the Karlijst
# phase's KarStatus lookup and Kar (fleet registry) schemas. Delivery
# planning schemas get added here once that phase is designed.

from datetime import date, datetime
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
    """Which KarTracker screens the calling user is allowed to view, and on
    which of those they're also allowed to create — used by the frontend
    to decide what to show (sidebar links, and finer-grained controls like
    the Data Upload/Download screen's upload button) without it having to
    know the full permission-checking rules itself.
    """

    viewable_screen_keys: list[str]
    creatable_screen_keys: list[str]
    editable_screen_keys: list[str]


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


class KarPlanningResponse(BaseModel):
    """One kar, denormalized by joining KarManagement with its status/team/
    transport-type lookups — the first query in what will grow into a
    wider, multi-table Kar Planning report as more tables are added.
    """

    id: int
    kar_nummer: str
    status_name: str
    team_name: str | None
    transport_type_name: str
    # Festival id -> label ("name — description", or just the name) of the
    # afleverlocatie planned for this kar's team at that festival. Festivals
    # with nothing planned (or a kar without a team) are absent from the dict.
    afleverlocaties: dict[int, str]
    geolocation: str | None


class KarPlanningFestivalResponse(BaseModel):
    """One festival column of the Kar Planning report."""

    id: int
    name: str


class KarPlanningReportResponse(BaseModel):
    """The whole Kar Planning report: the active festivals of the requested
    season (one extra table column each, in start-date order) plus one row
    per kar. `festivals` is empty when no season was requested.
    """

    festivals: list[KarPlanningFestivalResponse]
    rows: list[KarPlanningResponse]


class KarPlanningPrintRequest(BaseModel):
    """What the Kar Planning "Print" button sends: which karren to print a
    karblad for, in which season, plus the public site address the QR code
    of each page should point to (the browser knows it, the API doesn't).
    """

    season_id: int
    # A page per kar; capped so a single request can't ask for an absurd PDF.
    kar_ids: list[int] = Field(min_length=1, max_length=1000)
    site_url: str = Field(min_length=1, max_length=500)
    locale: Literal["nl", "en"] = "nl"


class KarMapKarRow(BaseModel):
    """One kar's pin/list entry on the Kar Map screen — KarManagement
    joined with its status/team lookups for the popup's "resume" content.
    """

    id: int
    kar_nummer: str
    status_name: str
    team_name: str | None
    latitude: float | None
    longitude: float | None


class KarMapAfleverlocatieRow(BaseModel):
    """One delivery location's pin/list entry on the Kar Map screen,
    joined with its zone and distribution point names.
    """

    id: int
    name: str
    description: str | None
    zone_name: str
    distributiepunt_name: str
    latitude: float | None
    longitude: float | None


class KarMapDistributiepuntRow(BaseModel):
    """One distribution point's pin/list entry on the Kar Map screen."""

    id: int
    name: str
    terrein_positie: str | None
    latitude: float | None
    longitude: float | None


class KarMapResponse(BaseModel):
    """The full Kar Map payload: one array per layer. Rows with no
    latitude/longitude are included too — the frontend excludes them from
    the map itself but still lists them in the side panel.
    """

    karren: list[KarMapKarRow]
    afleverlocaties: list[KarMapAfleverlocatieRow]
    distributiepunten: list[KarMapDistributiepuntRow]


class KarTrackerGroundplanResponse(BaseModel):
    """One ground-plan overlay: its name and south-west/north-east corner
    coordinates. The image itself is served separately by
    GET /groundplans/{id}/image; updated_at lets the frontend cache-bust
    that URL after the image is replaced.
    """

    model_config = {"from_attributes": True}

    id: int
    name: str
    sw_latitude: float
    sw_longitude: float
    ne_latitude: float
    ne_longitude: float
    updated_at: datetime


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


class KarStatusImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk kar-status import. A
    name that already exists is rejected as an error instead of being
    upserted — same rule as the Karren import.
    """

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class KarStatusImportResponse(BaseModel):
    """The full outcome of a bulk kar-status import — one result per row, in order."""

    results: list[KarStatusImportRowResult]


class DistributiepuntResponse(BaseModel):
    """One distribution point, as shown on the Distributiepunten screen."""

    id: int
    name: str
    latitude: float | None
    longitude: float | None
    terrein_positie: str | None
    altsien_kernlid_id: int | None


class DistributiepuntCreateRequest(BaseModel):
    """What's sent to create a brand-new distribution point.
    altsien_kernlid_id, if given, must reference an existing row (checked
    by the endpoint, not here).
    """

    name: str = Field(min_length=1, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    terrein_positie: str | None = Field(default=None, max_length=255)
    altsien_kernlid_id: int | None = None


class DistributiepuntUpdateRequest(DistributiepuntCreateRequest):
    """What's sent to update an existing distribution point — same shape as creating one."""


class DistributiepuntImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk distributiepunt import.
    A name that already exists is rejected as an error instead of being
    upserted — same rule as the Karren import.
    """

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class DistributiepuntImportResponse(BaseModel):
    """The full outcome of a bulk distributiepunt import — one result per row, in order."""

    results: list[DistributiepuntImportRowResult]


class ZoneResponse(BaseModel):
    """One delivery zone, as shown on the Zone screen."""

    id: int
    name: str


class ZoneCreateRequest(BaseModel):
    """What's sent to create a brand-new zone."""

    name: str = Field(min_length=1, max_length=255)


class ZoneUpdateRequest(BaseModel):
    """What's sent to rename an existing zone — same shape as creating one."""

    name: str = Field(min_length=1, max_length=255)


class ZoneImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk zone import. A name
    that already exists is rejected as an error instead of being upserted.
    """

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class ZoneImportResponse(BaseModel):
    """The full outcome of a bulk zone import — one result per row, in order."""

    results: list[ZoneImportRowResult]


class PlanKarOption(BaseModel):
    """One entry of a "Plan a kar" dropdown (a team or a delivery location)."""

    id: int
    name: str


class PlanKarAfleverlocatieOption(PlanKarOption):
    """A delivery-location dropdown entry: its name plus its description, shown next to it."""

    description: str | None


class PlanKarFestivalRow(BaseModel):
    """One matrix row: a festival plus its saved delivery location, if any."""

    festival_id: int
    festival_name: str
    afleverlocatie_id: int | None


class PlanKarResponse(BaseModel):
    """The matrix for one team in one season."""

    season_id: int
    team_id: int
    rows: list[PlanKarFestivalRow]


class PlanKarSaveRow(BaseModel):
    """One row to save; a null afleverlocatie_id clears that festival's assignment."""

    festival_id: int
    afleverlocatie_id: int | None = None


class PlanKarSaveRequest(BaseModel):
    """What the Save button sends: the whole matrix for one team in one season."""

    season_id: int
    team_id: int
    rows: list[PlanKarSaveRow]


class LeverdatumRow(BaseModel):
    """One "Delivery Dates" row: a festival plus its saved dates, if any."""

    festival_id: int
    festival_name: str
    delivery_date: date | None
    pickup_date: date | None


class LeverdatumResponse(BaseModel):
    """The "Delivery Dates" table for one season."""

    season_id: int
    rows: list[LeverdatumRow]


class LeverdatumSaveRow(BaseModel):
    """One row to save; both dates null clears that festival's record."""

    festival_id: int
    delivery_date: date | None = None
    pickup_date: date | None = None


class LeverdatumSaveRequest(BaseModel):
    """What the Save button sends: the whole table for one season."""

    season_id: int
    rows: list[LeverdatumSaveRow]


class AfleverlocatieResponse(BaseModel):
    """One delivery location, as shown on the Afleverlocatie screen."""

    id: int
    name: str
    description: str | None
    zone_id: int
    distributiepunt_id: int
    latitude: float | None
    longitude: float | None
    terrein_positie: str | None
    altsien_kernlid_id: int | None
    active: bool


class AfleverlocatieCreateRequest(BaseModel):
    """What's sent to create a brand-new delivery location. zone_id/
    distributiepunt_id must reference an existing row in their respective
    tables (checked by the endpoint, not here); altsien_kernlid_id, if
    given, must too.
    """

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    zone_id: int
    distributiepunt_id: int
    latitude: float | None = None
    longitude: float | None = None
    terrein_positie: str | None = Field(default=None, max_length=255)
    altsien_kernlid_id: int | None = None
    # Inactive locations are hidden from the "Plan a kar" dropdowns.
    active: bool = True


class AfleverlocatieUpdateRequest(AfleverlocatieCreateRequest):
    """What's sent to update an existing delivery location — same shape as creating one."""

    active: bool


class AfleverlocatieImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk afleverlocatie import.
    A name that already exists is rejected as an error instead of being
    upserted — same rule as the Karren import.
    """

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class AfleverlocatieImportResponse(BaseModel):
    """The full outcome of a bulk afleverlocatie import — one result per row, in order."""

    results: list[AfleverlocatieImportRowResult]
