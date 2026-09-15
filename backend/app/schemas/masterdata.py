# Schemas describing MasterData's screens, custom roles, permissions, and
# the Season screen (the first actual piece of master data it manages).

from datetime import date
from typing import Literal

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
    """Which MasterData screens the calling user is allowed to view, and on
    which of those they're also allowed to create — used by the frontend
    to decide what to show (sidebar links, and finer-grained controls like
    the Data Upload/Download screen's upload button) without it having to
    know the full permission-checking rules itself.
    """

    viewable_screen_keys: list[str]
    creatable_screen_keys: list[str]


class SeasonResponse(BaseModel):
    """One season, as shown on the Season screen."""

    id: int
    name: str
    periode_open: bool


class SeasonCreateRequest(BaseModel):
    """What's sent to create a brand-new season."""

    name: str = Field(min_length=1, max_length=255)
    periode_open: bool = False


class SeasonUpdateRequest(BaseModel):
    """What's sent to rename an existing season."""

    name: str = Field(min_length=1, max_length=255)
    periode_open: bool = False


class TeamLocationResponse(BaseModel):
    """One team location, as shown on the Team Location screen."""

    id: int
    location: str


class TeamLocationCreateRequest(BaseModel):
    """What's sent to create a brand-new team location."""

    location: str = Field(min_length=1, max_length=255)


class TeamLocationUpdateRequest(BaseModel):
    """What's sent to rename an existing team location."""

    location: str = Field(min_length=1, max_length=255)


class DeliveryMethodResponse(BaseModel):
    """One delivery method, as shown on the Delivery Method screen."""

    id: int
    delivery_method: str


class DeliveryMethodCreateRequest(BaseModel):
    """What's sent to create a brand-new delivery method."""

    delivery_method: str = Field(min_length=1, max_length=255)


class DeliveryMethodUpdateRequest(BaseModel):
    """What's sent to rename an existing delivery method."""

    delivery_method: str = Field(min_length=1, max_length=255)


class TeamTaskResponse(BaseModel):
    """One team task, as shown on the Team Tasks screen."""

    id: int
    team_tasks: str


class TeamTaskCreateRequest(BaseModel):
    """What's sent to create a brand-new team task."""

    team_tasks: str = Field(min_length=1, max_length=255)


class TeamTaskUpdateRequest(BaseModel):
    """What's sent to rename an existing team task."""

    team_tasks: str = Field(min_length=1, max_length=255)


class FestivalResponse(BaseModel):
    """One festival, as shown on the Festivals screen."""

    id: int
    name: str
    start_date: date
    end_date: date
    season_id: int


class FestivalCreateRequest(BaseModel):
    """What's sent to create a brand-new festival. season_id must reference
    an existing season (checked by the endpoint, not here)."""

    name: str = Field(min_length=1, max_length=255)
    start_date: date
    end_date: date
    season_id: int


class FestivalUpdateRequest(FestivalCreateRequest):
    """What's sent to update an existing festival — same shape as creating one."""


class ProductResponse(BaseModel):
    """One product, as shown on the Products screen."""

    id: int
    name: str
    type_id: int | None
    warehouse_id: int | None
    warehouse_location: str | None
    category_id: int | None
    is_consumable: bool
    is_blocked: bool
    is_logistics_product: bool
    limit_id: int | None
    description: str | None


class ProductCreateRequest(BaseModel):
    """What's sent to create a brand-new product. Only the name is
    required — every other field is optional. type_id/warehouse_id/
    category_id/limit_id, if given, must reference an existing row in the
    matching lookup table (checked by the endpoint, not here).
    """

    name: str = Field(min_length=1, max_length=255)
    type_id: int | None = None
    warehouse_id: int | None = None
    warehouse_location: str | None = Field(default=None, max_length=255)
    category_id: int | None = None
    is_consumable: bool = False
    is_blocked: bool = False
    is_logistics_product: bool = False
    limit_id: int | None = None
    description: str | None = None


