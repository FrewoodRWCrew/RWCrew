# StockMaster's booking engine: the ONLY place that changes stock.
#
# Every booking is one StockMaster_document with one ledger line
# (StockMaster_movement) per product moved, and the current stock per place
# (StockMaster_balance) is updated in the same database transaction. Each
# balance row is locked first (SELECT ... FOR UPDATE), so two people can
# never both take the last piece: stock can never go negative.
#
# A product's stock is in exactly one of three places ("buckets"):
#   - "free"     free stock on the product's fixed bin in its warehouse
#   - "kar"      loaded in a kar standing in the warehouse
#   - "external" outside our stock (supplier, team/festival, used, lost)
#
# Kar stock only exists while the kar is in the warehouse: "Kar vertrekt"
# books its whole contents out and opens a StockMaster_kar_trip; "Kar terug"
# books what came back in (into the kar or straight to free stock) and
# closes the trip. A kar with an open trip can't be loaded or unloaded.
#
# The functions below don't depend on a web request (the user and season
# are passed in) and never commit: the caller commits once everything
# succeeded. That way the screens and, later, automated bookings from
# TagScan CSVs (module_1/line_processing.py) follow exactly the same rules.

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import belgian_now
from app.db.models.festival import Festival
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.season import Season
from app.db.models.stockmaster_balance import StockMasterBalance
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.stockmaster_kar_trip import StockMasterKarTrip
from app.db.models.stockmaster_movement import StockMasterMovement
from app.db.models.stockmaster_reason import StockMasterReason
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.warehouse import Warehouse

FREE = "free"
KAR = "kar"
EXTERNAL = "external"

# Every booking type, in the order of the warehouse process (the same order
# as the "Akties" menu), plus the reversal of one of them.
BOOK_IN = "book_in"
KAR_LOAD = "kar_load"
BOOK_OUT = "book_out"
KAR_DISPATCH = "kar_dispatch"
KAR_RETURN = "kar_return"
KAR_UNLOAD = "kar_unload"
COUNT = "count"
REVERSAL = "reversal"
DOC_TYPES = (BOOK_IN, KAR_LOAD, BOOK_OUT, KAR_DISPATCH, KAR_RETURN, KAR_UNLOAD, COUNT, REVERSAL)

POSTED = "posted"
REVERSED = "reversed"


