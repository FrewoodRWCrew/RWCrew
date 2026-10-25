# Schemas for Atelier (module-5). The access-rights screens' custom-roles
# shapes (screens, roles, permissions, users) are identical to module 3's, so
# they are re-used from app/schemas/intervention_requests.py — the same as
# StockMaster does. Below them: the masterdata shapes (block 1); the
# reservation, stock and hand-out/return shapes follow in the next blocks.

from datetime import date, datetime
from decimal import Decimal
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
from app.schemas.masterdata import ImportOutcome

# --- Masterdata (block 1): sizes and articles ---------------------------------

# Who a size is cut for (the same codes as FITS in app/db/models/atelier_size.py).
Fit = Literal["women", "men", "unisex"]


class SizeResponse(BaseModel):
    """One size, as shown on the Maten screen and in the article's checklist."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    fit: Fit
    sort_order: int
    active: bool


class SizeRequest(BaseModel):
    """What's sent to create or change a size."""

    name: str = Field(min_length=1, max_length=50)
    fit: Fit
    sort_order: int = Field(default=0, ge=0)
    active: bool = True


class ArticleSizeResponse(BaseModel):
    """One size an article comes in."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    size_id: int
    min_stock: int | None
    # The share (%) of the article's pieces to prepare in this size.
    size_share_pct: float | None
    active: bool


class ArticleSizeInput(BaseModel):
    """One ticked size in the article's form."""

    size_id: int
    min_stock: int | None = Field(default=None, ge=0)
    size_share_pct: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    active: bool = True


class ArticleResponse(BaseModel):
    """One article with its sizes, as shown on the Artikelen screen."""

    id: int
    code: str
    name: str
    description: str | None
    colour: str | None
    cost: float | None
    is_tag_managed: bool
    active: bool
    # The optional picture: whether there is one, and when it last changed.
    has_image: bool
    image_updated_at: datetime | None
    sizes: list[ArticleSizeResponse]


class ArticleRequest(BaseModel):
    """What's sent to create or change an article. `sizes` is the article's
    whole size list: sizes left out are removed from the article."""

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    colour: str | None = Field(default=None, max_length=100)
    cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    is_tag_managed: bool = False
    active: bool = True
    sizes: list[ArticleSizeInput] = []


class SeasonSummaryResponse(BaseModel):
    """A season for the module's own season dropdown."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    periode_open: bool


class MasterdataStatsResponse(BaseModel):
    """The KPI page's "Masterdata" section for one season."""

    articles_active: int
    articles_inactive: int
    sizes_active: int
    article_sizes_active: int


class AtelierImportRowResult(BaseModel):
    """The outcome of one uploaded row (every Atelier XLSX import)."""

    row_number: int
    # What the row is about (a size, article code, ...), for the result table.
    name: str | None
    outcome: ImportOutcome
    detail: str | None = None


class AtelierImportResponse(BaseModel):
    """One result per uploaded row."""

    results: list[AtelierImportRowResult]


# --- Reservations and preparation (block 2) ---------------------------------


class FestivalSummaryResponse(BaseModel):
    """A festival of the season, with its days (start → end)."""

    id: int
    name: str
    start_date: date
    end_date: date
    days: list[date]


class PackageLine(BaseModel):
    """One package line: each person gets N of this article."""

    model_config = ConfigDict(from_attributes=True)

    article_id: int
    quantity_per_person: int = Field(ge=1, le=99)


class ReservationRowResponse(BaseModel):
    """One team on a festival's Reservaties table: persons + package."""

    team_id: int
    team_name: str
    team_active: bool
    persons: int
    # The package per person, in article-name order.
    lines: list[PackageLine]
    note: str | None
    updated_by_name: str | None
    updated_at: datetime | None


class ReservationInput(BaseModel):
    """One team's reservation as edited on screen; `lines` left out (null)
    keeps the package as it is."""

    team_id: int
    persons: int = Field(ge=0, le=9999)
    note: str | None = Field(default=None, max_length=2000)
    lines: list[PackageLine] | None = None


class SaveReservationsRequest(BaseModel):
    """The festival's reservations as edited on screen (only the sent teams change)."""

    reservations: list[ReservationInput]


class PreviousReservationsResponse(BaseModel):
    """Last year's matching festival (null when there is none) and its
    reservations, for the "copy from last year" panel."""

    festival: FestivalSummaryResponse | None
    rows: list[ReservationRowResponse]


class CopyReservationsRequest(BaseModel):
    """The teams whose reservation of last year's festival is copied."""

    team_ids: list[int] = Field(min_length=1)


class CopyReservationsResponse(BaseModel):
    """What the copy did."""

    teams_changed: int
    # Package lines skipped because their article is no longer active.
    skipped_inactive: int


class SizeEstimateResponse(BaseModel):
    """How many pieces of one size to prepare (estimate), next to the stock."""

    size_id: int
    article_size_id: int
    size_name: str
    fit: Fit
    quantity: int
    # The store's pieces of this size: available now, and everything it owns
    # (available + to wash + handed out).
    available: int
    owned: int


