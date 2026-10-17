# Read-only views of StockMaster's data, as shown on its screens: the stock
# overview, the kar cards and kar detail, the booking history, "Te
# bestellen", the count sheet and the KPI main page. Nothing here changes
# stock — that only happens in stock_service.py.
#
# The volumes are small (~250 products, ~10,000 bookings a year), so most
# views simply load the few rows they need and combine them in Python,
# which keeps the code plain and the same on Postgres and SQLite (tests).

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.timezone import BELGIAN_TZ, to_belgian
from app.db.models.festival import Festival
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_limit import ProductLimit
from app.db.models.product_type import ProductType
from app.db.models.season import Season
from app.db.models.stockmaster_balance import StockMasterBalance
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.stockmaster_kar_trip import StockMasterKarTrip
from app.db.models.stockmaster_movement import StockMasterMovement
from app.db.models.stockmaster_reason import StockMasterReason
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival
from app.db.models.warehouse import Warehouse
from app.modules.module_4.requirement_service import (
    list_requirements,
    needs_per_product,
    previous_season_requirements,
    requirements_by_kar,
)
from app.modules.module_4.delivery_entitlement import delivery_entitlement
from app.modules.module_4.manual_request_service import list_manual_requests, manual_requests_by_kar
from app.modules.module_4.stock_service import BOOK_OUT, REVERSED, dispatched_lines, open_trip_of
from app.schemas.stockmaster import (
    CountSheetLine,
    DashboardResponse,
    DispatchedLineResponse,
    DocumentResponse,
    EntitlementTrace,
    KarDetailResponse,
    KarLineResponse,
    KarQuantity,
    KarSummaryResponse,
    ManualRequestResponse,
    MonthActionCount,
    MovementResponse,
    NamedItem,
    NamedQuantity,
    OrderNeedResponse,
    PreviousRequirementLine,
    PreviousRequirementsResponse,
    ProductStockResponse,
    RequirementResponse,
    TripResponse,
)


# --- Shared building blocks ------------------------------------------------


@dataclass
class StockSnapshot:
    """All current stock at once: free stock per product, and per product
    the pieces in each kar.
    """

    free: dict[int, int]
    in_kars: dict[int, dict[int, int]]

    def kar_total(self, product_id: int) -> int:
        """Pieces of one product over all kars."""
        return sum(self.in_kars.get(product_id, {}).values())

    def total(self, product_id: int) -> int:
        """Pieces of one product in the warehouse (free + all kars)."""
        return self.free.get(product_id, 0) + self.kar_total(product_id)

    def kar_contents(self, kar_id: int) -> dict[int, int]:
        """{product_id: quantity} in one kar."""
        return {
            product_id: per_kar[kar_id] for product_id, per_kar in self.in_kars.items() if kar_id in per_kar
        }


def load_stock(db: Session) -> StockSnapshot:
    """Read every balance row once."""
    free: dict[int, int] = {}
    in_kars: dict[int, dict[int, int]] = defaultdict(dict)
    for product_id, kar_id, quantity in db.execute(
        select(StockMasterBalance.product_id, StockMasterBalance.kar_id, StockMasterBalance.quantity)
    ).all():
        if kar_id is None:
            free[product_id] = quantity
        else:
            in_kars[product_id][kar_id] = quantity
    return StockSnapshot(free, dict(in_kars))


def _names(db: Session, model, column) -> dict[int, str]:
    """{id: name} of a small lookup table."""
    return {row_id: name for row_id, name in db.execute(select(model.id, column)).all()}


def _bin_label(warehouse_name: str | None, location: str | None) -> str | None:
    """Warehouse + bin as one readable text ("Hal A · B-12")."""
    return " · ".join(part for part in (warehouse_name, location) if part) or None


def _is_below_minimum(product: Product, total: int) -> bool:
    """Only consumables with a minimum are watched."""
    return product.is_consumable and product.min_stock is not None and total < product.min_stock