class StockError(Exception):
    """A booking that breaks one of the stock rules. `code` is a stable
    key the frontend translates; `params` fill in the details (product
    name, available quantity, kar number...).
    """

    def __init__(self, code: str, *params: object, status_code: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.params = [str(param) for param in params]
        self.status_code = status_code

    @property
    def detail(self) -> str:
        """"code|param|param" — what the API returns as its error detail."""
        return "|".join([self.code, *self.params])


@dataclass
class BookingLine:
    """One product line as entered on a booking screen (or, later, grouped
    from a TagScan CSV).
    """

    product_id: int
    quantity: int
    # Only on "Kar terug": where the returned pieces go ("kar" or "free").
    destination: str | None = None
    # Later: the TagScan scan lines this line was booked from.
    tagscan_line_ids: list[int] = field(default_factory=list)


@dataclass
class BookingOrigin:
    """Where a booking came from: a screen ("manual") or, later, an
    automated TagScan run with its scan file.
    """

    source: str = "manual"
    tagscan_header_id: int | None = None


@dataclass
class _Move:
    """One ledger line to post: a quantity from one place to another."""

    product_id: int
    quantity: int
    from_bucket: str
    from_kar_id: int | None
    to_bucket: str
    to_kar_id: int | None
    tagscan_line_id: int | None = None


# --- Lookups ---------------------------------------------------------------


def get_product(db: Session, product_id: int) -> Product:
    """Load a product, or refuse the booking."""
    product = db.get(Product, product_id)
    if product is None:
        raise StockError("product_not_found", product_id, status_code=404)
    return product


def get_kar(db: Session, kar_id: int) -> KarTrackerKar:
    """Load a kar, or refuse the booking."""
    kar = db.get(KarTrackerKar, kar_id)
    if kar is None:
        raise StockError("kar_not_found", kar_id, status_code=404)
    return kar


def open_trip_of(db: Session, kar_id: int) -> StockMasterKarTrip | None:
    """The kar's current trip while it's out of the warehouse, if any."""
    return db.scalar(
        select(StockMasterKarTrip)
        .where(StockMasterKarTrip.kar_id == kar_id, StockMasterKarTrip.return_document_id.is_(None))
        .order_by(StockMasterKarTrip.id.desc())
        .limit(1)
    )


def ensure_kar_in_warehouse(db: Session, kar: KarTrackerKar) -> None:
    """Refuse loading/unloading/counting a kar that's out (onderweg)."""
    if open_trip_of(db, kar.id) is not None:
        raise StockError("kar_out", kar.kar_nummer)


def balance_quantity(db: Session, product_id: int, kar_id: int | None) -> int:
    """How many pieces of a product lie in one place right now."""
    query = select(StockMasterBalance.quantity).where(StockMasterBalance.product_id == product_id)
    query = query.where(StockMasterBalance.kar_id.is_(None) if kar_id is None else StockMasterBalance.kar_id == kar_id)
    return db.scalar(query) or 0


def kar_contents(db: Session, kar_id: int) -> dict[int, int]:
    """{product_id: quantity} of everything loaded in one kar."""
    rows = db.execute(
        select(StockMasterBalance.product_id, StockMasterBalance.quantity).where(StockMasterBalance.kar_id == kar_id)
    ).all()
    return {product_id: quantity for product_id, quantity in rows}


def bin_label(db: Session, product: Product) -> str | None:
    """The product's warehouse + bin as one readable text ("Hal A · B-12")."""
    warehouse = db.get(Warehouse, product.warehouse_id) if product.warehouse_id else None
    parts = [part for part in (warehouse.name if warehouse else None, product.warehouse_location) if part]
    return " · ".join(parts) or None


def _place_label(db: Session, kar_id: int | None) -> str:
    """How a place reads in an error: the kar number, or "free"."""
    if kar_id is None:
        return FREE
    kar = db.get(KarTrackerKar, kar_id)
    return kar.kar_nummer if kar else str(kar_id)


# --- Posting ---------------------------------------------------------------


def _change_balance(db: Session, product: Product, kar_id: int | None, delta: int) -> None:
    """Add (or with a negative delta, take) pieces in one place, after
    locking that place's row. Refuses to go below zero; an emptied row is
    removed, so a balance row always means "there is stock here".
    """
    query = select(StockMasterBalance).where(StockMasterBalance.product_id == product.id)
    query = query.where(StockMasterBalance.kar_id.is_(None) if kar_id is None else StockMasterBalance.kar_id == kar_id)
    balance = db.scalar(query.with_for_update())

    available = balance.quantity if balance else 0
    new_quantity = available + delta
    if new_quantity < 0:
        raise StockError("insufficient_stock", product.name, available, _place_label(db, kar_id))

    if balance is None:
        db.add(StockMasterBalance(product_id=product.id, kar_id=kar_id, quantity=new_quantity))
    elif new_quantity == 0:
        db.delete(balance)
    else:
        balance.quantity = new_quantity
        balance.updated_at = datetime.now(timezone.utc)
    # Write right away, so a later line in the same booking sees this one.
    db.flush()


def _new_document(
    db: Session,
    user: User,
    season: Season,
    doc_type: str,
    origin: BookingOrigin | None = None,
    **fields: object,
) -> StockMasterDocument:
    """Create the booking's header, stored under the given (logged-in) user,
    and give it its readable number (SM-<Belgian year>-<id>).
    """
    origin = origin or BookingOrigin()
    document = StockMasterDocument(
        doc_number=f"TMP-{datetime.now(timezone.utc).timestamp()}",
        doc_type=doc_type,
        season_id=season.id,
        status=POSTED,
        source=origin.source,
        tagscan_header_id=origin.tagscan_header_id,
        created_by=user.id,
        created_by_name=user.display_name,
        **fields,
    )
    db.add(document)
    db.flush()
    document.doc_number = f"SM-{belgian_now().year}-{document.id:05d}"
    db.flush()
    return document


def _post_moves(db: Session, document: StockMasterDocument, user: User, moves: Iterable[_Move]) -> None:
    """Write the ledger lines and update the balances. Lines are handled in
    product order, so two bookings always lock rows in the same order.
    """
    for move in sorted(moves, key=lambda item: (item.product_id, item.from_kar_id or 0, item.to_kar_id or 0)):
        if move.quantity <= 0:
            raise StockError("invalid_quantity")
        product = get_product(db, move.product_id)

        # Take from the source first, then add at the destination.
        if move.from_bucket != EXTERNAL:
            _change_balance(db, product, move.from_kar_id, -move.quantity)
        if move.to_bucket != EXTERNAL:
            _change_balance(db, product, move.to_kar_id, move.quantity)

        db.add(
            StockMasterMovement(
                document_id=document.id,
                product_id=product.id,
                quantity=move.quantity,
                from_bucket=move.from_bucket,
                from_kar_id=move.from_kar_id,
                to_bucket=move.to_bucket,
                to_kar_id=move.to_kar_id,
                bin_snapshot=bin_label(db, product),
                tagscan_line_id=move.tagscan_line_id,
                created_by=user.id,
                created_by_name=user.display_name,
            )
        )
    db.flush()


def _merge_lines(lines: Iterable[BookingLine]) -> list[BookingLine]:
    """Add up lines for the same product (and destination), so a product
    typed twice in the basket becomes one ledger line.
    """
    merged: dict[tuple[int, str | None], BookingLine] = {}
    for line in lines:
        if line.quantity <= 0:
            raise StockError("invalid_quantity")
        key = (line.product_id, line.destination)
        if key in merged:
            merged[key].quantity += line.quantity
            merged[key].tagscan_line_ids.extend(line.tagscan_line_ids)
        else:
            merged[key] = BookingLine(line.product_id, line.quantity, line.destination, list(line.tagscan_line_ids))
    if not merged:
        raise StockError("no_lines")
    return list(merged.values())


def _moves_for(lines: list[BookingLine], from_bucket: str, from_kar_id: int | None, to_bucket: str, to_kar_id: int | None) -> list[_Move]:
    """The same from/to for every line. A line booked from several TagScan
    lines keeps the link on its first one (the rest are linked by the
    document's scan file).
    """
    return [
        _Move(
            line.product_id,
            line.quantity,
            from_bucket,
            from_kar_id,
            to_bucket,
            to_kar_id,
            line.tagscan_line_ids[0] if line.tagscan_line_ids else None,
        )
        for line in lines
    ]


def _ensure_not_blocked(db: Session, lines: list[BookingLine]) -> None:
    """Blocked products (MasterData) can't be booked in or loaded."""
    for line in lines:
        product = get_product(db, line.product_id)
        if product.is_blocked:
            raise StockError("product_blocked", product.name)


def _ensure_reason(db: Session, reason_id: int | None, required: bool) -> None:
    """A chosen reason must exist; on some bookings one is required."""
    if reason_id is None:
        if required:
            raise StockError("reason_required")
        return
    if db.get(StockMasterReason, reason_id) is None:
        raise StockError("reason_not_found", status_code=404)


# --- The bookings ----------------------------------------------------------


def book_in(
    db: Session,
    user: User,
    season: Season,
    lines: Iterable[BookingLine],
    *,
    reference: str | None = None,
    reason_id: int | None = None,
    comment: str | None = None,
    origin: BookingOrigin | None = None,
) -> StockMasterDocument:
    """Inboeken: goods arrive and go to free stock."""
    merged = _merge_lines(lines)
    _ensure_not_blocked(db, merged)
    _ensure_reason(db, reason_id, required=False)
    document = _new_document(
        db, user, season, BOOK_IN, origin, reference=reference, reason_id=reason_id, comment=comment
    )
    _post_moves(db, document, user, _moves_for(merged, EXTERNAL, None, FREE, None))
    return document


def book_out(
    db: Session,
    user: User,
    season: Season,
    lines: Iterable[BookingLine],
    *,
    reason_id: int | None,
    from_kar_id: int | None = None,
    reference: str | None = None,
    comment: str | None = None,
    origin: BookingOrigin | None = None,
) -> StockMasterDocument:
    """Uitboeken: used, broken or lost goods leave the stock — from free
    stock, or out of a kar standing in the warehouse. A reason is required.
    """
    merged = _merge_lines(lines)
    _ensure_reason(db, reason_id, required=True)
    kar = None
    if from_kar_id is not None:
        kar = get_kar(db, from_kar_id)
        ensure_kar_in_warehouse(db, kar)
    document = _new_document(
        db,
        user,
        season,
        BOOK_OUT,
        origin,
        kar_id=kar.id if kar else None,
        kar_nummer=kar.kar_nummer if kar else None,
        reference=reference,
        reason_id=reason_id,
        comment=comment,
    )
    from_bucket = KAR if kar else FREE
    _post_moves(db, document, user, _moves_for(merged, from_bucket, kar.id if kar else None, EXTERNAL, None))
    return document


def load_kar(
    db: Session,
    user: User,
    season: Season,
    kar_id: int,
    lines: Iterable[BookingLine],
    *,
    from_kar_id: int | None = None,
    reference: str | None = None,
    comment: str | None = None,
    origin: BookingOrigin | None = None,
) -> StockMasterDocument:
    """Kar laden: from free stock (or from another kar) into a kar."""
    merged = _merge_lines(lines)
    _ensure_not_blocked(db, merged)
    kar = get_kar(db, kar_id)
    ensure_kar_in_warehouse(db, kar)
    source_kar = None
    if from_kar_id is not None:
        if from_kar_id == kar_id:
            raise StockError("same_kar")
        source_kar = get_kar(db, from_kar_id)
        ensure_kar_in_warehouse(db, source_kar)
    document = _new_document(
        db,
        user,
        season,
        KAR_LOAD,
        origin,
        kar_id=kar.id,
        kar_nummer=kar.kar_nummer,
        from_kar_id=source_kar.id if source_kar else None,
        from_kar_nummer=source_kar.kar_nummer if source_kar else None,
        reference=reference,
        comment=comment,
    )
    from_bucket = KAR if source_kar else FREE
    _post_moves(
        db, document, user, _moves_for(merged, from_bucket, source_kar.id if source_kar else None, KAR, kar.id)
    )
    return document


def unload_kar(
    db: Session,
    user: User,
    season: Season,
    kar_id: int,
    lines: Iterable[BookingLine],
    *,
    comment: str | None = None,
    origin: BookingOrigin | None = None,
) -> StockMasterDocument:
    """Kar uitladen: from a kar back to free stock."""
    merged = _merge_lines(lines)
    kar = get_kar(db, kar_id)
    ensure_kar_in_warehouse(db, kar)
    document = _new_document(
        db, user, season, KAR_UNLOAD, origin, kar_id=kar.id, kar_nummer=kar.kar_nummer, comment=comment
    )
    _post_moves(db, document, user, _moves_for(merged, KAR, kar.id, FREE, None))
    return document


def dispatch_kar(
    db: Session,
    user: User,
    season: Season,
    kar_id: int,
    *,
    team_id: int | None = None,
    festival_id: int | None = None,
    reference: str | None = None,
    comment: str | None = None,
    origin: BookingOrigin | None = None,
) -> StockMasterDocument:
    """Kar vertrekt: the kar's whole contents leave the warehouse with it,
    and a trip is opened (the kar is "onderweg" until Kar terug). The team
    defaults to the kar's own team in KarTracker.
    """
    kar = get_kar(db, kar_id)
    ensure_kar_in_warehouse(db, kar)
    team_id = team_id if team_id is not None else kar.team_id
    if team_id is not None and db.get(Team, team_id) is None:
        raise StockError("team_not_found", status_code=404)
    if festival_id is not None and db.get(Festival, festival_id) is None:
        raise StockError("festival_not_found", status_code=404)

    document = _new_document(
        db,
        user,
        season,
        KAR_DISPATCH,
        origin,
        kar_id=kar.id,
        kar_nummer=kar.kar_nummer,
        team_id=team_id,
        festival_id=festival_id,
        reference=reference,
        comment=comment,
    )
    contents = kar_contents(db, kar.id)
    _post_moves(
        db,
        document,
        user,
        [_Move(product_id, quantity, KAR, kar.id, EXTERNAL, None) for product_id, quantity in contents.items()],
    )
    db.add(
        StockMasterKarTrip(
            kar_id=kar.id,
            season_id=season.id,
            team_id=team_id,
            festival_id=festival_id,
            dispatch_document_id=document.id,
        )
    )
    db.flush()
    return document


def dispatched_lines(db: Session, trip: StockMasterKarTrip) -> dict[int, int]:
    """{product_id: quantity} that left with the kar on this trip."""
    rows = db.execute(
        select(StockMasterMovement.product_id, StockMasterMovement.quantity).where(
            StockMasterMovement.document_id == trip.dispatch_document_id
        )
    ).all()
    result: dict[int, int] = {}
    for product_id, quantity in rows:
        result[product_id] = result.get(product_id, 0) + quantity
    return result


def return_kar(
    db: Session,
    user: User,
    season: Season,
    kar_id: int,
    lines: Iterable[BookingLine],
    *,
    comment: str | None = None,
    origin: BookingOrigin | None = None,
) -> StockMasterDocument:
    """Kar terug: the kar is back. Each returned line goes back into the kar
    or straight to free stock (the line's destination, defaulted on the
    screen from the product's "stock_return_to" setting). What isn't
    returned simply stays out (consumed/lost). Closes the trip. A kar can
    also come back empty (no lines).
    """
    kar = get_kar(db, kar_id)
    trip = open_trip_of(db, kar.id)
    if trip is None:
        raise StockError("kar_not_out", kar.kar_nummer)

    line_list = [line for line in lines if line.quantity != 0]
    merged = _merge_lines(line_list) if line_list else []
    for line in merged:
        if line.destination not in (KAR, FREE):
            raise StockError("invalid_destination")

    document = _new_document(
        db,
        user,
        season,
        KAR_RETURN,
        origin,
        kar_id=kar.id,
        kar_nummer=kar.kar_nummer,
        team_id=trip.team_id,
        festival_id=trip.festival_id,
        comment=comment,
    )
    # Close the trip first: the kar is back in the warehouse, so it can
    # receive stock again.
    trip.return_document_id = document.id
    trip.returned_at = datetime.now(timezone.utc)
    db.flush()

    moves = [
        _Move(
            line.product_id,
            line.quantity,
            EXTERNAL,
            None,
            line.destination,
            kar.id if line.destination == KAR else None,
        )
        for line in merged
    ]
    _post_moves(db, document, user, moves)
    return document


@dataclass
class CountLine:
    """One counted product: what was really found in the place."""

    product_id: int
    counted: int


def count_stock(
    db: Session,
    user: User,
    season: Season,
    lines: Iterable[CountLine],
    *,
    kar_id: int | None = None,
    reason_id: int | None = None,
    comment: str | None = None,
    origin: BookingOrigin | None = None,
) -> StockMasterDocument:
    """Telling: compare the counted quantities with the expected ones (free
    stock, or one kar) and book only the differences. Refused when nothing
    differs.
    """
    kar = None
    if kar_id is not None:
        kar = get_kar(db, kar_id)
        ensure_kar_in_warehouse(db, kar)
    _ensure_reason(db, reason_id, required=False)

    bucket = KAR if kar else FREE
    place_kar_id = kar.id if kar else None
    moves: list[_Move] = []
    seen: set[int] = set()
    for line in lines:
        if line.counted < 0:
            raise StockError("invalid_quantity")
        if line.product_id in seen:
            raise StockError("duplicate_product")
        seen.add(line.product_id)
        get_product(db, line.product_id)
        difference = line.counted - balance_quantity(db, line.product_id, place_kar_id)
        if difference > 0:
            moves.append(_Move(line.product_id, difference, EXTERNAL, None, bucket, place_kar_id))
        elif difference < 0:
            moves.append(_Move(line.product_id, -difference, bucket, place_kar_id, EXTERNAL, None))
    if not moves:
        raise StockError("no_differences")

    document = _new_document(
        db,
        user,
        season,
        COUNT,
        origin,
        kar_id=place_kar_id,
        kar_nummer=kar.kar_nummer if kar else None,
        reason_id=reason_id,
        comment=comment,
    )
    _post_moves(db, document, user, moves)
    return document


def reverse_document(
    db: Session,
    user: User,
    document: StockMasterDocument,
    *,
    comment: str | None = None,
) -> StockMasterDocument:
    """Ongedaan maken: book the exact opposite of a booking in a new
    "reversal" document (the original stays, marked "reversed"). Refused
    when it would make stock negative, for a reversal itself, or twice.

    - Reversing "Kar vertrekt" puts the contents back in the kar and removes
      the trip (only while the kar is still out).
    - Reversing "Kar terug" takes the returned goods out again and reopens
      the trip (only for the kar's latest trip, while it's in the warehouse).
    """
    if document.doc_type == REVERSAL:
        raise StockError("cannot_reverse_reversal")
    if document.status == REVERSED:
        raise StockError("already_reversed")

    season = db.get(Season, document.season_id)
    trip_to_remove: StockMasterKarTrip | None = None
    trip_to_reopen: StockMasterKarTrip | None = None
    if document.doc_type == KAR_DISPATCH:
        trip_to_remove = db.scalar(
            select(StockMasterKarTrip).where(StockMasterKarTrip.dispatch_document_id == document.id)
        )
        if trip_to_remove is None or trip_to_remove.return_document_id is not None:
            raise StockError("kar_already_returned", document.kar_nummer or "")
    elif document.doc_type == KAR_RETURN:
        trip_to_reopen = db.scalar(
            select(StockMasterKarTrip).where(StockMasterKarTrip.return_document_id == document.id)
        )
        if trip_to_reopen is None:
            raise StockError("trip_not_found", status_code=404)
        latest_trip = db.scalar(
            select(StockMasterKarTrip)
            .where(StockMasterKarTrip.kar_id == trip_to_reopen.kar_id)
            .order_by(StockMasterKarTrip.id.desc())
            .limit(1)
        )
        if latest_trip is None or latest_trip.id != trip_to_reopen.id:
            raise StockError("kar_left_again", document.kar_nummer or "")

    original_moves = db.scalars(
        select(StockMasterMovement).where(StockMasterMovement.document_id == document.id)
    ).all()

    # Any kar touched by the reversal must be in the warehouse — except the
    # kar of a "Kar vertrekt" being undone (it comes back by this reversal).
    if trip_to_remove is not None:
        db.delete(trip_to_remove)
        db.flush()
    for kar_id in {move.from_kar_id for move in original_moves} | {move.to_kar_id for move in original_moves}:
        if kar_id is not None and open_trip_of(db, kar_id) is not None:
            raise StockError("kar_out", _place_label(db, kar_id))

    reversal = _new_document(
        db,
        user,
        season,
        REVERSAL,
        None,
        kar_id=document.kar_id,
        kar_nummer=document.kar_nummer,
        from_kar_id=document.from_kar_id,
        from_kar_nummer=document.from_kar_nummer,
        team_id=document.team_id,
        festival_id=document.festival_id,
        reversal_of_id=document.id,
        comment=comment,
    )
    _post_moves(
        db,
        reversal,
        user,
        [
            _Move(move.product_id, move.quantity, move.to_bucket, move.to_kar_id, move.from_bucket, move.from_kar_id)
            for move in original_moves
        ],
    )
    document.status = REVERSED

    # The kar goes out again: its trip is open once more.
    if trip_to_reopen is not None:
        trip_to_reopen.return_document_id = None
        trip_to_reopen.returned_at = None
    db.flush()
    return reversal