class ArticleNeedResponse(BaseModel):
    """The pieces of one article needed per festival day, with a size estimate."""

    article_id: int
    article_code: str
    article_name: str
    quantity: int
    sizes: list[SizeEstimateResponse]
    # True when the article's size split (%) isn't complete, so an equal split was used.
    equal_split: bool


class BundleLineResponse(BaseModel):
    """One article in a team's bundle."""

    article_id: int
    article_name: str
    quantity: int


class TeamBundleResponse(BaseModel):
    """What one team gets each festival day: persons x its package."""

    team_id: int
    team_name: str
    persons: int
    lines: list[BundleLineResponse]


class PreparationResponse(BaseModel):
    """The Voorbereiden screen for one festival: the same need on every day."""

    festival: FestivalSummaryResponse
    persons_per_day: int
    pieces_per_day: int
    articles: list[ArticleNeedResponse]
    bundles: list[TeamBundleResponse]
    # Teams with persons but no package (nothing to prepare for them).
    teams_without_package: list[str]


class FestivalReservationStatsResponse(BaseModel):
    """The KPI page's line for one festival."""

    festival: FestivalSummaryResponse
    persons_per_day: int
    pieces_per_day: int
    # Teams with at least one person.
    teams_reserved: int
    # Teams with persons but no package yet.
    teams_without_package: int
    # Active teams reserved (persons > 0) at another festival of the season
    # but with nothing here (no persons, no note): probably forgotten.
    teams_missing: list[str]


# --- Stock (block 3) -------------------------------------------------------------

StockStatus = Literal["available", "to_wash", "handed_out"]
WriteOffReason = Literal["damaged", "lost", "not_returned", "other"]


class StockSizeRow(BaseModel):
    """One article size on the stock overview: its pieces per status."""

    article_size_id: int
    size_id: int
    size_name: str
    fit: Fit
    active: bool
    min_stock: int | None
    available: int
    to_wash: int
    handed_out: int


class StockArticleRow(BaseModel):
    """One article on the stock overview, with all its sizes."""

    article_id: int
    code: str
    name: str
    active: bool
    has_image: bool
    image_updated_at: datetime | None
    sizes: list[StockSizeRow]


class StockLineInput(BaseModel):
    """One booking line; `from_status` only on a write-off."""

    article_size_id: int
    quantity: int = Field(ge=1, le=100000)
    from_status: Literal["available", "to_wash"] | None = None


class ReceiptRequest(BaseModel):
    """Ontvangst: the received lines, where they came from and a note."""

    lines: list[StockLineInput] = Field(min_length=1)
    reference: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class WashRequest(BaseModel):
    """Gewassen: the washed lines (to wash → available)."""

    lines: list[StockLineInput] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=2000)


class WriteOffRequest(BaseModel):
    """Afboeken: the lines (each from available or to wash), why, and a note."""

    lines: list[StockLineInput] = Field(min_length=1)
    reason: WriteOffReason
    note: str | None = Field(default=None, max_length=2000)


class CountLineInput(BaseModel):
    """A counted quantity of an article size in one status."""

    article_size_id: int
    status: Literal["available", "to_wash"]
    counted: int = Field(ge=0, le=100000)


class CountRequest(BaseModel):
    """Telling: the counted quantities; only differences are booked."""

    lines: list[CountLineInput] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=2000)


class ReverseRequest(BaseModel):
    """Ongedaan maken: an optional note on the reversal."""

    note: str | None = Field(default=None, max_length=2000)


class StockMovementResponse(BaseModel):
    """One line of a booking."""

    article_size_id: int
    article_id: int
    article_name: str
    size_name: str
    fit: Fit
    from_status: StockStatus | None
    to_status: StockStatus | None
    quantity: int


class StockDocumentResponse(BaseModel):
    """A booking with its lines (the history list leaves the lines empty)."""

    id: int
    doc_number: str
    doc_type: str
    reference: str | None
    reason: str | None
    note: str | None
    status: str
    reversal_of_number: str | None
    reversed_by_number: str | None
    created_by_name: str | None
    created_at: datetime
    total_quantity: int
    movements: list[StockMovementResponse]


class OrderNeedLine(BaseModel):
    """One article size to order: the highest day need of the season minus
    what the atelier owns."""

    article_id: int
    article_code: str
    article_name: str
    article_size_id: int
    size_name: str
    fit: Fit
    needed: int
    # The festival with that highest day need.
    festival_name: str
    owned: int
    to_order: int


class MinStockLine(BaseModel):
    """An article size whose available stock is below its minimum."""

    article_size_id: int
    article_id: int
    article_name: str
    size_name: str
    fit: Fit
    min_stock: int
    available: int


class StockTotalsResponse(BaseModel):
    """The KPI page's stock tiles."""

    available: int
    to_wash: int
    handed_out: int
    # Article sizes whose available stock is below their minimum.
    below_min_stock: int


# --- Counter desk (block 4) -------------------------------------------------------