# --- Stock overview --------------------------------------------------------


def build_product_stock(db: Session) -> list[ProductStockResponse]:
    """Every product with its free stock, its stock per kar and its total."""
    stock = load_stock(db)
    warehouses = _names(db, Warehouse, Warehouse.name)
    categories = _names(db, ProductCategory, ProductCategory.name)
    types = _names(db, ProductType, ProductType.name)
    kar_numbers = _names(db, KarTrackerKar, KarTrackerKar.kar_nummer)

    result = []
    for product in db.scalars(select(Product).order_by(Product.name)).all():
        warehouse_name = warehouses.get(product.warehouse_id) if product.warehouse_id else None
        kars = sorted(
            (
                KarQuantity(kar_id=kar_id, kar_nummer=kar_numbers.get(kar_id, str(kar_id)), quantity=quantity)
                for kar_id, quantity in stock.in_kars.get(product.id, {}).items()
            ),
            key=lambda item: item.kar_nummer,
        )
        total = stock.total(product.id)
        result.append(
            ProductStockResponse(
                product_id=product.id,
                name=product.name,
                type_name=types.get(product.type_id) if product.type_id else None,
                category_id=product.category_id,
                category_name=categories.get(product.category_id) if product.category_id else None,
                warehouse_id=product.warehouse_id,
                warehouse_name=warehouse_name,
                warehouse_location=product.warehouse_location,
                bin_label=_bin_label(warehouse_name, product.warehouse_location),
                is_consumable=product.is_consumable,
                is_blocked=product.is_blocked,
                stock_return_to=product.stock_return_to,
                min_stock=product.min_stock,
                free=stock.free.get(product.id, 0),
                in_kars=stock.kar_total(product.id),
                total=total,
                kars=kars,
                below_minimum=_is_below_minimum(product, total),
                has_image=product.has_image,
                image_updated_at=product.image_updated_at,
            )
        )
    return result


def count_below_minimum(db: Session) -> int:
    """How many consumables are below their minimum stock (the banner)."""
    stock = load_stock(db)
    watched = db.scalars(
        select(Product).where(Product.is_consumable.is_(True), Product.min_stock.is_not(None))
    ).all()
    return sum(1 for product in watched if _is_below_minimum(product, stock.total(product.id)))


# --- Kars ------------------------------------------------------------------


def _trip_response(db: Session, trip: StockMasterKarTrip) -> TripResponse:
    """A kar's open trip with readable names."""
    team = db.get(Team, trip.team_id) if trip.team_id else None
    festival = db.get(Festival, trip.festival_id) if trip.festival_id else None
    document = db.get(StockMasterDocument, trip.dispatch_document_id)
    return TripResponse(
        trip_id=trip.id,
        team_id=trip.team_id,
        team_name=team.name if team else None,
        festival_id=trip.festival_id,
        festival_name=festival.name if festival else None,
        dispatched_at=trip.dispatched_at,
        dispatch_document_id=trip.dispatch_document_id,
        dispatch_doc_number=document.doc_number if document else "",
    )


def _kar_summary(
    db: Session,
    kar: KarTrackerKar,
    contents: dict[int, int],
    needs: dict[int, int],
    team_names: dict[int, str],
    status_names: dict[int, str],
    trip: StockMasterKarTrip | None,
) -> KarSummaryResponse:
    """One kar card: what's in it, and how far it's loaded against its needs."""
    # A kar that's out is measured against what left with it (its balance is empty then):
    # its "Kar vertrekt" plus the follow-up deliveries.
    loaded = dispatched_lines(db, trip) if trip else contents
    return KarSummaryResponse(
        kar_id=kar.id,
        kar_nummer=kar.kar_nummer,
        team_id=kar.team_id,
        team_name=team_names.get(kar.team_id) if kar.team_id else None,
        kartracker_status=status_names.get(kar.status_id),
        is_out=trip is not None,
        trip=_trip_response(db, trip) if trip else None,
        product_count=len(contents),
        total_quantity=sum(contents.values()),
        required_total=sum(needs.values()),
        loaded_toward_required=sum(min(loaded.get(product_id, 0), needed) for product_id, needed in needs.items()),
        # Per product type: a needed product counts as loaded once the kar holds all of it.
        required_product_count=len(needs),
        loaded_product_count=sum(1 for product_id, needed in needs.items() if loaded.get(product_id, 0) >= needed),
    )


