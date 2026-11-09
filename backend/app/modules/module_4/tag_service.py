# StockMaster's per-piece RFID trace, used by the RWCrew Pi app: what read
# EPCs are (resolve), "Tags koppelen" (link tags to a product), the LAST KNOWN
# place of every product tag, and its history. The ONLY writer of the tag
# place columns (Tagscan_rfid_tag.stock_*) and of StockMaster_movement_tag.
#
# One product tag = one piece of its product (Tagscan_rfid_tag.
# assigned_product_id). Stock itself stays counted per product in
# stock_service.py; a Pi booking counts its tags into the booking's
# quantities (tag_booking.py) and then moves the tags here, in the same
# transaction.
#
# "Last known place" (decided with the user): only Pi bookings move tags.
# Web bookings move quantities without knowing which tags, so a place can be
# out of date. That's why the rules below only refuse CLEAR contradictions
# (booking in a tag that is known to be in a kar, unloading a tag that is in
# another kar...), and why an unknown place (NULL — every tag before its first
# Pi booking) is accepted everywhere. A count (Telling) on the Pi is the
# authority that puts places right again.
#
# Nothing here commits: the router does.

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timezone import belgian_today
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.stockmaster_kar_trip import StockMasterKarTrip
from app.db.models.stockmaster_movement import StockMasterMovement
from app.db.models.stockmaster_movement_tag import StockMasterMovementTag
from app.db.models.user import User
from app.modules.module_1.tag_trace import Reader, clean_epcs, touch
from app.modules.module_4.stock_service import StockError

# What a read EPC turned out to be (ResolvedStockTag.state):
UNKNOWN = "unknown"  # never registered in TagScan's register
ATELIER = "atelier"  # an Atelier clothing piece (module-5), not ours
KAR_TAG = "kar_tag"  # the tag mounted on a kar: tells which kar this is
UNASSIGNED = "unassigned"  # registered, but linked to nothing yet
INACTIVE = "inactive"  # a product tag that is lost/damaged/retired
PRODUCT = "product"  # one piece of a product: can be booked

# A product tag's place (RfidTag.stock_place; None = unknown).
FREE = "free"
KAR = "kar"
OUT = "out"
WRITTEN_OFF = "written_off"
PLACES = (FREE, KAR, OUT, WRITTEN_OFF)

# The most EPCs one call may send: a full kar holds a lot of pieces.
MAX_EPCS = 1000

# Bookings by Pi action (the same keys as stock_service's doc types).
BOOK_IN = "book_in"
KAR_LOAD = "kar_load"
KAR_UNLOAD = "kar_unload"
BOOK_OUT = "book_out"
KAR_DISPATCH = "kar_dispatch"
KAR_RETURN = "kar_return"
COUNT = "count"


def cleaned(epcs: list[str]) -> list[str]:
    """The read EPCs trimmed, each once, at most MAX_EPCS."""
    return clean_epcs(epcs, MAX_EPCS, lambda limit: StockError("too_many_tags", limit))


# --- Where a tag really is -------------------------------------------------


@dataclass(frozen=True)
class Place:
    """A tag's place as far as we can still believe it. A kar that left
    since (a web "Kar vertrekt") takes its tags along on its trip; a trip
    that is over (web "Kar terug") leaves its tags unknown — they came back
    into the kar or to free stock, we can't tell which."""

    place: str | None
    kar_id: int | None = None
    trip_id: int | None = None


def _open_trips_by_kar(db: Session, kar_ids: Iterable[int]) -> dict[int, StockMasterKarTrip]:
    """The open trip of each of these kars that is out right now."""
    ids = {kar_id for kar_id in kar_ids if kar_id is not None}
    if not ids:
        return {}
    trips = db.scalars(
        select(StockMasterKarTrip).where(
            StockMasterKarTrip.kar_id.in_(ids), StockMasterKarTrip.return_document_id.is_(None)
        )
    ).all()
    return {trip.kar_id: trip for trip in trips}


def _open_trip_ids(db: Session, trip_ids: Iterable[int]) -> set[int]:
    """Which of these trips are still open (the kar is still out)."""
    ids = {trip_id for trip_id in trip_ids if trip_id is not None}
    if not ids:
        return set()
    return set(
        db.scalars(
            select(StockMasterKarTrip.id).where(
                StockMasterKarTrip.id.in_(ids), StockMasterKarTrip.return_document_id.is_(None)
            )
        ).all()
    )