class ProductUpdateRequest(ProductCreateRequest):
    """What's sent to update an existing product — same shape as creating one."""


class ProductTypeResponse(BaseModel):
    """One product type, as shown on the Type screen."""

    id: int
    name: str


class ProductTypeCreateRequest(BaseModel):
    """What's sent to create a brand-new product type."""

    name: str = Field(min_length=1, max_length=255)


class ProductTypeUpdateRequest(BaseModel):
    """What's sent to rename an existing product type."""

    name: str = Field(min_length=1, max_length=255)


class ProductCategoryResponse(BaseModel):
    """One product category, as shown on the Categorie screen."""

    id: int
    name: str


class ProductCategoryCreateRequest(BaseModel):
    """What's sent to create a brand-new product category."""

    name: str = Field(min_length=1, max_length=255)


class ProductCategoryUpdateRequest(BaseModel):
    """What's sent to rename an existing product category."""

    name: str = Field(min_length=1, max_length=255)


class WarehouseResponse(BaseModel):
    """One warehouse (Magazijn), as shown on the Magazijn screen."""

    id: int
    name: str


class WarehouseCreateRequest(BaseModel):
    """What's sent to create a brand-new warehouse."""

    name: str = Field(min_length=1, max_length=255)


class WarehouseUpdateRequest(BaseModel):
    """What's sent to rename an existing warehouse."""

    name: str = Field(min_length=1, max_length=255)


class ProductLimitResponse(BaseModel):
    """One limit option (Limiet), as shown on the Limiet screen."""

    id: int
    name: str


class ProductLimitCreateRequest(BaseModel):
    """What's sent to create a brand-new limit option."""

    name: str = Field(min_length=1, max_length=255)


class ProductLimitUpdateRequest(BaseModel):
    """What's sent to rename an existing limit option."""

    name: str = Field(min_length=1, max_length=255)


class MasterDataTypeBreakdownItem(BaseModel):
    """How many products have one product type — one entry per existing
    type (zero-filled), plus one "Unassigned" entry (type_name=None) for
    products with no type set, for the dashboard's "Products by Type" chart.
    """

    type_name: str | None
    count: int


class MasterDataCategoryBreakdownItem(BaseModel):
    """Same as MasterDataTypeBreakdownItem, but for product categories."""

    category_name: str | None
    count: int


class MasterDataWarehouseBreakdownItem(BaseModel):
    """Same as MasterDataTypeBreakdownItem, but for warehouses."""

    warehouse_name: str | None
    count: int


class MasterDataDashboardResponse(BaseModel):
    """Aggregate KPI stats for MasterData's landing dashboard ("Masterdata Overview")."""

    total_products: int
    total_seasons: int
    blocked_products: int
    consumable_products: int
    logistics_products: int
    products_missing_classification: int
    products_by_type: list[MasterDataTypeBreakdownItem]
    products_by_category: list[MasterDataCategoryBreakdownItem]
    products_by_warehouse: list[MasterDataWarehouseBreakdownItem]


class AltsienKernlidResponse(BaseModel):
    """One Altsien Kernleden contact, as shown on its screen."""

    id: int
    first_name: str
    name: str
    telephone_number: str
    email: EmailStr


class AltsienKernlidCreateRequest(BaseModel):
    """What's sent to create a brand-new Altsien Kernleden contact."""

    first_name: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    telephone_number: str = Field(min_length=1, max_length=255)
    email: EmailStr


class AltsienKernlidUpdateRequest(AltsienKernlidCreateRequest):
    """What's sent to update an existing Altsien Kernleden contact — same shape as creating one."""


class TeamResponse(BaseModel):
    """One team, as shown on the Teams screen. task_ids/kernlid_ids are
    derived from the MasterData_team_team_task / MasterData_team_kernlid
    join tables by the endpoint — they aren't columns on Team itself.
    """

    id: int
    name: str
    location_id: int | None
    delivery_method_id: int | None
    task_ids: list[int]
    kernlid_ids: list[int]
    description: str | None


