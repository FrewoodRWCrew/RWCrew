# Atelier's stock engine (block 3): the ONLY place that changes Atelier stock
# — the same pattern as StockMaster's module_4/stock_service.py.
#
# Stock is counted per article size (Atelier_article_size) and status:
#   - "available"   clean, in the store, ready to hand out
#   - "to_wash"     came back from a shift, waiting to be washed
#   - "handed_out"  at a worker during a shift (used from block 4 on)
# Outside the store (a delivery, a write-off) is NULL.
#
# Every booking is one Atelier_stock_document with one Atelier_stock_movement
# per article size, and Atelier_stock_balance is updated in the same
# transaction after locking its row (SELECT ... FOR UPDATE), so stock never
# goes negative. Nothing is edited or deleted: "Ongedaan maken" books the
# exact opposite in a "reversal" document. These functions never commit:
# the caller (the router, later the counter desk of block 4) does.

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import belgian_now
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_size import AtelierSize
from app.db.models.atelier_stock_balance import AtelierStockBalance
from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.atelier_stock_movement import AtelierStockMovement
from app.db.models.user import User

# The stock statuses (None = outside the store).
AVAILABLE = "available"
TO_WASH = "to_wash"
HANDED_OUT = "handed_out"
STATUSES = (AVAILABLE, TO_WASH, HANDED_OUT)

# The booking types (the desk's hand_out / return below).
RECEIPT = "receipt"
WASHED = "washed"
WRITE_OFF = "write_off"
COUNT = "count"
REVERSAL = "reversal"
# The counter desk (block 4): a pick-up and a return.
HAND_OUT = "hand_out"
RETURN = "return"
DOC_TYPES = (RECEIPT, WASHED, WRITE_OFF, COUNT, REVERSAL, HAND_OUT, RETURN)
# Bookings of the counter desk are linked to its hand-out lines, so they can
# only be undone there ("Uitgifte annuleren"), never on Boekingen.
DESK_TYPES = (HAND_OUT, RETURN)

# Why pieces are written off; "other" needs a note.
WRITE_OFF_REASONS = ("damaged", "lost", "not_returned", "other")

POSTED = "posted"
REVERSED = "reversed"


class StockError(Exception):
    """A booking that breaks a stock rule. `code` is a stable key the
    frontend translates (atelier.stock.errors.<code>); `params` fill in the
    details (article size, quantity present ...)."""

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
class StockLine:
    """One line of a receipt, wash or write-off: N pieces of an article
    size; `from_status` only on a write-off (available or to_wash)."""

    article_size_id: int
    quantity: int
    from_status: str | None = None


@dataclass
class CountLine:
    """One counted quantity: an article size in one status."""

    article_size_id: int
    status: str
    counted: int


@dataclass
class _Move:
    """One ledger line to post."""

    article_size_id: int
    quantity: int
    from_status: str | None
    to_status: str | None


# --- Lookups -------------------------------------------------------------------


def get_article_size(db: Session, article_size_id: int) -> AtelierArticleSize:
    """Load an article size, or refuse the booking."""
    row = db.get(AtelierArticleSize, article_size_id)
    if row is None:
        raise StockError("article_size_not_found", article_size_id, status_code=404)
    return row


def article_size_label(db: Session, article_size_id: int) -> str:
    """"T-shirt crew zwart · M (men)" — for error messages and PDFs."""
    row = get_article_size(db, article_size_id)
    article = db.get(AtelierArticle, row.article_id)
    size = db.get(AtelierSize, row.size_id)
    return f"{article.name} · {size.name} ({size.fit})"


def balance_quantity(db: Session, article_size_id: int, status: str) -> int:
    """The pieces of an article size in one status right now."""
    balance = db.scalar(
        select(AtelierStockBalance).where(
            AtelierStockBalance.article_size_id == article_size_id, AtelierStockBalance.status == status
        )
    )
    return balance.quantity if balance else 0


def all_balances(db: Session) -> dict[tuple[int, str], int]:
    """Every balance: (article size id, status) → pieces."""
    return {
        (row.article_size_id, row.status): row.quantity for row in db.scalars(select(AtelierStockBalance)).all()
    }


# --- Posting ---------------------------------------------------------------------


