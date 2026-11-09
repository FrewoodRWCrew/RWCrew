# A StockMaster booking made on the RWCrew Pi: the read RFID tags (one tag =
# one piece of its product) plus the untagged pieces the operator added by
# hand become an ordinary booking in stock_service.py, and the tags move to
# their new place in tag_service.py — all in the caller's one transaction.
#
# What each action does with the tags (see tag_service for the places):
#   book_in       read tags + extra pieces → free stock; tags become "free"
#   kar_load      → the kar (or straight out on its trip when the kar is out)
#   kar_unload    kar → free stock
#   book_out      Scrap: free stock or a kar → out, with a reason; "written_off"
#   kar_dispatch  "correct, then book": the read pieces are compared with the
#                 kar's contents; extra pieces are loaded, the missing ones go
#                 back to free stock or are written off (the operator's choice
#                 per product, `missing`), then the whole kar leaves
#   kar_return    the returned pieces go into the kar or to free stock (per
#                 product); unread tags stay out (consumed)
#   count         Telling of free stock or a kar: the counted quantity per
#                 product = tags + untagged pieces; read tags get the counted
#                 place, known-but-unread tags of those products become unknown
#
# Never commits: the router does.

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from app.db.models.season import Season
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.user import User
from app.modules.module_1.tag_trace import Reader
from app.modules.module_4 import stock_service, tag_service
from app.modules.module_4.stock_service import BookingLine, BookingOrigin, CountLine, StockError

PI_ORIGIN = "pi"


@dataclass
class ManualLine:
    """Untagged pieces added by hand on the Pi ("Product toevoegen"). On Kar
    terug the destination also applies to the product's tagged pieces; on a
    count, quantity 0 without tags means "counted, none found"."""

    product_id: int
    quantity: int
    destination: str | None = None


@dataclass
class MissingLine:
    """Kar vertrekt: pieces the kar should hold that weren't there, and where
    they go ("free" = back to free stock, "written_off" = booked out)."""

    product_id: int
    quantity: int
    destination: str


@dataclass
class TagBookingCommand:
    """Everything the Pi sends for one booking."""

    action: str
    season: Season
    epcs: list[str]
    lines: list[ManualLine] = field(default_factory=list)
    missing: list[MissingLine] = field(default_factory=list)
    kar_id: int | None = None
    reason_id: int | None = None
    team_id: int | None = None
    festival_id: int | None = None
    reference: str | None = None
    comment: str | None = None
    reader: Reader | None = None


@dataclass
class TagBookingResult:
    """The booking made (and, for Kar vertrekt, the corrections before it)."""

    document: StockMasterDocument
    corrections: list[StockMasterDocument]
    pieces: int
    tags: int


def _required_kar(kar_id: int | None) -> int:
    """Kar bookings need a kar."""
    if kar_id is None:
        raise StockError("kar_required")
    return kar_id


def _manual_counts(lines: list[ManualLine]) -> dict[int, int]:
    """{product id: untagged pieces} of the hand-added lines."""
    counts: dict[int, int] = defaultdict(int)
    for line in lines:
        if line.quantity < 0:
            raise StockError("invalid_quantity")
        counts[line.product_id] += line.quantity
    return dict(counts)


def _booking_lines(*counts: dict[int, int]) -> list[BookingLine]:
    """One booking line per product with the pieces of all given counts."""
    total: dict[int, int] = defaultdict(int)
    for count in counts:
        for product_id, quantity in count.items():
            total[product_id] += quantity
    return [BookingLine(product_id, quantity) for product_id, quantity in sorted(total.items()) if quantity > 0]


def _tags_of(tags: list[RfidTag], product_id: int) -> list[RfidTag]:
    """The tags of one product."""
    return [tag for tag in tags if tag.assigned_product_id == product_id]