class PlaceBook:
    """Works out the believable place of many tags with a few queries."""

    def __init__(self, db: Session, tags: Iterable[RfidTag]) -> None:
        tags = list(tags)
        self._out_kars = _open_trips_by_kar(db, (tag.stock_kar_id for tag in tags if tag.stock_place == KAR))
        self._open_trips = _open_trip_ids(db, (tag.stock_trip_id for tag in tags if tag.stock_place == OUT))

    def of(self, tag: RfidTag) -> Place:
        """The tag's place, corrected for what happened on the web since."""
        if tag.stock_place == KAR:
            trip = self._out_kars.get(tag.stock_kar_id)
            if trip is not None:
                return Place(OUT, tag.stock_kar_id, trip.id)
            return Place(KAR, tag.stock_kar_id)
        if tag.stock_place == OUT:
            if tag.stock_trip_id in self._open_trips:
                return Place(OUT, tag.stock_kar_id, tag.stock_trip_id)
            return Place(None)
        if tag.stock_place in (FREE, WRITTEN_OFF):
            return Place(tag.stock_place)
        return Place(None)


def _kar_numbers(db: Session, kar_ids: Iterable[int | None]) -> dict[int, str]:
    """{kar id: kar number} for the given kars."""
    ids = {kar_id for kar_id in kar_ids if kar_id is not None}
    if not ids:
        return {}
    return dict(db.execute(select(KarTrackerKar.id, KarTrackerKar.kar_nummer).where(KarTrackerKar.id.in_(ids))).all())


def _tags_by_epc(db: Session, epcs: list[str]) -> dict[str, RfidTag]:
    """The registered tags of these EPCs (in chunks: a kar can mean 1000)."""
    result: dict[str, RfidTag] = {}
    for start in range(0, len(epcs), 500):
        chunk = epcs[start : start + 500]
        for tag in db.scalars(select(RfidTag).where(RfidTag.epc_uid.in_(chunk))).all():
            result[tag.epc_uid] = tag
    return result


# --- Resolve ---------------------------------------------------------------


@dataclass
class ResolvedStockTag:
    """One read EPC: what it is and, for a product piece, where it is."""

    epc: str
    state: str
    rfid_tag_id: int | None = None
    product_id: int | None = None
    product_name: str | None = None
    is_blocked: bool = False
    stock_return_to: str | None = None
    # KAR_TAG: the kar this tag is mounted on.
    kar_id: int | None = None
    kar_nummer: str | None = None
    kar_is_out: bool = False
    # PRODUCT: the believable place (see Place), with the kar's number.
    place: str | None = None
    place_kar_id: int | None = None
    place_kar_nummer: str | None = None
    place_trip_id: int | None = None
    # ATELIER: which clothing piece it is (shown on the Pi).
    assigned_to: str | None = None


def resolve(db: Session, epcs: list[str]) -> list[ResolvedStockTag]:
    """What each read EPC is, in reading order (see the states above)."""
    epcs = cleaned(epcs)
    tags = _tags_by_epc(db, epcs)
    products = {
        product.id: product
        for product in db.scalars(
            select(Product).where(Product.id.in_({tag.assigned_product_id for tag in tags.values() if tag.assigned_product_id}))
        ).all()
    } if tags else {}
    places = PlaceBook(db, tags.values())
    kar_tag_ids = [tag.kar_id for tag in tags.values() if tag.kar_id]
    out_kars = _open_trips_by_kar(db, kar_tag_ids)
    kar_numbers = _kar_numbers(db, [*kar_tag_ids, *(tag.stock_kar_id for tag in tags.values())])

    result = []
    for epc in epcs:
        tag = tags.get(epc)
        if tag is None:
            result.append(ResolvedStockTag(epc=epc, state=UNKNOWN))
            continue
        if tag.atelier_article_size_id is not None:
            result.append(
                ResolvedStockTag(epc=epc, state=ATELIER, rfid_tag_id=tag.id, assigned_to=_atelier_label(db, tag))
            )
            continue
        if tag.assigned_product_id is None and tag.kar_id is not None:
            result.append(
                ResolvedStockTag(
                    epc=epc,
                    state=KAR_TAG,
                    rfid_tag_id=tag.id,
                    kar_id=tag.kar_id,
                    kar_nummer=kar_numbers.get(tag.kar_id),
                    kar_is_out=tag.kar_id in out_kars,
                )
            )
            continue
        if tag.assigned_product_id is None:
            result.append(ResolvedStockTag(epc=epc, state=UNASSIGNED, rfid_tag_id=tag.id))
            continue
        product = products.get(tag.assigned_product_id)
        place = places.of(tag)
        result.append(
            ResolvedStockTag(
                epc=epc,
                state=PRODUCT if tag.status == "active" else INACTIVE,
                rfid_tag_id=tag.id,
                product_id=tag.assigned_product_id,
                product_name=product.name if product else None,
                is_blocked=bool(product and product.is_blocked),
                stock_return_to=product.stock_return_to if product else None,
                place=place.place,
                place_kar_id=place.kar_id,
                place_kar_nummer=kar_numbers.get(place.kar_id) if place.kar_id else None,
                place_trip_id=place.trip_id,
            )
        )
    return result