def _change_balance(db: Session, article_size_id: int, status: str, delta: int) -> None:
    """Add (or with a negative delta, take) pieces in one status, after
    locking that row. Refuses to go below zero; an emptied row is removed."""
    balance = db.scalar(
        select(AtelierStockBalance)
        .where(AtelierStockBalance.article_size_id == article_size_id, AtelierStockBalance.status == status)
        .with_for_update()
    )
    present = balance.quantity if balance else 0
    new_quantity = present + delta
    if new_quantity < 0:
        raise StockError("insufficient_stock", article_size_label(db, article_size_id), present, status)

    if balance is None:
        db.add(AtelierStockBalance(article_size_id=article_size_id, status=status, quantity=new_quantity))
    elif new_quantity == 0:
        db.delete(balance)
    else:
        balance.quantity = new_quantity
        balance.updated_at = datetime.now(timezone.utc)
    # Write right away, so a later line in the same booking sees this one.
    db.flush()


def _new_document(db: Session, user: User, doc_type: str, **fields: object) -> AtelierStockDocument:
    """The booking's header under the session user, with its readable
    number AT-<Belgian year>-<id>."""
    document = AtelierStockDocument(
        doc_number=f"TMP-{datetime.now(timezone.utc).timestamp()}",
        doc_type=doc_type,
        status=POSTED,
        created_by=user.id,
        created_by_name=user.display_name,
        **fields,
    )
    db.add(document)
    db.flush()
    document.doc_number = f"AT-{belgian_now().year}-{document.id:05d}"
    db.flush()
    return document


def _post_moves(db: Session, document: AtelierStockDocument, moves: Iterable[_Move]) -> None:
    """Write the ledger lines and update the balances, in article-size
    order so two bookings always lock rows in the same order."""
    for move in sorted(moves, key=lambda item: (item.article_size_id, item.from_status or "", item.to_status or "")):
        if move.quantity <= 0:
            raise StockError("invalid_quantity")
        get_article_size(db, move.article_size_id)
        # Take from the source first, then add at the destination.
        if move.from_status is not None:
            _change_balance(db, move.article_size_id, move.from_status, -move.quantity)
        if move.to_status is not None:
            _change_balance(db, move.article_size_id, move.to_status, move.quantity)
        db.add(
            AtelierStockMovement(
                document_id=document.id,
                article_size_id=move.article_size_id,
                from_status=move.from_status,
                to_status=move.to_status,
                quantity=move.quantity,
            )
        )
    db.flush()


def _merge(lines: Iterable[StockLine]) -> list[StockLine]:
    """Add up lines for the same article size (and source status), so a
    size typed twice becomes one ledger line."""
    merged: dict[tuple[int, str | None], StockLine] = {}
    for line in lines:
        if line.quantity <= 0:
            raise StockError("invalid_quantity")
        key = (line.article_size_id, line.from_status)
        if key in merged:
            merged[key].quantity += line.quantity
        else:
            merged[key] = StockLine(line.article_size_id, line.quantity, line.from_status)
    if not merged:
        raise StockError("no_lines")
    return list(merged.values())


def _clean(text: str | None) -> str | None:
    """Trimmed text, None when empty."""
    return (text or "").strip() or None


# --- Bookings ---------------------------------------------------------------------


def receive(
    db: Session, user: User, lines: Iterable[StockLine], *, reference: str | None = None, note: str | None = None
) -> AtelierStockDocument:
    """Ontvangst: new pieces come into the store as available. Only active
    article sizes of active articles can be received."""
    merged = _merge(lines)
    for line in merged:
        row = get_article_size(db, line.article_size_id)
        article = db.get(AtelierArticle, row.article_id)
        if not row.active or not article.active:
            raise StockError("article_size_inactive", article_size_label(db, line.article_size_id))
    document = _new_document(db, user, RECEIPT, reference=_clean(reference), note=_clean(note))
    _post_moves(db, document, [_Move(line.article_size_id, line.quantity, None, AVAILABLE) for line in merged])
    return document


def wash(db: Session, user: User, lines: Iterable[StockLine], *, note: str | None = None) -> AtelierStockDocument:
    """Gewassen: pieces waiting to be washed become available again."""
    merged = _merge(lines)
    document = _new_document(db, user, WASHED, note=_clean(note))
    _post_moves(db, document, [_Move(line.article_size_id, line.quantity, TO_WASH, AVAILABLE) for line in merged])
    return document