def post_tag_booking(db: Session, user: User, command: TagBookingCommand) -> TagBookingResult:
    """Make one Pi booking with its tags (see the module header)."""
    tags = tag_service.tags_for_booking(db, command.epcs)
    tag_service.check_places(db, command.action, tags, kar_id=command.kar_id)
    tag_counts = tag_service.count_by_product(tags)
    manual = _manual_counts(command.lines)
    origin = BookingOrigin(source=PI_ORIGIN)
    reader = command.reader
    action = command.action
    corrections: list[StockMasterDocument] = []

    if action == tag_service.BOOK_IN:
        document = stock_service.book_in(
            db, user, command.season, _booking_lines(tag_counts, manual),
            reference=command.reference, reason_id=command.reason_id, comment=command.comment, origin=origin,
        )
        tag_service.apply_places(db, document, tags, tag_service.FREE, reader=reader)

    elif action == tag_service.KAR_LOAD:
        kar_id = _required_kar(command.kar_id)
        document = stock_service.load_kar(
            db, user, command.season, kar_id, _booking_lines(tag_counts, manual),
            reference=command.reference, comment=command.comment, origin=origin,
        )
        # Loaded into a kar that is out: a follow-up delivery on its trip.
        if document.trip_id is not None:
            tag_service.apply_places(
                db, document, tags, tag_service.OUT, to_kar_id=kar_id, to_trip_id=document.trip_id, reader=reader
            )
        else:
            tag_service.apply_places(db, document, tags, tag_service.KAR, to_kar_id=kar_id, reader=reader)

    elif action == tag_service.KAR_UNLOAD:
        document = stock_service.unload_kar(
            db, user, command.season, _required_kar(command.kar_id), _booking_lines(tag_counts, manual),
            comment=command.comment, origin=origin,
        )
        tag_service.apply_places(db, document, tags, tag_service.FREE, reader=reader)

    elif action == tag_service.BOOK_OUT:
        document = stock_service.book_out(
            db, user, command.season, _booking_lines(tag_counts, manual),
            reason_id=command.reason_id, from_kar_id=command.kar_id,
            reference=command.reference, comment=command.comment, origin=origin,
        )
        tag_service.apply_places(db, document, tags, tag_service.WRITTEN_OFF, reader=reader)

    elif action == tag_service.KAR_RETURN:
        document = _kar_return(db, user, command, tags, tag_counts, origin)

    elif action == tag_service.COUNT:
        document = _count(db, user, command, tags, tag_counts, manual, origin)

    elif action == tag_service.KAR_DISPATCH:
        document, corrections = _kar_dispatch(db, user, command, tags, tag_counts, manual, origin)

    else:
        raise StockError("invalid_action")

    return TagBookingResult(
        document=document,
        corrections=corrections,
        pieces=sum(tag_counts.values()) + sum(manual.values()),
        tags=len(tags),
    )


def _kar_return(
    db: Session,
    user: User,
    command: TagBookingCommand,
    tags: list[RfidTag],
    tag_counts: dict[int, int],
    origin: BookingOrigin,
) -> StockMasterDocument:
    """Kar terug: per product into the kar or to free stock (the line's
    destination, else the product's own "stock_return_to")."""
    kar_id = _required_kar(command.kar_id)
    destinations: dict[int, str] = {}
    untagged: dict[int, int] = defaultdict(int)
    for line in command.lines:
        if line.destination is not None:
            if line.destination not in (stock_service.KAR, stock_service.FREE):
                raise StockError("invalid_destination")
            destinations[line.product_id] = line.destination
        untagged[line.product_id] += line.quantity
    for product_id in set(tag_counts) | set(untagged):
        if product_id not in destinations:
            product = db.get(Product, product_id)
            if product is None:
                raise StockError("product_not_found", product_id, status_code=404)
            destinations[product_id] = product.stock_return_to if product.stock_return_to in ("kar", "free") else "kar"

    lines = [
        BookingLine(product_id, tag_counts.get(product_id, 0) + untagged.get(product_id, 0), destinations[product_id])
        for product_id in sorted(destinations)
        if tag_counts.get(product_id, 0) + untagged.get(product_id, 0) > 0
    ]
    document = stock_service.return_kar(
        db, user, command.season, kar_id, lines, comment=command.comment, origin=origin
    )
    for destination in (stock_service.KAR, stock_service.FREE):
        product_tags = [tag for tag in tags if destinations.get(tag.assigned_product_id) == destination]
        if destination == stock_service.KAR:
            tag_service.apply_places(db, document, product_tags, tag_service.KAR, to_kar_id=kar_id, reader=command.reader)
        else:
            tag_service.apply_places(db, document, product_tags, tag_service.FREE, reader=command.reader)
    return document


def _count(
    db: Session,
    user: User,
    command: TagBookingCommand,
    tags: list[RfidTag],
    tag_counts: dict[int, int],
    manual: dict[int, int],
    origin: BookingOrigin,
) -> StockMasterDocument:
    """Telling of free stock (no kar) or one kar: every product read or added
    (also with 0) is counted; only differences are booked, but the tags'
    places are always recorded."""
    counted = sorted(set(tag_counts) | set(manual))
    if not counted:
        raise StockError("no_lines")
    document = stock_service.count_stock(
        db, user, command.season,
        [CountLine(product_id, tag_counts.get(product_id, 0) + manual.get(product_id, 0)) for product_id in counted],
        kar_id=command.kar_id, reason_id=command.reason_id, comment=command.comment, origin=origin,
        allow_no_differences=True,
    )
    if command.kar_id is not None:
        tag_service.apply_places(
            db, document, tags, tag_service.KAR, to_kar_id=command.kar_id, reader=command.reader, counted=False
        )
        known = tag_service.tags_at(db, kar_id=command.kar_id, product_ids=counted)
    else:
        tag_service.apply_places(db, document, tags, tag_service.FREE, reader=command.reader, counted=False)
        known = tag_service.tags_at(db, free=True, product_ids=counted)
    # Known here but not read: we no longer know where those pieces are.
    read_ids = {tag.id for tag in tags}
    unread = [tag for tag in known if tag.id not in read_ids]
    tag_service.apply_places(db, document, unread, None, counted=False)
    return document