def _atelier_label(db: Session, tag: RfidTag) -> str | None:
    """"T-shirt" — the Atelier article an Atelier piece belongs to."""
    article_size = db.get(AtelierArticleSize, tag.atelier_article_size_id)
    article = db.get(AtelierArticle, article_size.article_id) if article_size else None
    return article.name if article else None


def tagged_counts(db: Session) -> dict[int, int]:
    """Per product: how many pieces carry an active RFID tag."""
    return dict(
        db.execute(
            select(RfidTag.assigned_product_id, func.count())
            .where(RfidTag.assigned_product_id.is_not(None), RfidTag.status == "active")
            .group_by(RfidTag.assigned_product_id)
        ).all()
    )


def tags_at(db: Session, *, kar_id: int | None = None, free: bool = False, product_ids: Iterable[int] | None = None) -> list[RfidTag]:
    """The active product tags last known in one place: a kar (standing in
    the warehouse) or free stock — the pieces a Pi screen expects to read."""
    query = select(RfidTag).where(RfidTag.assigned_product_id.is_not(None), RfidTag.status == "active")
    if kar_id is not None:
        query = query.where(RfidTag.stock_place == KAR, RfidTag.stock_kar_id == kar_id)
    elif free:
        query = query.where(RfidTag.stock_place == FREE)
    else:
        return []
    if product_ids is not None:
        query = query.where(RfidTag.assigned_product_id.in_(set(product_ids)))
    return list(db.scalars(query.order_by(RfidTag.epc_uid)).all())


# --- Tags koppelen ---------------------------------------------------------


def assign(
    db: Session,
    user: User,
    epcs: list[str],
    product_id: int,
    replace: bool = False,
    reader: Reader | None = None,
) -> list[RfidTag]:
    """Tags koppelen: the read tags become pieces of this product. A new EPC
    is registered in TagScan's register; a known tag may not be an Atelier
    piece or a kar's tag. A tag already linked to another product only
    changes with `replace` (the Pi asks) — and then its place is forgotten,
    since it was counted as the other product."""
    epcs = cleaned(epcs)
    if not epcs:
        raise StockError("no_tags")
    product = db.get(Product, product_id)
    if product is None:
        raise StockError("product_not_found", product_id, status_code=404)
    if product.is_blocked:
        raise StockError("product_blocked", product.name)

    existing = _tags_by_epc(db, epcs)
    kar_numbers = _kar_numbers(db, (tag.kar_id for tag in existing.values()))
    other_products = {
        row_id: name
        for row_id, name in db.execute(
            select(Product.id, Product.name).where(
                Product.id.in_({tag.assigned_product_id for tag in existing.values() if tag.assigned_product_id})
            )
        ).all()
    } if existing else {}

    note = f"Gekoppeld via RWCrew Pi door {user.display_name}"
    tags = []
    for epc in epcs:
        tag = existing.get(epc)
        if tag is None:
            # A new tag in TagScan's register, with who linked it and where.
            tag = RfidTag(
                epc_uid=epc,
                status="active",
                assigned_product_id=product.id,
                date_assigned=belgian_today(),
                notes_1=note,
            )
            touch(tag, reader)
            db.add(tag)
            tags.append(tag)
            continue
        if tag.atelier_article_size_id is not None:
            raise StockError("tag_is_atelier_piece", epc)
        if tag.kar_id is not None:
            raise StockError("tag_is_kar", epc, kar_numbers.get(tag.kar_id, tag.kar_id))
        if tag.assigned_product_id not in (None, product.id):
            if not replace:
                raise StockError("tag_other_product", epc, other_products.get(tag.assigned_product_id, ""))
            # Counted as another product until now: its place means nothing any more.
            forget_place(tag)
        tag.assigned_product_id = product.id
        tag.status = "active"
        tag.date_assigned = belgian_today()
        if not tag.notes_1:
            tag.notes_1 = note
        touch(tag, reader)
        tags.append(tag)
    # A product that gets tags is followed by RFID from now on.
    if not product.is_tag_managed:
        product.is_tag_managed = True
    db.flush()
    return tags