def _with_manual(needs: dict[int, int], manual: dict[int, int]) -> dict[int, int]:
    """A kar's needs plus its manual requests per product: what its loading progress
    ("2/3 producten", "13/15 stuks") is measured against.
    """
    total = dict(needs)
    for product_id, quantity in manual.items():
        total[product_id] = total.get(product_id, 0) + quantity
    return total


def _season_demand(db: Session, season_id: int) -> dict[int, int]:
    """{product_id: pieces asked this season over all kars}: kar needs plus manual requests."""
    demand = needs_per_product(db, season_id)
    for kar_manual in manual_requests_by_kar(db, season_id).values():
        for product_id, quantity in kar_manual.items():
            demand[product_id] = demand.get(product_id, 0) + quantity
    return demand


def _open_trips(db: Session) -> dict[int, StockMasterKarTrip]:
    """{kar_id: open trip} for every kar that's out."""
    return {
        trip.kar_id: trip
        for trip in db.scalars(select(StockMasterKarTrip).where(StockMasterKarTrip.return_document_id.is_(None))).all()
    }


def build_kar_summaries(db: Session, season_id: int | None) -> list[KarSummaryResponse]:
    """Every kar of KarTracker as a card, with this season's loading progress."""
    stock = load_stock(db)
    needs = requirements_by_kar(db, season_id) if season_id else {}
    manual = manual_requests_by_kar(db, season_id) if season_id else {}
    team_names = _names(db, Team, Team.name)
    status_names = _names(db, KarTrackerKarStatus, KarTrackerKarStatus.name)
    trips = _open_trips(db)
    return [
        _kar_summary(
            db, kar, stock.kar_contents(kar.id), _with_manual(needs.get(kar.id, {}), manual.get(kar.id, {})),
            team_names, status_names, trips.get(kar.id),
        )
        for kar in db.scalars(select(KarTrackerKar).order_by(KarTrackerKar.kar_nummer)).all()
    ]