class TeamCreateRequest(BaseModel):
    """What's sent to create a brand-new team. location_id/delivery_method_id,
    if given, must reference an existing row in their lookup table; every id
    in task_ids/kernlid_ids must reference an existing TeamTask/AltsienKernlid
    row — all checked by the endpoint, not here.
    """

    name: str = Field(min_length=1, max_length=255)
    location_id: int | None = None
    delivery_method_id: int | None = None
    task_ids: list[int] = Field(default_factory=list)
    kernlid_ids: list[int] = Field(default_factory=list)
    description: str | None = None


class TeamUpdateRequest(TeamCreateRequest):
    """What's sent to update an existing team — same shape as creating one."""


# --- Data Upload/Download: bulk XLSX import/export, one row-result pair
# per master-data table, mirroring KarTracker's KarImportRowResult/
# KarStatusImportRowResult (app/schemas/kartracker.py). None of these have
# an "updated" outcome — a row naming something that already exists is
# rejected as an error instead of being upserted, same rule as KarTracker.


class SeasonImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk season import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class SeasonImportResponse(BaseModel):
    """The full outcome of a bulk season import — one result per row, in order."""

    results: list[SeasonImportRowResult]


class ProductTypeImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk product-type import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class ProductTypeImportResponse(BaseModel):
    """The full outcome of a bulk product-type import — one result per row, in order."""

    results: list[ProductTypeImportRowResult]


class WarehouseImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk warehouse import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class WarehouseImportResponse(BaseModel):
    """The full outcome of a bulk warehouse import — one result per row, in order."""

    results: list[WarehouseImportRowResult]


class ProductCategoryImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk product-category import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class ProductCategoryImportResponse(BaseModel):
    """The full outcome of a bulk product-category import — one result per row, in order."""

    results: list[ProductCategoryImportRowResult]


class ProductLimitImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk product-limit import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class ProductLimitImportResponse(BaseModel):
    """The full outcome of a bulk product-limit import — one result per row, in order."""

    results: list[ProductLimitImportRowResult]


class TeamLocationImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk team-location import."""

    row_number: int
    location: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class TeamLocationImportResponse(BaseModel):
    """The full outcome of a bulk team-location import — one result per row, in order."""

    results: list[TeamLocationImportRowResult]


class DeliveryMethodImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk delivery-method import."""

    row_number: int
    delivery_method: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class DeliveryMethodImportResponse(BaseModel):
    """The full outcome of a bulk delivery-method import — one result per row, in order."""

    results: list[DeliveryMethodImportRowResult]


class TeamTaskImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk team-task import."""

    row_number: int
    team_tasks: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class TeamTaskImportResponse(BaseModel):
    """The full outcome of a bulk team-task import — one result per row, in order."""

    results: list[TeamTaskImportRowResult]


class FestivalImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk festival import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class FestivalImportResponse(BaseModel):
    """The full outcome of a bulk festival import — one result per row, in order."""

    results: list[FestivalImportRowResult]


class ProductImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk product import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class ProductImportResponse(BaseModel):
    """The full outcome of a bulk product import — one result per row, in order."""

    results: list[ProductImportRowResult]


class TeamImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk team import. Only
    Team's scalar fields (name/location/delivery method/description) are
    imported — task/kernlid links are not part of this bulk tool.
    """

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class TeamImportResponse(BaseModel):
    """The full outcome of a bulk team import — one result per row, in order."""

    results: list[TeamImportRowResult]


class AltsienKernlidImportRowResult(BaseModel):
    """What happened to one row of an uploaded bulk Altsien Kernleden import."""

    row_number: int
    name: str | None
    outcome: Literal["created", "error"]
    detail: str | None


class AltsienKernlidImportResponse(BaseModel):
    """The full outcome of a bulk Altsien Kernleden import — one result per row, in order."""

    results: list[AltsienKernlidImportRowResult]
