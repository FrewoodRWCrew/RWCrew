# Inboeken from a TagScan scan: scanned CSV lines with the action "Book In"
# that are still waiting ("new") become basket lines for the booking panel,
# the same way an uploaded Inboeken Excel does (booking_import.py). Every
# distinct EPC in a file is one piece of the product its tag is assigned to
# in TagManagement (looked up live, not from the scan-time snapshot, so a tag
# registered after the scan counts too).
#
# Reading never books anything. The lines are only marked "loaded" when the
# person confirms the booking: the booking request carries the line ids, and
# mark_lines_booked() runs in the booking's own transaction — so a booking
# and its scan lines always go together, and the same scan can't be booked
# twice. Lines with a problem (unknown tag, tag without product) stay
# waiting: register the tag and load again, or cancel the line with a reason.
#
# Problems come back as "code|param", translated by the frontend under
# stockMaster.booking.importErrors.<code> (shared with the Excel import).

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.rfid_tag import RfidTag
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.modules.module_1.line_processing import (
    BOOK_IN_ACTIONS,
    PROCESS_LOADED,
    pending_filter,
    refresh_header_process_status,
)
from app.modules.module_4.stock_service import StockError
from app.schemas.stockmaster import BookInImportLine, TagscanBookInFile, TagscanBookInProblem


def count_waiting_lines(db: Session) -> int:
    """How many scanned "Book In" lines are waiting — for StockMaster's banner."""
    return db.scalar(select(func.count(TagLineData.id)).where(*pending_filter(BOOK_IN_ACTIONS))) or 0


def get_waiting_line(db: Session, line_id: int) -> TagLineData | None:
    """One waiting "Book In" line, or None when it doesn't exist or isn't one."""
    return db.scalar(select(TagLineData).where(TagLineData.id == line_id, *pending_filter(BOOK_IN_ACTIONS)))


def list_waiting_files(db: Session) -> list[TagscanBookInFile]:
    """Every scanned file with waiting "Book In" lines (oldest first), each
    with its basket lines (product + number of distinct tags) and the lines
    that can't be booked yet.
    """
    rows = db.execute(
        select(TagLineData, TagHeaderData)
        .join(TagHeaderData, TagLineData.header_data_id == TagHeaderData.id)
        .where(*pending_filter(BOOK_IN_ACTIONS))
        .order_by(TagLineData.header_data_id.asc(), TagLineData.line_number.asc())
    ).all()
    if not rows:
        return []

    # Every scanned EPC's tag at once, instead of one query per line.
    epcs = {line.epc.strip() for line, _header in rows}
    tags_by_epc = {tag.epc_uid: tag for tag in db.scalars(select(RfidTag).where(RfidTag.epc_uid.in_(epcs))).all()}

    files: dict[int, TagscanBookInFile] = {}
    quantities: dict[int, dict[int, int]] = {}  # header id → product id → pieces, in file order
    seen_epcs: dict[int, set[str]] = {}  # header id → EPCs already counted in that file

    for line, header in rows:
        file = files.get(header.id)
        if file is None:
            file = TagscanBookInFile(
                header_data_id=header.id, filename=header.filename, scanned_at=header.created_at,
                line_ids=[], lines=[], problems=[],
            )
            files[header.id] = file
            quantities[header.id] = {}
            seen_epcs[header.id] = set()

        epc = line.epc.strip()
        tag = tags_by_epc.get(epc)
        if tag is None or tag.assigned_product_id is None:
            code = "unknown_tag" if tag is None else "no_product"
            file.problems.append(
                TagscanBookInProblem(line_id=line.id, line_number=line.line_number, epc=epc, detail=f"{code}|{epc}")
            )
            continue

        # The line is used either way; the same tag read twice is one piece.
        file.line_ids.append(line.id)
        if epc in seen_epcs[header.id]:
            continue
        seen_epcs[header.id].add(epc)
        product_quantities = quantities[header.id]
        product_quantities[tag.assigned_product_id] = product_quantities.get(tag.assigned_product_id, 0) + 1

    for header_id, file in files.items():
        file.lines = [
            BookInImportLine(product_id=product_id, quantity=quantity)
            for product_id, quantity in quantities[header_id].items()
        ]
    return list(files.values())


def mark_lines_booked(db: Session, line_ids: list[int], document: StockMasterDocument) -> None:
    """Mark the scan lines a booking was made from as "loaded", pointing at
    that booking. Every line must still be a waiting "Book In" line —
    otherwise someone booked (or cancelled) it in the meantime and the
    whole booking is refused. Does not commit; the router does.
    """
    unique_ids = set(line_ids)
    lines = db.scalars(
        select(TagLineData)
        .where(TagLineData.id.in_(unique_ids), *pending_filter(BOOK_IN_ACTIONS))
        .order_by(TagLineData.id)
        .with_for_update()
    ).all()
    if len(lines) != len(unique_ids):
        raise StockError("tagscan_already_booked")

    now = datetime.now(timezone.utc)
    for line in lines:
        line.process_status = PROCESS_LOADED
        line.process_comment = f"Booked in: {document.doc_number}"
        line.processed_at = now

    # Each file's overall status follows its lines.
    for header_id in {line.header_data_id for line in lines}:
        refresh_header_process_status(db, header_id)