def build_kar_detail(db: Session, kar: KarTrackerKar, season_id: int | None) -> KarDetailResponse:
    """A kar's contents versus its needs, what left with it (when out), and
    the festivals its team works this season.
    """
    stock = load_stock(db)
    contents = stock.kar_contents(kar.id)
    needs = requirements_by_kar(db, season_id).get(kar.id, {}) if season_id else {}
    team_names = _names(db, Team, Team.name)
    status_names = _names(db, KarTrackerKarStatus, KarTrackerKarStatus.name)
    trip = open_trip_of(db, kar.id)
    warehouses = _names(db, Warehouse, Warehouse.name)
    # What left with this kar this season and didn't come back (consumed outside the warehouse).
    consumed: dict[int, int] = defaultdict(int)
    if season_id:
        for _team_id, product_id, used in _trip_consumption(db, season_id, kar.id):
            consumed[product_id] += used

    # The products asked for by hand this season (Kar laden's "Manueel" rows).
    manual = list_manual_requests(db, season_id, kar.id) if season_id else []

    product_ids = set(contents) | set(needs) | set(consumed)
    # What the flow diagram needs to work out each row's entitlement: the products' Limiet
    # names, everything asked this season over all kars, and this kar's KarTracker status.
    limit_names = _names(db, ProductLimit, ProductLimit.name)
    demand = _season_demand(db, season_id) if season_id else {}
    kar_status = status_names.get(kar.status_id)
    manual_quantities = {request.product_id: request.quantity for request in manual}
    # The manual requests' products are loaded for their names, but get no kar line of their own:
    # Kar laden shows them on their Manueel row.
    product_rows = select(Product).where(Product.id.in_(product_ids | {request.product_id for request in manual}))
    products = {product.id: product for product in db.scalars(product_rows).all()}

    def entitlement(product: Product, requested: int, cap_used: int = 0) -> EntitlementTrace:
        """The flow diagram for one row of this kar (Altsien Select or Manueel)."""
        return delivery_entitlement(
            product,
            limit_names.get(product.limit_id) if product.limit_id else None,
            requested,
            stock.total(product.id),
            demand.get(product.id, 0),
            kar_status,
            cap_used,
        )

    # The Altsien Select row of each product goes first: a Manueel row only gets what it
    # left of Maximum initiële stock.
    kar_traces = {product_id: entitlement(products[product_id], needs.get(product_id, 0)) for product_id in product_ids}
    lines = []
    for product_id in product_ids:
        product = products[product_id]
        in_kar = contents.get(product_id, 0)
        required = needs.get(product_id, 0)
        trace = kar_traces[product_id]
        lines.append(
            KarLineResponse(
                product_id=product_id,
                name=product.name,
                bin_label=_bin_label(
                    warehouses.get(product.warehouse_id) if product.warehouse_id else None, product.warehouse_location
                ),
                in_kar=in_kar,
                required=required,
                missing=max(required - in_kar, 0),
                surplus=max(in_kar - required, 0) if required else 0,
                free_available=stock.free.get(product_id, 0),
                consumed_outside=consumed.get(product_id, 0),
                is_consumable=product.is_consumable,
                is_blocked=product.is_blocked,
                stock_return_to=product.stock_return_to,
                entitled=trace.entitled,
                entitlement_trace=trace,
            )
        )
    lines.sort(key=lambda line: line.name.lower())

    dispatched = []
    if trip is not None:
        left = dispatched_lines(db, trip)
        left_products = {
            product.id: product for product in db.scalars(select(Product).where(Product.id.in_(set(left)))).all()
        }
        dispatched = sorted(
            (
                DispatchedLineResponse(
                    product_id=product_id,
                    name=left_products[product_id].name,
                    quantity=quantity,
                    is_consumable=left_products[product_id].is_consumable,
                    stock_return_to=left_products[product_id].stock_return_to,
                )
                for product_id, quantity in left.items()
            ),
            key=lambda line: line.name.lower(),
        )

    festivals: list[NamedItem] = []
    if season_id:
        query = select(Festival.id, Festival.name).where(Festival.season_id == season_id)
        team_query = query
        if kar.team_id:
            team_query = query.join(TeamFestival, TeamFestival.festival_id == Festival.id).where(
                TeamFestival.team_id == kar.team_id, TeamFestival.season_id == season_id
            )
        rows = db.execute(team_query.order_by(Festival.start_date)).all() if kar.team_id else []
        # No festivals chosen for the team yet: offer every festival of the season.
        if not rows:
            rows = db.execute(query.order_by(Festival.start_date)).all()
        festivals = [NamedItem(id=festival_id, name=name) for festival_id, name in rows]

    # The Manueel rows, each with its own entitlement (sharing Maximum initiële stock with the Altsien row).
    manual_rows = []
    for request in manual:
        altsien = kar_traces.get(request.product_id)
        trace = entitlement(products[request.product_id], request.quantity, altsien.entitled if altsien else 0)
        manual_rows.append(
            ManualRequestResponse(
                id=request.id, product_id=request.product_id, name=products[request.product_id].name,
                quantity=request.quantity, entitled=trace.entitled, entitlement_trace=trace,
            )
        )

    return KarDetailResponse(
        # The progress counts the manual requests too.
        kar=_kar_summary(
            db, kar, contents,
            _with_manual(needs, manual_quantities),
            team_names, status_names, trip,
        ),
        lines=lines,
        dispatched=dispatched,
        festivals=festivals,
        manual_requests=sorted(manual_rows, key=lambda request: request.name.lower()),
    )