def write_off(
    db: Session, user: User, lines: Iterable[StockLine], *, reason: str, note: str | None = None
) -> AtelierStockDocument:
    """Afboeken: pieces leave the store for good (damaged, lost, ...), taken
    from available or from to-wash. "other" needs a note."""
    if reason not in WRITE_OFF_REASONS:
        raise StockError("invalid_reason")
    if reason == "other" and not _clean(note):
        raise StockError("note_required")
    merged = _merge(lines)
    for line in merged:
        if line.from_status not in (AVAILABLE, TO_WASH):
            raise StockError("invalid_status")
    document = _new_document(db, user, WRITE_OFF, reason=reason, note=_clean(note))
    _post_moves(db, document, [_Move(line.article_size_id, line.quantity, line.from_status, None) for line in merged])
    return document


def count_stock(db: Session, user: User, lines: Iterable[CountLine], *, note: str | None = None) -> AtelierStockDocument:
    """Telling: compare the counted pieces (available and to-wash) with the
    booked ones and book only the differences. Refused when nothing differs."""
    moves: list[_Move] = []
    seen: set[tuple[int, str]] = set()
    for line in lines:
        if line.status not in (AVAILABLE, TO_WASH):
            raise StockError("invalid_status")
        if line.counted < 0:
            raise StockError("invalid_quantity")
        key = (line.article_size_id, line.status)
        if key in seen:
            raise StockError("duplicate_line")
        seen.add(key)
        get_article_size(db, line.article_size_id)
        difference = line.counted - balance_quantity(db, line.article_size_id, line.status)
        if difference > 0:
            moves.append(_Move(line.article_size_id, difference, None, line.status))
        elif difference < 0:
            moves.append(_Move(line.article_size_id, -difference, line.status, None))
    if not moves:
        raise StockError("no_differences")
    document = _new_document(db, user, COUNT, note=_clean(note))
    _post_moves(db, document, moves)
    return document


def hand_out(db: Session, user: User, article_size_ids: list[int], *, note: str | None = None) -> AtelierStockDocument:
    """A pick-up at the counter: one piece of each article size, available →
    handed out (refused when a size has no piece available)."""
    merged = _merge(StockLine(article_size_id, 1) for article_size_id in article_size_ids)
    document = _new_document(db, user, HAND_OUT, note=_clean(note))
    _post_moves(db, document, [_Move(line.article_size_id, line.quantity, AVAILABLE, HANDED_OUT) for line in merged])
    return document


def return_pieces(db: Session, user: User, article_size_ids: list[int], *, note: str | None = None) -> AtelierStockDocument:
    """A return at the counter: the pieces come back, handed out → to wash."""
    merged = _merge(StockLine(article_size_id, 1) for article_size_id in article_size_ids)
    document = _new_document(db, user, RETURN, note=_clean(note))
    _post_moves(db, document, [_Move(line.article_size_id, line.quantity, HANDED_OUT, TO_WASH) for line in merged])
    return document


def reverse_document(
    db: Session,
    user: User,
    document: AtelierStockDocument,
    *,
    note: str | None = None,
    from_desk: bool = False,
) -> AtelierStockDocument:
    """Ongedaan maken: book the exact opposite of a booking in a new
    "reversal" document (the original stays, marked "reversed"). Refused
    for a reversal, twice, or when the pieces are no longer there. A counter
    booking can only be undone by the desk itself (`from_desk`)."""
    if document.doc_type in DESK_TYPES and not from_desk:
        raise StockError("use_desk")
    if document.doc_type == REVERSAL:
        raise StockError("cannot_reverse_reversal")
    if document.status == REVERSED:
        raise StockError("already_reversed")
    original = db.scalars(select(AtelierStockMovement).where(AtelierStockMovement.document_id == document.id)).all()
    reversal = _new_document(db, user, REVERSAL, reversal_of_id=document.id, note=_clean(note))
    _post_moves(
        db,
        reversal,
        [_Move(move.article_size_id, move.quantity, move.to_status, move.from_status) for move in original],
    )
    document.status = REVERSED
    db.flush()
    return reversal
