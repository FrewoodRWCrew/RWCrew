# One-off fill of the "CSV Comment" field (csv_comment_cell) for data that was
# scanned before the field existed: every logged file is re-read from its
# archived copy in "Read Tags", its lines get their own "Comment" cell back (by
# line number), the file gets its joined value, and every registered tag gets
# the latest non-empty value scanned for its EPC — the same result a fresh scan
# would have produced. Run through app/cli/backfill_tagscan_csv_comment.py.

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.rfid_tag import RfidTag
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.modules.module_1.file_browser import get_source_root
from app.modules.module_1.tag_header_data import READED_SUBFOLDER
from app.modules.module_1.tag_line_data import apply_comment_to_tag, joined_comments, parse_csv_rows


@dataclass
class CsvCommentBackfillResult:
    """What the backfill did, for the CLI's report."""

    files_read: int = 0
    lines_filled: int = 0
    tags_filled: int = 0
    # Logged files whose archived CSV couldn't be found or read.
    missing_files: list[str] = field(default_factory=list)


def backfill_csv_comment_cells(db: Session) -> CsvCommentBackfillResult:
    """Fill csv_comment_cell on files, lines and tags from the archived CSVs.
    Safe to run again: files whose lines already have a value are skipped,
    and tags only change when a newer value exists. Doesn't commit.
    """
    result = CsvCommentBackfillResult()
    readed_dir = get_source_root(db) / READED_SUBFOLDER

    # Files that already have a value on any line were scanned (or filled)
    # with the new field — nothing to do for them.
    done_header_ids = set(
        db.scalars(select(TagLineData.header_data_id).where(TagLineData.csv_comment_cell.is_not(None)).distinct())
    )

    for header in db.scalars(select(TagHeaderData).order_by(TagHeaderData.id)).all():
        if header.id in done_header_ids or header.csv_comment_cell:
            continue

        # The archived copy of the file, as moved there by the scan.
        file = readed_dir / header.filename
        try:
            rows = parse_csv_rows(file)
        except OSError:
            result.missing_files.append(header.filename)
            continue
        result.files_read += 1

        # Each line gets its own row's cell back, matched by CSV line number.
        values_by_line = {row["line_number"]: row["csv_comment_cell"] for row in rows}
        for line in db.scalars(select(TagLineData).where(TagLineData.header_data_id == header.id)).all():
            value = values_by_line.get(line.line_number)
            if value and line.csv_comment_cell != value:
                line.csv_comment_cell = value
                result.lines_filled += 1
        header.csv_comment_cell = joined_comments([row["csv_comment_cell"] for row in rows])

    db.flush()

    # Per EPC the newest non-empty value (oldest file first, CSV order, so the
    # last one seen wins) — matched by EPC rather than rfid_tag_id, so tags
    # created later from a line (Assignment) get it too.
    latest_by_epc: dict[str, str] = {}
    lines = db.execute(
        select(TagLineData.epc, TagLineData.csv_comment_cell)
        .join(TagHeaderData, TagLineData.header_data_id == TagHeaderData.id)
        .where(TagLineData.csv_comment_cell.is_not(None))
        .order_by(TagHeaderData.created_at, TagHeaderData.id, TagLineData.line_number)
    ).all()
    for epc, value in lines:
        latest_by_epc[epc.strip()] = value

    for tag in db.scalars(select(RfidTag)).all():
        value = latest_by_epc.get(tag.epc_uid.strip())
        if value and tag.csv_comment_cell != value:
            apply_comment_to_tag(tag, value)
            result.tags_filled += 1

    db.flush()
    return result