# --- Kar needs (Benodigdheden) ---------------------------------------------
# Shared by StockMaster's own "Benodigdheden" screen and Altsien Select's
# Products wizard step, so both show exactly the same lines.


def build_requirement_responses(db: Session, season_id: int, kar: KarTrackerKar) -> list[RequirementResponse]:
    """A kar's needs with product names, bins and what's in the kar now."""
    detail_lines = {line.product_id: line for line in build_kar_detail(db, kar, season_id).lines}
    result = []
    for row in list_requirements(db, season_id, kar.id):
        line = detail_lines.get(row.product_id)
        product = db.get(Product, row.product_id)
        result.append(
            RequirementResponse(
                product_id=row.product_id,
                product_name=product.name if product else str(row.product_id),
                bin_label=line.bin_label if line else None,
                quantity=row.quantity,
                comment=row.comment,
                in_kar=line.in_kar if line else 0,
                updated_by_name=row.updated_by_name,
                updated_at=row.updated_at,
            )
        )
    result.sort(key=lambda item: item.product_name.lower())
    return result


def build_previous_requirements(db: Session, season: Season, kar_id: int) -> PreviousRequirementsResponse:
    """Last season's needs of the same kar ("Kopieer van vorig seizoen"),
    each with what's already listed this season.
    """
    previous, rows = previous_season_requirements(db, season, kar_id)
    current = {row.product_id: row.quantity for row in list_requirements(db, season.id, kar_id)}
    lines = []
    for row in rows:
        product = db.get(Product, row.product_id)
        lines.append(
            PreviousRequirementLine(
                product_id=row.product_id,
                product_name=product.name if product else str(row.product_id),
                quantity=row.quantity,
                current_quantity=current.get(row.product_id),
            )
        )
    lines.sort(key=lambda item: item.product_name.lower())
    return PreviousRequirementsResponse(season_name=previous.name if previous else None, lines=lines)


# --- Booking history -------------------------------------------------------


@dataclass
class DocumentFilters:
    """The filters of the Boekingen screen."""

    season_id: int | None = None
    doc_type: str | None = None
    product_id: int | None = None
    kar_id: int | None = None
    user_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None


def _belgian_day_start(day: date) -> datetime:
    """Midnight at the start of a Belgian calendar day."""
    return datetime.combine(day, time.min, tzinfo=BELGIAN_TZ)


def list_documents(db: Session, filters: DocumentFilters, offset: int, limit: int) -> tuple[list[DocumentResponse], int]:
    """One page of bookings, newest first, plus the total count."""
    query = select(StockMasterDocument)
    if filters.season_id is not None:
        query = query.where(StockMasterDocument.season_id == filters.season_id)
    if filters.doc_type:
        query = query.where(StockMasterDocument.doc_type == filters.doc_type)
    if filters.kar_id is not None:
        query = query.where(
            or_(StockMasterDocument.kar_id == filters.kar_id, StockMasterDocument.from_kar_id == filters.kar_id)
        )
    if filters.user_id is not None:
        query = query.where(StockMasterDocument.created_by == filters.user_id)
    if filters.product_id is not None:
        query = query.where(
            StockMasterDocument.id.in_(
                select(StockMasterMovement.document_id).where(StockMasterMovement.product_id == filters.product_id)
            )
        )
    if filters.date_from is not None:
        query = query.where(StockMasterDocument.created_at >= _belgian_day_start(filters.date_from))
    if filters.date_to is not None:
        query = query.where(StockMasterDocument.created_at < _belgian_day_start(filters.date_to + timedelta(days=1)))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    documents = db.scalars(
        query.order_by(StockMasterDocument.created_at.desc(), StockMasterDocument.id.desc()).offset(offset).limit(limit)
    ).all()
    return build_document_responses(db, list(documents), with_lines=False), total


