# Schemas for StockMaster (module-4): stock overview, kars, bookings, kar
# needs, "Te bestellen", the count sheet, reasons and the KPI page. The
# custom-roles shapes (screens, roles, permissions, users) are identical to
# module 3's, so they are re-used from app/schemas/intervention_requests.py
# — the same as Altsien Select does.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.intervention_requests import (  # noqa: F401  (re-exported for the router)
    CreateOrGrantUserRequest,
    InterventionRequestsUserSummaryResponse as UserSummaryResponse,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
)

# The bookings a screen can make (a reversal goes through its own endpoint).
BookingAction = Literal["book_in", "kar_load", "book_out", "kar_dispatch", "kar_return", "kar_unload", "count"]


# --- Lookups ---------------------------------------------------------------


class NamedItem(BaseModel):
    """A plain {id, name} pair for dropdowns."""

    id: int
    name: str


class ReasonResponse(BaseModel):
    """One reason that can be chosen on a booking."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    applies_to: str | None
    active: bool
    sort_order: int


class ReasonWriteRequest(BaseModel):
    """What the Redenen screen sends to add or change a reason."""

    name: str = Field(min_length=1, max_length=100)
    applies_to: Literal["book_in", "kar_load", "book_out", "kar_dispatch", "kar_return", "kar_unload", "count"] | None = None
    active: bool = True
    sort_order: int = 0


class LookupsResponse(BaseModel):
    """Everything the StockMaster screens' dropdowns and filters need."""

    warehouses: list[NamedItem]
    categories: list[NamedItem]
    teams: list[NamedItem]
    reasons: list[ReasonResponse]
    # Everyone who ever made a booking (for the Boekingen user filter).
    booking_users: list[NamedItem]


# --- Stock overview --------------------------------------------------------


class KarQuantity(BaseModel):
    """How many pieces of a product lie in one kar."""

    kar_id: int
    kar_nummer: str
    quantity: int


class ProductStockResponse(BaseModel):
    """One product line on the stock overview (and in the booking panel's
    product search): free, in kars and total, with its bin.
    """

    product_id: int
    name: str
    type_name: str | None
    category_id: int | None
    category_name: str | None
    warehouse_id: int | None
    warehouse_name: str | None
    warehouse_location: str | None
    bin_label: str | None
    is_consumable: bool
    is_blocked: bool
    stock_return_to: str
    min_stock: int | None
    free: int
    in_kars: int
    total: int
    kars: list[KarQuantity]
    # Consumable with a minimum, and its total stock below that minimum.
    below_minimum: bool


class AlertsResponse(BaseModel):
    """What the orange banner at the top of StockMaster shows."""

    below_minimum_count: int


# --- Kars ------------------------------------------------------------------


class TripResponse(BaseModel):
    """A kar's current trip while it's out of the warehouse."""

    trip_id: int
    team_id: int | None
    team_name: str | None
    festival_id: int | None
    festival_name: str | None
    dispatched_at: datetime
    dispatch_document_id: int
    dispatch_doc_number: str


class KarSummaryResponse(BaseModel):
    """One kar card on the Karren screen."""

    kar_id: int
    kar_nummer: str
    team_id: int | None
    team_name: str | None
    kartracker_status: str | None
    is_out: bool
    trip: TripResponse | None
    # What's in it now.
    product_count: int
    total_quantity: int
    # Loading progress against this season's needs ("18 / 20").
    required_total: int
    loaded_toward_required: int


class KarLineResponse(BaseModel):
    """One product on the kar detail: in the kar versus needed."""

    product_id: int
    name: str
    bin_label: str | None
    in_kar: int
    required: int
    missing: int
    surplus: int
    free_available: int
    is_consumable: bool
    is_blocked: bool
    stock_return_to: str


class DispatchedLineResponse(BaseModel):
    """What left with the kar on its current trip (pre-fills "Kar terug")."""

    product_id: int
    name: str
    quantity: int
    is_consumable: bool
    stock_return_to: str


class KarDetailResponse(BaseModel):
    """Everything the kar detail and the kar booking panels need."""

    kar: KarSummaryResponse
    lines: list[KarLineResponse]
    dispatched: list[DispatchedLineResponse]
    # The festivals the kar's team works this season (for "Kar vertrekt").
    festivals: list[NamedItem]


# --- Bookings --------------------------------------------------------------