def _kar_dispatch(
    db: Session,
    user: User,
    command: TagBookingCommand,
    tags: list[RfidTag],
    tag_counts: dict[int, int],
    manual: dict[int, int],
    origin: BookingOrigin,
) -> tuple[StockMasterDocument, list[StockMasterDocument]]:
    """Kar vertrekt, "correct, then book" (see the module header)."""
    kar_id = _required_kar(command.kar_id)
    kar = stock_service.get_kar(db, kar_id)
    stock_service.ensure_kar_in_warehouse(db, kar)
    expected = stock_service.kar_contents(db, kar_id)

    # What the operator decided for the missing pieces, per product.
    declared: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for line in command.missing:
        if line.quantity <= 0:
            raise StockError("invalid_quantity")
        if line.destination not in (tag_service.FREE, tag_service.WRITTEN_OFF):
            raise StockError("invalid_destination")
        declared[line.product_id][line.destination] += line.quantity

    to_free: list[BookingLine] = []
    written_off: list[BookingLine] = []
    extra: list[BookingLine] = []
    for product_id in sorted(set(expected) | set(tag_counts) | set(manual) | set(declared)):
        present = tag_counts.get(product_id, 0) + manual.get(product_id, 0)
        shortfall = expected.get(product_id, 0) - present
        decided = sum(declared[product_id].values()) if product_id in declared else 0
        name = _product_name(db, product_id)
        if shortfall > 0:
            if decided < shortfall:
                raise StockError("missing_unresolved", name, shortfall)
            if decided > shortfall:
                raise StockError("missing_too_many", name)
            if declared[product_id][tag_service.FREE]:
                to_free.append(BookingLine(product_id, declared[product_id][tag_service.FREE]))
            if declared[product_id][tag_service.WRITTEN_OFF]:
                written_off.append(BookingLine(product_id, declared[product_id][tag_service.WRITTEN_OFF]))
        else:
            if decided:
                raise StockError("missing_too_many", name)
            if shortfall < 0:
                extra.append(BookingLine(product_id, -shortfall))

    # Before anything moves: the tags last known in the kar that weren't read.
    read_ids = {tag.id for tag in tags}
    unread = [tag for tag in tag_service.tags_at(db, kar_id=kar_id) if tag.id not in read_ids]

    result = stock_service.dispatch_kar_corrected(
        db, user, command.season, kar_id,
        to_free=to_free, written_off=written_off, extra=extra, reason_id=command.reason_id,
        team_id=command.team_id, festival_id=command.festival_id,
        reference=command.reference, comment=command.comment, origin=origin,
    )
    trip = stock_service.open_trip_of(db, kar_id)
    tag_service.apply_places(
        db, result.dispatch, tags, tag_service.OUT, to_kar_id=kar_id, to_trip_id=trip.id if trip else None,
        reader=command.reader,
    )

    # The unread tags follow the missing pieces of their product: written off
    # first, then back to free stock; any left over become unknown.
    for product_id in {tag.assigned_product_id for tag in unread}:
        product_tags = _tags_of(unread, product_id)
        off = declared[product_id][tag_service.WRITTEN_OFF] if product_id in declared else 0
        free = declared[product_id][tag_service.FREE] if product_id in declared else 0
        if result.written_off is not None and off:
            tag_service.apply_places(db, result.written_off, product_tags[:off], tag_service.WRITTEN_OFF)
        product_tags = product_tags[off:]
        if result.unloaded is not None and free:
            tag_service.apply_places(db, result.unloaded, product_tags[:free], tag_service.FREE)
        product_tags = product_tags[free:]
        tag_service.apply_places(db, result.dispatch, product_tags, None, counted=False)
    return result.dispatch, result.corrections


def _product_name(db: Session, product_id: int) -> str:
    """A product's name for an error."""
    product = db.get(Product, product_id)
    if product is None:
        raise StockError("product_not_found", product_id, status_code=404)
    return product.name