def build_document_responses(
    db: Session, documents: list[StockMasterDocument], with_lines: bool
) -> list[DocumentResponse]:
    """Bookings with readable names; the lines only when asked (detail)."""
    if not documents:
        return []
    ids = [document.id for document in documents]
    seasons = _names(db, Season, Season.name)
    teams = _names(db, Team, Team.name)
    festivals = _names(db, Festival, Festival.name)
    reasons = _names(db, StockMasterReason, StockMasterReason.name)

    totals = {
        document_id: (int(count), int(quantity or 0))
        for document_id, count, quantity in db.execute(
            select(
                StockMasterMovement.document_id, func.count(), func.sum(StockMasterMovement.quantity)
            )
            .where(StockMasterMovement.document_id.in_(ids))
            .group_by(StockMasterMovement.document_id)
        ).all()
    }
    # Numbers of the bookings these reverse, and of the reversals that undid them.
    related_ids = {document.reversal_of_id for document in documents if document.reversal_of_id}
    numbers = {
        row_id: number
        for row_id, number in db.execute(
            select(StockMasterDocument.id, StockMasterDocument.doc_number).where(StockMasterDocument.id.in_(related_ids))
        ).all()
    }
    reversed_by = {
        original_id: (row_id, number)
        for row_id, original_id, number in db.execute(
            select(StockMasterDocument.id, StockMasterDocument.reversal_of_id, StockMasterDocument.doc_number).where(
                StockMasterDocument.reversal_of_id.in_(ids)
            )
        ).all()
    }

    lines_by_document: dict[int, list[MovementResponse]] = defaultdict(list)
    if with_lines:
        kar_numbers = _names(db, KarTrackerKar, KarTrackerKar.kar_nummer)
        product_names = _names(db, Product, Product.name)
        for move in db.scalars(
            select(StockMasterMovement)
            .where(StockMasterMovement.document_id.in_(ids))
            .order_by(StockMasterMovement.id)
        ).all():
            lines_by_document[move.document_id].append(
                MovementResponse(
                    product_id=move.product_id,
                    product_name=product_names.get(move.product_id, str(move.product_id)),
                    quantity=move.quantity,
                    from_bucket=move.from_bucket,
                    from_kar_nummer=kar_numbers.get(move.from_kar_id) if move.from_kar_id else None,
                    to_bucket=move.to_bucket,
                    to_kar_nummer=kar_numbers.get(move.to_kar_id) if move.to_kar_id else None,
                    bin_snapshot=move.bin_snapshot,
                )
            )
        for lines in lines_by_document.values():
            lines.sort(key=lambda line: line.product_name.lower())

    result = []
    for document in documents:
        line_count, total_quantity = totals.get(document.id, (0, 0))
        reversal = reversed_by.get(document.id)
        result.append(
            DocumentResponse(
                id=document.id,
                doc_number=document.doc_number,
                doc_type=document.doc_type,
                status=document.status,
                season_id=document.season_id,
                season_name=seasons.get(document.season_id),
                kar_id=document.kar_id,
                kar_nummer=document.kar_nummer,
                from_kar_nummer=document.from_kar_nummer,
                team_name=teams.get(document.team_id) if document.team_id else None,
                festival_name=festivals.get(document.festival_id) if document.festival_id else None,
                reference=document.reference,
                reason_name=reasons.get(document.reason_id) if document.reason_id else None,
                comment=document.comment,
                source=document.source,
                reversal_of_id=document.reversal_of_id,
                reversal_of_number=numbers.get(document.reversal_of_id) if document.reversal_of_id else None,
                reversed_by_id=reversal[0] if reversal else None,
                reversed_by_number=reversal[1] if reversal else None,
                created_by_name=document.created_by_name,
                created_at=document.created_at,
                line_count=line_count,
                total_quantity=total_quantity,
                lines=lines_by_document.get(document.id, []),
            )
        )
    return result


# --- Te bestellen and Telling ----------------------------------------------


