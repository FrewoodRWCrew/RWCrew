# Carrying out the action a scanned CSV line asks for. Every line logged by
# a Tag Headerdata scan starts with process_status "new"; this module turns
# it into "loaded" (done) or "cancelled" (deliberately skipped), with a
# process_comment saying why, and keeps the line's file (TagHeaderData) in
# sync with an overall status of its own.
#
# Only actions listed in PROCESSABLE_ACTIONS are offered for processing —
# today just "Assignment" (create the tag when it isn't registered yet, with
# the product the user picked for that file — a tag must always have one).
# Adding a new action = write one more _process_<action>() handler and add
# it to that dict (extend ProcessContext if it needs extra user input);
# lines with any other action simply stay "new" until their own handler
# exists.
#
# Kept free of FastAPI/routing concerns (mirrors tag_import.py), so it's
# easy to unit test on its own.

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.timezone import belgian_today
from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.modules.module_1.tag_line_data import match_tag, preload_tag_lookup
from app.schemas.tagscan import LineProcessRowResult

PROCESS_NEW = "new"
PROCESS_LOADED = "loaded"
PROCESS_CANCELLED = "cancelled"

ACTION_ASSIGNMENT = "assignment"

COMMENT_NO_LINES = "No lines"


@dataclass
class ProcessContext:
    """What the user chose for one file's lines before processing them —
    today only the product every Assignment line of that file gets.
    """

    product: Product | None = None


def _process_assignment(db: Session, line: TagLineData, context: ProcessContext) -> tuple[str, str]:
    """"Assignment": register the line's EPC as a new RFID tag with the
    file's product, or give an already registered tag that product when it
    has none yet. A tag that already has a product is never changed.
    Returns (outcome, comment). A new tag is flushed straight away, so a
    second line with the same EPC later in the same batch finds it and
    reports "exists" instead of colliding on the unique epc_uid.
    """
    product = context.product
    if product is None:
        # A tag must always be assigned to a product.
        raise ValueError("A product is required")

    epc = line.epc.strip()
    existing = db.scalar(select(RfidTag).where(RfidTag.epc_uid == epc))

    if existing is None:
        db.add(
            RfidTag(
                epc_uid=epc,
                status="active",
                assigned_product_id=product.id,
                date_assigned=belgian_today(),
                manufacturer=line.manufacturer,
                batch_number=line.batch_number,
                last_reader_id=line.scanner_name or line.scanner,
                last_location=line.scanner_location,
            )
        )
        db.flush()
        return "created", f"Tag created for {product.name}"

    # Registered before without a product: fill it in.
    if existing.assigned_product_id is None:
        existing.assigned_product_id = product.id
        existing.date_assigned = belgian_today()
        db.flush()
        return "assigned", f"Product {product.name} assigned to existing tag"

    if existing.assigned_product_id == product.id:
        return "exists", f"Tag already assigned to {product.name}"

    # Assigned to another product: left alone, the comment says which one.
    other = db.get(Product, existing.assigned_product_id)
    other_name = other.name if other is not None else f"product #{existing.assigned_product_id}"
    return "exists", f"Tag already assigned to {other_name} — not changed"


# Lowercased CSV "Action" value → the handler that carries it out.
PROCESSABLE_ACTIONS: dict[str, Callable[[Session, TagLineData, ProcessContext], tuple[str, str]]] = {
    ACTION_ASSIGNMENT: _process_assignment,
}


def _pending_filter():
    """The WHERE clause for "waiting to be processed": still "new", and an
    action this module knows how to carry out (compared ignoring case and
    surrounding spaces, since it's free text typed on the scanner side).
    """
    return (
        TagLineData.process_status == PROCESS_NEW,
        func.lower(func.trim(TagLineData.action)).in_(list(PROCESSABLE_ACTIONS)),
    )


def count_pending_lines(db: Session) -> int:
    """How many lines are waiting — for the banner on every TagScan screen."""
    return db.scalar(select(func.count(TagLineData.id)).where(*_pending_filter())) or 0


def list_pending_lines(db: Session) -> list[tuple[TagLineData, str]]:
    """Every waiting line paired with its file's name, oldest file first
    and in CSV order, so they're processed in the order they arrived.
    """
    rows = db.execute(
        select(TagLineData, TagHeaderData.filename)
        .join(TagHeaderData, TagLineData.header_data_id == TagHeaderData.id)
        .where(*_pending_filter())
        .order_by(TagLineData.header_data_id.asc(), TagLineData.line_number.asc())
    ).all()
    return [(line, filename) for line, filename in rows]