class DeskOpenLine(BaseModel):
    """One piece a person still has (not yet returned)."""

    line_id: int
    handout_id: int
    article_id: int
    article_name: str
    size_name: str
    fit: Fit
    festival_name: str
    team_name: str
    day: date
    handed_out_at: datetime


class DeskPersonResponse(BaseModel):
    """A known worker (search result at the desk) with the pieces still out."""

    id: int
    first_name: str
    last_name: str
    # "First Last".
    name: str
    email: str | None
    # The wristband number at the asked festival (else the latest one known).
    bracelet_number: str | None
    last_team_id: int | None
    open_lines: list[DeskOpenLine]


class DeskTeamOption(BaseModel):
    """A team with a reservation at the festival (the desk's team dropdown)."""

    team_id: int
    team_name: str
    persons: int


class DeskSizeOption(BaseModel):
    """One size of a package article at the desk, with its available pieces."""

    article_size_id: int
    size_name: str
    fit: Fit
    available: int


class DeskPackageArticle(BaseModel):
    """One article of the team's package: 1 piece, size picked at the desk."""

    article_id: int
    code: str
    name: str
    has_image: bool
    image_updated_at: datetime | None
    sizes: list[DeskSizeOption]


class DeskContextResponse(BaseModel):
    """What the desk needs for a team at a festival on a day."""

    team_id: int
    team_name: str
    # The reservation's number of persons, and the people who already picked up today.
    persons_reserved: int
    served_today: int
    articles: list[DeskPackageArticle]


class HandoutLineInput(BaseModel):
    """One piece to hand out: the article and the size picked."""

    article_id: int
    article_size_id: int


class HandoutRequest(BaseModel):
    """Ophalen: who (first + family name = the person's key, email, optional
    bracelet number), for which team/festival/day, and the pieces."""

    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    bracelet_number: str | None = Field(default=None, max_length=100)
    # The wristband scan this pick-up came from (marked used).
    scan_id: int | None = None
    festival_id: int
    team_id: int
    day: date
    lines: list[HandoutLineInput] = Field(min_length=1)


class ReturnRequest(BaseModel):
    """Terugbrengen: the pieces (hand-out lines) that came back."""

    line_ids: list[int] = Field(min_length=1)
    # The wristband scan this return came from (marked used).
    scan_id: int | None = None


class HandoutLineResponse(BaseModel):
    """One piece of a pick-up."""

    id: int
    article_id: int
    article_name: str
    size_name: str
    fit: Fit
    returned_at: datetime | None


class HandoutResponse(BaseModel):
    """One pick-up with its pieces."""

    id: int
    person_id: int
    person_name: str
    email: str | None
    # The person's wristband number at this pick-up's festival.
    bracelet_number: str | None
    festival_name: str
    team_name: str
    day: date
    status: Literal["open", "returned", "cancelled"]
    created_at: datetime
    created_by_name: str | None
    lines: list[HandoutLineResponse]


class DeskStatsResponse(BaseModel):
    """The KPI page's desk tiles."""

    # Pieces handed out today (Belgian date), and pieces still out over all days.
    handed_out_today: int
    still_out: int
    # People with at least one piece still out.
    persons_with_open: int



# --- Wristband scans (block 5) ----------------------------------------------------


class ScanResponse(BaseModel):
    """One received scan message (the desk card and the settings log)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    received_at: datetime
    source: Literal["webhook", "test"]
    status: Literal["new", "used", "dismissed", "ignored", "refused"]
    status_detail: str | None
    event: str | None
    device_id: str | None
    device_name: str | None
    wristband_number: str | None
    first_name: str | None
    last_name: str | None
    team_name: str | None
    team_id: int | None
    profile_name: str | None
    email: str | None
    size: str | None
    person_id: int | None


class ScanLogEntry(ScanResponse):
    """A scan in the settings log, with the message as received."""

    raw: str | None


class TeamSummaryResponse(BaseModel):
    """A MasterData team (the Test-scan form's team dropdown)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    active: bool


class ScannerResponse(BaseModel):
    """A scanner of the wristband company (auto-registered by its first scan)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    device_name: str | None
    label: str | None
    last_seen_at: datetime | None


class ScannerLabelRequest(BaseModel):
    """Our own name for a scanner, e.g. "Balie 1" (empty = none)."""

    label: str | None = Field(default=None, max_length=255)


class AtelierSettingsResponse(BaseModel):
    """Atelier's settings, plus the webhook address and whether a token is configured."""

    wristband_required: bool
    webhook_path: str
    webhook_token_configured: bool


class AtelierSettingsRequest(BaseModel):
    """Change Atelier's settings."""

    wristband_required: bool


class TestScanRequest(BaseModel):
    """The Test-scan screen: a message exactly as the wristband company would send it."""

    raw: str = Field(min_length=1, max_length=100_000)


class TestScanResponse(BaseModel):
    """What the processing did with a test message."""

    scan: ScanResponse
    http_status: int
    team_name_matched: str | None