def build_order_needs(
    db: Session, season_id: int, warehouse_id: int | None, category_id: int | None
) -> list[OrderNeedResponse]:
    """Per product with needs this season: needed, in stock, to order
    (needs − free − in kars, never below zero).
    """
    needs = needs_per_product(db, season_id)
    if not needs:
        return []
    stock = load_stock(db)
    warehouses = _names(db, Warehouse, Warehouse.name)
    categories = _names(db, ProductCategory, ProductCategory.name)

    query = select(Product).where(Product.id.in_(set(needs)))
    if warehouse_id is not None:
        query = query.where(Product.warehouse_id == warehouse_id)
    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    result = []
    for product in db.scalars(query).all():
        free = stock.free.get(product.id, 0)
        in_kars = stock.kar_total(product.id)
        warehouse_name = warehouses.get(product.warehouse_id) if product.warehouse_id else None
        result.append(
            OrderNeedResponse(
                product_id=product.id,
                name=product.name,
                category_name=categories.get(product.category_id) if product.category_id else None,
                warehouse_id=product.warehouse_id,
                warehouse_name=warehouse_name,
                bin_label=_bin_label(warehouse_name, product.warehouse_location),
                needed=needs[product.id],
                free=free,
                in_kars=in_kars,
                in_stock=free + in_kars,
                to_order=max(needs[product.id] - free - in_kars, 0),
                is_blocked=product.is_blocked,
            )
        )
    # Grouped per warehouse and then by name — the same order as the PDF.
    result.sort(key=lambda line: ((line.warehouse_name or "~").lower(), line.name.lower()))
    return result


def build_count_sheet(
    db: Session,
    *,
    kar_id: int | None,
    warehouse_id: int | None,
    bin_from: str | None,
    bin_to: str | None,
) -> list[CountSheetLine]:
    """The products to count with the quantity expected there: one kar's
    contents, or the free stock of a warehouse (optionally a bin range),
    sorted by bin so the counter can walk the shelves in order.
    """
    stock = load_stock(db)
    warehouses = _names(db, Warehouse, Warehouse.name)

    if kar_id is not None:
        contents = stock.kar_contents(kar_id)
        products = db.scalars(select(Product).where(Product.id.in_(set(contents)))).all()
        expected = contents
    else:
        query = select(Product)
        if warehouse_id is not None:
            query = query.where(Product.warehouse_id == warehouse_id)
        products = db.scalars(query).all()
        low = (bin_from or "").strip().lower()
        high = (bin_to or "").strip().lower()

        def in_range(location: str | None) -> bool:
            """Bin range check, ignoring case; an open end means "no limit"."""
            value = (location or "").strip().lower()
            if low and value < low:
                return False
            # "B" as upper bound also includes "B-12", "B-99"...
            if high and value > high and not value.startswith(high):
                return False
            return True

        products = [product for product in products if in_range(product.warehouse_location)]
        expected = stock.free

    lines = [
        CountSheetLine(
            product_id=product.id,
            name=product.name,
            bin_label=_bin_label(
                warehouses.get(product.warehouse_id) if product.warehouse_id else None, product.warehouse_location
            ),
            warehouse_location=product.warehouse_location,
            expected=expected.get(product.id, 0),
        )
        for product in products
    ]
    lines.sort(key=lambda line: ((line.warehouse_location or "~").lower(), line.name.lower()))
    return lines


# --- KPI -------------------------------------------------------------------