def forget_place(tag: RfidTag) -> None:
    """Make a tag's place unknown without a booking (its product changed in
    Tags koppelen or in Tagbeheer)."""
    tag.stock_place = None
    tag.stock_kar_id = None
    tag.stock_trip_id = None
    tag.stock_document_id = None
    tag.stock_place_at = None


# --- Booking with tags -----------------------------------------------------


def tags_for_booking(db: Session, epcs: list[str]) -> list[RfidTag]:
    """The product tags of a Pi booking, in reading order. Every tag must be
    an active piece of a product; a kar's own tag is skipped (it only tells
    the Pi which kar it is), anything else refuses the whole booking."""
    epcs = cleaned(epcs)
    tags = _tags_by_epc(db, epcs)
    result = []
    for epc in epcs:
        tag = tags.get(epc)
        if tag is None:
            raise StockError("tag_unknown", epc)
        if tag.atelier_article_size_id is not None:
            raise StockError("tag_is_atelier_piece", epc)
        if tag.assigned_product_id is None:
            if tag.kar_id is not None:
                continue
            raise StockError("tag_no_product", epc)
        if tag.status != "active":
            raise StockError("tag_inactive", epc)
        result.append(tag)
    return result


def count_by_product(tags: Iterable[RfidTag]) -> dict[int, int]:
    """{product id: pieces} of a list of product tags."""
    counts: dict[int, int] = defaultdict(int)
    for tag in tags:
        counts[tag.assigned_product_id] += 1
    return dict(counts)


def check_places(db: Session, action: str, tags: list[RfidTag], *, kar_id: int | None = None) -> None:
    """Refuse a Pi booking when a tag is clearly somewhere else than the
    booking says (see the table in docs and the module header). Unknown
    places are always fine; a count accepts everything (it is the authority)."""
    if action == COUNT or not tags:
        return
    places = PlaceBook(db, tags)
    numbers = _kar_numbers(db, [tag.stock_kar_id for tag in tags])
    kar_trip = _open_trips_by_kar(db, [kar_id]).get(kar_id) if kar_id is not None else None

    for tag in tags:
        place = places.of(tag)
        epc = tag.epc_uid
        kar_label = numbers.get(place.kar_id, "") if place.kar_id else ""
        here = place.kar_id is not None and place.kar_id == kar_id
        if place.place is None:
            continue

        if action == BOOK_IN:
            if place.place == FREE:
                raise StockError("tag_already_in_stock", epc)
            if place.place == KAR:
                raise StockError("tag_in_kar", epc, kar_label)
            if place.place == OUT:
                raise StockError("tag_on_trip", epc, kar_label)
            continue  # written off: it turned up again

        if place.place == WRITTEN_OFF:
            # A written-off piece only comes back through Inboeken or Kar terug.
            if action == KAR_RETURN:
                continue
            raise StockError("tag_written_off", epc)

        if action == KAR_LOAD:
            if place.place == KAR:
                raise StockError("tag_already_in_kar" if here else "tag_in_other_kar", epc, kar_label)
            if place.place == OUT:
                if kar_trip is not None and place.trip_id == kar_trip.id:
                    raise StockError("tag_already_in_kar", epc, kar_label)
                raise StockError("tag_on_trip", epc, kar_label)
            continue  # free

        if action in (KAR_UNLOAD, KAR_DISPATCH) or (action == BOOK_OUT and kar_id is not None):
            # Out of kar K: the tag is in K, or free (a web Kar laden since).
            if place.place == KAR and not here:
                raise StockError("tag_in_other_kar", epc, kar_label)
            if place.place == OUT:
                raise StockError("tag_on_trip", epc, kar_label)
            continue

        if action == BOOK_OUT:
            # Out of free stock.
            if place.place == KAR:
                raise StockError("tag_in_kar", epc, kar_label)
            if place.place == OUT:
                raise StockError("tag_on_trip", epc, kar_label)
            continue

        if action == KAR_RETURN:
            if place.place == OUT and not here:
                raise StockError("tag_on_other_trip", epc, kar_label)
            if place.place == KAR and not here:
                raise StockError("tag_in_other_kar", epc, kar_label)
            continue


