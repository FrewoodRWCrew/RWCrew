# Carrying out the action a scanned CSV line asks for. Every line logged by
# a Tag Headerdata scan starts with process_status "new"; this module turns
# it into "loaded" (done) or "cancelled" (deliberately skipped), with a
# process_comment saying why, and keeps the line's file (TagHeaderData) in
# sync with an overall status of its own.
#
# Only actions listed in PROCESSABLE_ACTIONS are offered for processing —
# today just "Assignment" (create the tag when it isn't registered yet).
# Adding a new action = write one more _process_<action>() handler and add
# it to that dict; lines with any other action simply stay "new" until
# their own handler exists.
#
# Kept free of FastAPI/routing concerns (mirrors tag_import.py), so it's
# easy to unit test on its own.

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.rfid_tag import RfidTag
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.modules.module_1.tag_line_data import match_tag, preload_tag_lookup
from app.schemas.tagscan import LineProcessRowResult

PROCESS_NEW = "new"
PROCESS_LOADED = "loaded"
PROCESS_CANCELLED = "cancelled"

ACTION_ASSIGNMENT = "assignment"

COMMENT_TAG_CREATED = "Tag created"
COMMENT_TAG_EXISTS = "Tag already exists — nothing created"
COMMENT_NO_LINES = "No lines"


def _process_assignment(db: Session, line: TagLineData) -> tuple[str, str]:
    """"Assignment": register the line's EPC as a new RFID tag unless it's
    already registered. Returns (outcome, comment). The new tag is flushed
    straight away, so a second line with the same EPC later in the same
    batch finds it and reports "exists" instead of colliding on the unique
    epc_uid.
    """
    epc = line.epc.strip()
    if db.scalar(select(RfidTag.id).where(RfidTag.epc_uid == epc)) is not None:
        return "exists", COMMENT_TAG_EXISTS

    db.add(
        RfidTag(
            epc_uid=epc,
            status="active",
            manufacturer=line.manufacturer,
            batch_number=line.batch_number,
            last_reader_id=line.scanner_name or line.scanner,
            last_location=line.scanner_location,
        )
    )
    db.flush()
    return "created", COMMENT_TAG_CREATED


# Lowercased CSV "Action" value → the handler that carries it out.
PROCESSABLE_ACTIONS: dict[str, Callable[[Session, TagLineData], tuple[str, str]]] = {
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


def process_pending_lines(db: Session, line_ids: list[int] | None = None) -> list[LineProcessRowResult]:
    """Carry out every waiting line's action (or only those in line_ids),
    one result per line. Best-effort, like the Excel import: each line runs
    inside its own SAVEPOINT, so one failing line rolls back only itself,
    stays "new" with the error as its comment, and never stops the rest.
    """
    pending = list_pending_lines(db)
    if line_ids is not None:
        wanted = set(line_ids)
        pending = [(line, filename) for line, filename in pending if line.id in wanted]

    results: list[LineProcessRowResult] = []
    touched_header_ids: set[int] = set()
    touched_epcs: set[str] = set()

    for line, filename in pending:
        handler = PROCESSABLE_ACTIONS[line.action.strip().lower()]
        savepoint = db.begin_nested()
        try:
            outcome, comment = handler(db, line)
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