class BookingLineRequest(BaseModel):
    """One product line of a booking. On "Telling" the quantity is the
    counted quantity (0 allowed); on "Kar terug" 0 means "not returned".
    """

    product_id: int
    quantity: int = Field(ge=0)
    destination: Literal["kar", "free"] | None = None


class BookingRequest(BaseModel):
    """What a booking screen sends. Which fields matter depends on the
    action (see the router).
    """

    action: BookingAction
    season_id: int
    kar_id: int | None = None
    from_kar_id: int | None = None
    team_id: int | None = None
    festival_id: int | None = None
    reference: str | None = Field(default=None, max_length=255)
    reason_id: int | None = None
    comment: str | None = None
    lines: list[BookingLineRequest] = []


class ReverseRequest(BaseModel):
    """Optional comment when undoing a booking."""

    comment: str | None = None


class MovementResponse(BaseModel):
    """One ledger line of a booking."""

    product_id: int
    product_name: str
    quantity: int
    from_bucket: str
    from_kar_nummer: str | None
    to_bucket: str
    to_kar_nummer: str | None
    bin_snapshot: str | None


class DocumentResponse(BaseModel):
    """One booking (with its lines on the detail page)."""

    id: int
    doc_number: str
    doc_type: str
    status: str
    season_id: int
    season_name: str | None
    kar_id: int | None
    kar_nummer: str | None
    from_kar_nummer: str | None
    team_name: str | None
    festival_name: str | None
    reference: str | None
    reason_name: str | None
    comment: str | None
    source: str
    reversal_of_id: int | None
    reversal_of_number: str | None
    reversed_by_id: int | None
    reversed_by_number: str | None
    created_by_name: str | None
    created_at: datetime
    line_count: int
    total_quantity: int
    lines: list[MovementResponse]


class DocumentPageResponse(BaseModel):
    """One page of the booking history, plus the total number of rows."""

    items: list[DocumentResponse]
    total: int


# --- Kar needs (Benodigdheden) ---------------------------------------------


class RequirementResponse(BaseModel):
    """One product a kar needs this season."""

    product_id: int
    product_name: str
    bin_label: str | None
    quantity: int
    comment: str | None
    in_kar: int
    updated_by_name: str | None
    updated_at: datetime


class RequirementLineRequest(BaseModel):
    """One line as sent by the Benodigdheden screen."""

    product_id: int
    quantity: int = Field(ge=1)
    comment: str | None = None


class RequirementsSaveRequest(BaseModel):
    """The kar's complete list for the season (replaces what was stored)."""

    season_id: int
    kar_id: int
    lines: list[RequirementLineRequest]


class PreviousRequirementLine(BaseModel):
    """One of last season's needs, with what's already listed now."""

    product_id: int
    product_name: str
    quantity: int
    current_quantity: int | None


class PreviousRequirementsResponse(BaseModel):
    """Last season's needs of the same kar ("Kopieer van vorig seizoen")."""

    season_name: str | None
    lines: list[PreviousRequirementLine]


# --- Te bestellen and Telling ----------------------------------------------


class OrderNeedResponse(BaseModel):
    """One product on "Te bestellen": needs versus stock."""

    product_id: int
    name: str
    category_name: str | None
    warehouse_id: int | None
    warehouse_name: str | None
    bin_label: str | None
    needed: int
    free: int
    in_kars: int
    in_stock: int
    to_order: int
    is_blocked: bool


class CountSheetLine(BaseModel):
    """One product on the count sheet, with the quantity expected there."""

    product_id: int
    name: str
    bin_label: str | None
    warehouse_location: str | None
    expected: int


# --- KPI -------------------------------------------------------------------


class MonthActionCount(BaseModel):
    """How many bookings of one type were made in one month."""

    month: str
    doc_type: str
    count: int


class NamedQuantity(BaseModel):
    """A name with a number of pieces (charts)."""

    name: str
    quantity: int


class DashboardResponse(BaseModel):
    """The figures on StockMaster's KPI main page for one season."""

    total_stock: int
    free_stock: int
    in_kars: int
    kars_in_warehouse: int
    kars_out: int
    kars_with_needs: int
    kars_complete: int
    below_minimum: int
    order_lines: int
    bookings_per_month: list[MonthActionCount]
    consumption_per_team: list[NamedQuantity]
    top_consumed_products: list[NamedQuantity]