def _trip_consumption(db: Session, season_id: int, kar_id: int | None = None) -> list[tuple[int | None, int, int]]:
    """(team_id, product_id, pieces not returned) per closed trip of the
    season: what left with the kar minus what came back. With a kar_id,
    only that kar's trips (Kar laden's "Reeds in kar buiten magazijn").
    """
    result = []
    query = select(StockMasterKarTrip).where(
        StockMasterKarTrip.season_id == season_id, StockMasterKarTrip.return_document_id.is_not(None)
    )
    if kar_id is not None:
        query = query.where(StockMasterKarTrip.kar_id == kar_id)
    trips = db.scalars(query).all()
    for trip in trips:
        left = dispatched_lines(db, trip)
        returned: dict[int, int] = defaultdict(int)
        for product_id, quantity in db.execute(
            select(StockMasterMovement.product_id, StockMasterMovement.quantity).where(
                StockMasterMovement.document_id == trip.return_document_id
            )
        ).all():
            returned[product_id] += quantity
        for product_id, quantity in left.items():
            used = quantity - returned.get(product_id, 0)
            if used > 0:
                result.append((trip.team_id, product_id, used))
    return result


def build_dashboard(db: Session, season_id: int) -> DashboardResponse:
    """Tiles and charts of the KPI main page for one season."""
    stock = load_stock(db)
    free_stock = sum(stock.free.values())
    in_kars = sum(sum(per_kar.values()) for per_kar in stock.in_kars.values())

    kar_count = db.scalar(select(func.count()).select_from(KarTrackerKar)) or 0
    kars_out = len(_open_trips(db))

    needs = requirements_by_kar(db, season_id)
    kars_complete = 0
    for kar_id, kar_needs in needs.items():
        contents = stock.kar_contents(kar_id)
        if all(contents.get(product_id, 0) >= needed for product_id, needed in kar_needs.items()):
            kars_complete += 1

    order_lines = sum(1 for line in build_order_needs(db, season_id, None, None) if line.to_order > 0)

    # Bookings per month and type (reversed ones and reversals left out).
    per_month: dict[tuple[str, str], int] = defaultdict(int)
    for doc_type, created_at in db.execute(
        select(StockMasterDocument.doc_type, StockMasterDocument.created_at).where(
            StockMasterDocument.season_id == season_id,
            StockMasterDocument.status != REVERSED,
            StockMasterDocument.reversal_of_id.is_(None),
        )
    ).all():
        per_month[(to_belgian(created_at).strftime("%Y-%m"), doc_type)] += 1
    bookings_per_month = [
        MonthActionCount(month=month, doc_type=doc_type, count=count)
        for (month, doc_type), count in sorted(per_month.items())
    ]

    # Consumption: what didn't come back from trips, plus "Uitboeken".
    team_names = _names(db, Team, Team.name)
    product_names = _names(db, Product, Product.name)
    per_team: dict[str, int] = defaultdict(int)
    per_product: dict[int, int] = defaultdict(int)
    for team_id, product_id, used in _trip_consumption(db, season_id):
        per_team[team_names.get(team_id, "-") if team_id else "-"] += used
        per_product[product_id] += used
    for product_id, quantity in db.execute(
        select(StockMasterMovement.product_id, StockMasterMovement.quantity)
        .join(StockMasterDocument, StockMasterDocument.id == StockMasterMovement.document_id)
        .where(
            StockMasterDocument.season_id == season_id,
            StockMasterDocument.doc_type == BOOK_OUT,
            StockMasterDocument.status != REVERSED,
        )
    ).all():
        per_product[product_id] += quantity

    def top(values: dict, names: dict | None) -> list[NamedQuantity]:
        """The ten biggest, largest first."""
        ranked = sorted(values.items(), key=lambda item: item[1], reverse=True)[:10]
        return [NamedQuantity(name=names.get(key, str(key)) if names else key, quantity=value) for key, value in ranked]

    return DashboardResponse(
        total_stock=free_stock + in_kars,
        free_stock=free_stock,
        in_kars=in_kars,
        kars_in_warehouse=kar_count - kars_out,
        kars_out=kars_out,
        kars_with_needs=len(needs),
        kars_complete=kars_complete,
        below_minimum=count_below_minimum(db),
        order_lines=order_lines,
        bookings_per_month=bookings_per_month,
        consumption_per_team=top(per_team, None),
        top_consumed_products=top(per_product, product_names),
    )