def _movement_index(db: Session, document: StockMasterDocument) -> dict[tuple[int, str], int]:
    """{(product id, to bucket): movement id} of one booking's ledger lines."""
    index: dict[tuple[int, str], int] = {}
    for movement in db.scalars(select(StockMasterMovement).where(StockMasterMovement.document_id == document.id)).all():
        index.setdefault((movement.product_id, movement.to_bucket), movement.id)
        index.setdefault((movement.product_id, "*"), movement.id)
    return index


# Which ledger bucket a tag place lands in (to match a tag to its movement).
_BUCKET_OF_PLACE = {FREE: "free", KAR: "kar", OUT: "external", WRITTEN_OFF: "external"}


def apply_places(
    db: Session,
    document: StockMasterDocument,
    tags: Iterable[RfidTag],
    to_place: str | None,
    *,
    to_kar_id: int | None = None,
    to_trip_id: int | None = None,
    reader: Reader | None = None,
    counted: bool = True,
) -> None:
    """Move tags to their new place as part of this booking: one trace row
    per tag (linked to the product's ledger line when `counted`), and the
    tag's place columns. `to_place` None = the place becomes unknown."""
    index = _movement_index(db, document) if counted else {}
    now = datetime.now(timezone.utc)
    for tag in tags:
        movement_id = None
        if counted:
            movement_id = index.get((tag.assigned_product_id, _BUCKET_OF_PLACE.get(to_place, "*"))) or index.get(
                (tag.assigned_product_id, "*")
            )
        db.add(
            StockMasterMovementTag(
                document_id=document.id,
                movement_id=movement_id,
                rfid_tag_id=tag.id,
                epc=tag.epc_uid,
                product_id=tag.assigned_product_id,
                from_place=tag.stock_place,
                from_kar_id=tag.stock_kar_id,
                from_trip_id=tag.stock_trip_id,
                from_document_id=tag.stock_document_id,
                to_place=to_place,
                to_kar_id=to_kar_id if to_place in (KAR, OUT) else None,
                to_trip_id=to_trip_id if to_place == OUT else None,
            )
        )
        tag.stock_place = to_place
        tag.stock_kar_id = to_kar_id if to_place in (KAR, OUT) else None
        tag.stock_trip_id = to_trip_id if to_place == OUT else None
        tag.stock_document_id = document.id if to_place is not None else None
        tag.stock_place_at = now
        touch(tag, reader)
    db.flush()


def reverse_places(db: Session, original: StockMasterDocument, reversal: StockMasterDocument) -> None:
    """"Ongedaan maken" of a booking: every tag it moved goes back to where
    it was — but only while that booking is still the tag's latest (a tag
    the Pi moved again since stays where it was last seen)."""
    links = db.scalars(
        select(StockMasterMovementTag)
        .where(StockMasterMovementTag.document_id == original.id)
        .order_by(StockMasterMovementTag.id)
    ).all()
    tag_ids = {link.rfid_tag_id for link in links if link.rfid_tag_id is not None}
    if not tag_ids:
        return
    tags = {tag.id: tag for tag in db.scalars(select(RfidTag).where(RfidTag.id.in_(tag_ids))).all()}
    # Trips removed by the reversal itself (an undone "Kar vertrekt") can't be pointed at.
    existing_trips = set(
        db.scalars(
            select(StockMasterKarTrip.id).where(
                StockMasterKarTrip.id.in_({link.from_trip_id for link in links if link.from_trip_id})
            )
        ).all()
    ) if any(link.from_trip_id for link in links) else set()
    now = datetime.now(timezone.utc)
    for link in links:
        tag = tags.get(link.rfid_tag_id)
        if tag is None:
            continue
        # Still where this booking left it? (A place it made unknown has no
        # booking on the tag: then the tag must still be unknown.)
        unchanged = tag.stock_document_id == original.id or (
            link.to_place is None and tag.stock_place is None and tag.stock_document_id is None
        )
        if not unchanged:
            continue
        from_trip = link.from_trip_id if link.from_trip_id in existing_trips else None
        db.add(
            StockMasterMovementTag(
                document_id=reversal.id,
                rfid_tag_id=tag.id,
                epc=tag.epc_uid,
                product_id=tag.assigned_product_id,
                from_place=tag.stock_place,
                from_kar_id=tag.stock_kar_id,
                from_trip_id=tag.stock_trip_id,
                from_document_id=tag.stock_document_id,
                to_place=link.from_place,
                to_kar_id=link.from_kar_id,
                to_trip_id=from_trip,
            )
        )
        tag.stock_place = link.from_place
        tag.stock_kar_id = link.from_kar_id
        tag.stock_trip_id = from_trip
        # Handed back to the booking that had put it there, so undoing that
        # one next still moves this tag.
        tag.stock_document_id = link.from_document_id if link.from_place is not None else None
        tag.stock_place_at = now
    db.flush()