def refresh_header_process_status(db: Session, header_id: int) -> None:
    """Recompute one file's overall status from its lines: "new" while any
    line is still waiting, "cancelled" when every line was cancelled,
    otherwise "loaded" — with a short summary of the counts as comment.
    Does not commit; the caller does.
    """
    header = db.get(TagHeaderData, header_id)
    if header is None:
        return

    # Sessions here don't autoflush: write pending line changes first, so
    # the count below sees them.
    db.flush()
    counts = dict(
        db.execute(
            select(TagLineData.process_status, func.count(TagLineData.id))
            .where(TagLineData.header_data_id == header_id)
            .group_by(TagLineData.process_status)
        ).all()
    )
    new_count = counts.get(PROCESS_NEW, 0)
    loaded_count = counts.get(PROCESS_LOADED, 0)
    cancelled_count = counts.get(PROCESS_CANCELLED, 0)

    if new_count + loaded_count + cancelled_count == 0:
        new_status, comment = PROCESS_LOADED, COMMENT_NO_LINES
    else:
        if new_count:
            new_status = PROCESS_NEW
        elif loaded_count == 0:
            new_status = PROCESS_CANCELLED
        else:
            new_status = PROCESS_LOADED
        # Only the non-zero parts, e.g. "12 loaded, 1 cancelled".
        parts = [
            f"{count} {label}"
            for count, label in (
                (loaded_count, PROCESS_LOADED),
                (cancelled_count, PROCESS_CANCELLED),
                (new_count, "waiting"),
            )
            if count
        ]
        comment = ", ".join(parts)

    if header.process_status != new_status or header.process_comment != comment:
        header.process_status = new_status
        header.process_comment = comment
        header.processed_at = datetime.now(timezone.utc)


def process_pending_lines(db: Session, product_by_header: dict[int, Product]) -> list[LineProcessRowResult]:
    """Carry out the action of every waiting line in the given files, each
    file's lines with the product chosen for that file (product_by_header:
    header_data_id → Product). One result per line. Best-effort, like the
    Excel import: each line runs inside its own SAVEPOINT, so one failing
    line rolls back only itself, stays "new" with the error as its comment,
    and never stops the rest.
    """
    pending = [(line, filename) for line, filename in list_pending_lines(db) if line.header_data_id in product_by_header]

    results: list[LineProcessRowResult] = []
    touched_header_ids: set[int] = set()
    touched_epcs: set[str] = set()

    for line, filename in pending:
        handler = PROCESSABLE_ACTIONS[line.action.strip().lower()]
        savepoint = db.begin_nested()
        try:
            context = ProcessContext(product=product_by_header.get(line.header_data_id))
            outcome, comment = handler(db, line, context)
            line.process_status = PROCESS_LOADED
            line.process_comment = comment
            line.processed_at = datetime.now(timezone.utc)
            savepoint.commit()
            touched_epcs.add(line.epc.strip())
        except (ValueError, IntegrityError) as error:
            savepoint.rollback()
            outcome = "error"
            comment = str(error) if isinstance(error, ValueError) else "This line conflicts with existing data"
            # Stays "new" (so it's offered again next time); only the
            # comment records what went wrong.
            line.process_comment = comment

        touched_header_ids.add(line.header_data_id)
        results.append(
            LineProcessRowResult(
                line_id=line.id,
                header_filename=filename,
                line_number=line.line_number,
                epc=line.epc,
                action=line.action,
                outcome=outcome,
                detail=comment,
            )
        )

    # Newly created tags: refresh the match snapshot of every (non-
    # cancelled) line with those EPCs, so they flip from "no_match" to
    # "converted" right away instead of waiting for the next Synchro.
    if touched_epcs:
        tags_by_epc, product_names_by_id = preload_tag_lookup(db)
        lines_to_rematch = db.scalars(
            select(TagLineData).where(TagLineData.epc.in_(touched_epcs), TagLineData.status != "cancelled")
        ).all()
        for other_line in lines_to_rematch:
            for field, value in match_tag(other_line.epc, tags_by_epc, product_names_by_id).items():
                setattr(other_line, field, value)

    for header_id in touched_header_ids:
        refresh_header_process_status(db, header_id)

    db.commit()
    return results


def cancel_line_processing(db: Session, line_id: int, comment: str) -> TagLineData | None:
    """Mark one line "cancelled" with the user's reason, and refresh its
    file's overall status. Returns None if the line doesn't exist.
    """
    line = db.get(TagLineData, line_id)
    if line is None:
        return None

    line.process_status = PROCESS_CANCELLED
    line.process_comment = comment
    line.processed_at = datetime.now(timezone.utc)
    refresh_header_process_status(db, line.header_data_id)
    db.commit()
    db.refresh(line)
    return line