# --- Labels and history ----------------------------------------------------


def place_kar_numbers(db: Session, tags: Iterable[RfidTag]) -> dict[int, str]:
    """{kar id: number} of the kars these tags' places point at (Tagbeheer)."""
    return _kar_numbers(db, (tag.stock_kar_id for tag in tags))


@dataclass
class StockTagEvent:
    """One Pi booking that moved the tag."""

    document_id: int
    doc_number: str
    doc_type: str
    status: str
    created_at: datetime
    created_by_name: str | None
    source: str | None
    from_place: str | None
    from_kar_nummer: str | None
    to_place: str | None
    to_kar_nummer: str | None
    counted: bool


@dataclass
class StockTagHistory:
    """A product tag as TagScan's register knows it now, and every Pi
    booking that moved it (newest first)."""

    epc: str
    rfid_tag_id: int | None = None
    status: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    place: str | None = None
    place_kar_nummer: str | None = None
    place_at: datetime | None = None
    last_read_at: datetime | None = None
    last_reader_id: str | None = None
    last_location: str | None = None
    events: list[StockTagEvent] = field(default_factory=list)


def history(db: Session, epc: str) -> StockTagHistory:
    """Tag-historiek of one EPC."""
    epc = epc.strip()
    if not epc:
        raise StockError("no_tags")
    result = StockTagHistory(epc=epc)
    tag = db.scalar(select(RfidTag).where(RfidTag.epc_uid == epc))
    if tag is not None:
        product = db.get(Product, tag.assigned_product_id) if tag.assigned_product_id else None
        place = PlaceBook(db, [tag]).of(tag)
        result.rfid_tag_id = tag.id
        result.status = tag.status
        result.product_id = tag.assigned_product_id
        result.product_name = product.name if product else None
        result.place = place.place
        result.place_kar_nummer = _kar_numbers(db, [place.kar_id]).get(place.kar_id) if place.kar_id else None
        result.place_at = tag.stock_place_at
        result.last_read_at = tag.last_read_at
        result.last_reader_id = tag.last_reader_id
        result.last_location = tag.last_location

    links = db.scalars(
        select(StockMasterMovementTag)
        .where(StockMasterMovementTag.epc == epc)
        .order_by(StockMasterMovementTag.id.desc())
    ).all()
    documents = {
        document.id: document
        for document in db.scalars(
            select(StockMasterDocument).where(StockMasterDocument.id.in_({link.document_id for link in links}))
        ).all()
    } if links else {}
    numbers = _kar_numbers(db, [*(link.from_kar_id for link in links), *(link.to_kar_id for link in links)])
    for link in links:
        document = documents[link.document_id]
        result.events.append(
            StockTagEvent(
                document_id=document.id,
                doc_number=document.doc_number,
                doc_type=document.doc_type,
                status=document.status,
                created_at=document.created_at,
                created_by_name=document.created_by_name,
                source=document.source,
                from_place=link.from_place,
                from_kar_nummer=numbers.get(link.from_kar_id) if link.from_kar_id else None,
                to_place=link.to_place,
                to_kar_nummer=numbers.get(link.to_kar_id) if link.to_kar_id else None,
                counted=link.movement_id is not None,
            )
        )
    return result
