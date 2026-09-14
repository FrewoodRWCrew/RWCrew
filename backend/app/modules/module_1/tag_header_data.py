# Business logic backing the "Tag Headerdata" screen: scanning
# TagScan's "Unreaded Tags" intake subfolder for new CSV files, logging
# each one exactly once into Tagscan_header_data, moving it into a
# sibling "Read Tags" folder so it's never picked up again, and — as of
# the "Tag Linedata" feature — also logging every data line inside it,
# enriched with a snapshot of its matching TagManagement tag (if any).

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.rfid_tag import RfidTag
from app.db.models.scanner import Scanner
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.modules.module_1.file_browser import get_source_root
from app.modules.module_1.tag_line_data import (
    match_scanner,
    match_tag,
    parse_csv_rows,
    preload_scanner_lookup,
    preload_tag_lookup,
)
from app.schemas.tagscan import TagHeaderDataScanFileResult

UNREADED_SUBFOLDER = "Unreaded Tags"
READED_SUBFOLDER = "Read Tags"


def _unreaded_dir(db: Session) -> Path:
    return get_source_root(db) / UNREADED_SUBFOLDER


def _readed_dir(db: Session) -> Path:
    return get_source_root(db) / READED_SUBFOLDER


def list_header_data(db: Session) -> list[TagHeaderData]:
    """Every logged file, newest first, for the screen's table."""
    return list(db.scalars(select(TagHeaderData).order_by(TagHeaderData.created_at.desc())).all())


def delete_header_data(db: Session, header_id: int) -> bool:
    """Permanently delete one header row and every line row linked to it,
    so its filename can be logged again by a future scan. Returns False
    if no such row exists. Deliberately does NOT touch the physical CSV
    file (it's presumably already sitting in Read Tags) — move it back
    into Unreaded Tags yourself if you want it re-scanned.
    """
    header = db.get(TagHeaderData, header_id)
    if header is None:
        return False

    db.execute(delete(TagLineData).where(TagLineData.header_data_id == header_id))
    db.delete(header)
    db.commit()
    return True


def _build_line_rows(
    header_data_id: int,
    parsed_rows: list[dict],
    tags_by_epc: dict[str, RfidTag],
    product_names_by_id: dict[int, str],
    scanners_by_name: dict[str, Scanner],
    scanners_by_id: dict[int, Scanner],
) -> list[TagLineData]:
    """Turn one file's parsed CSV rows into TagLineData rows, matching
    each one's EPC against the (pre-loaded, scan-wide) set of registered
    RFID tags and its raw "Scanner" value against the registered Scanners
    devices, snapshotting each match's key fields when found — the same
    match_tag()/match_scanner() used by the "Synchro" re-check on the Tag
    Linedata screen itself (see tag_line_data.sync_line_data).
    """
    return [
        TagLineData(
            header_data_id=header_data_id,
            line_number=row["line_number"],
            scanner=row["scanner"],
            epc=row["epc"],
            rssi=row["rssi"],
            antenna=row["antenna"],
            count=row["count"],
            last_seen=row["last_seen"],
            **match_tag(row["epc"], tags_by_epc, product_names_by_id),
            **match_scanner(row["scanner"], None, scanners_by_name, scanners_by_id),
        )
        for row in parsed_rows
    ]


def scan_unreaded_tags(db: Session) -> tuple[list[TagHeaderDataScanFileResult], list[TagHeaderData]]:
    """The full "Scan" action: process every CSV file directly inside
    Unreaded Tags (non-recursive — the scan is scoped to that one folder
    only), logging and moving each one that isn't already recorded, and
    logging every data line inside it (see "Tag Linedata"). One bad file
    never aborts the rest of the scan — every failure is caught and
    reported per-file instead.
    """
    unreaded_dir = _unreaded_dir(db)
    readed_dir = _readed_dir(db)

    results: list[TagHeaderDataScanFileResult] = []

    if not unreaded_dir.is_dir():
        return results, list_header_data(db)

    csv_files = sorted(
        entry for entry in unreaded_dir.iterdir() if entry.is_file() and entry.suffix.lower() == ".csv"
    )

    # Loaded once per scan call (not per-file/per-row) — a scan can cover
    # many files with many rows each, and neither list changes mid-scan.
    tags_by_epc, product_names_by_id = preload_tag_lookup(db)
    scanners_by_name, scanners_by_id = preload_scanner_lookup(db)

    for file in csv_files:
        filename = file.name

        already_logged = db.scalar(select(TagHeaderData).where(TagHeaderData.filename == filename))
        if already_logged is not None:
            results.append(
                TagHeaderDataScanFileResult(
                    filename=filename, outcome="skipped_duplicate", detail="This file was already logged"
                )
            )
            continue

        # Reading + parsing happens before any DB write: a file that
        # can't be read at all gets no header row and no line rows.
        try:
            parsed_rows = parse_csv_rows(file)
        except OSError as error:
            results.append(TagHeaderDataScanFileResult(filename=filename, outcome="error", detail=str(error)))
            continue

        # The file's own scanner: the first non-empty "Scanner" value among
        # its parsed rows (every row in one CSV comes from the same
        # physical device), matched the same way a line's raw value is.
        header_scanner = next((row["scanner"] for row in parsed_rows if row["scanner"]), None)
        header_match = match_scanner(header_scanner, None, scanners_by_name, scanners_by_id)

        # The number of data lines actually logged below — NOT a raw
        # physical line count, so this always matches how many rows show
        # up for this file on the Tag Linedata screen (the CSV's own
        # header row and any skipped blank line are never counted here).
        new_entry = TagHeaderData(
            filename=filename,
            line_count=len(parsed_rows),
            scanner=header_scanner,
            **header_match,
        )
        db.add(new_entry)
        try:
            db.commit()
        except IntegrityError:
            # Another scan logged this exact filename a moment ago — the
            # DB's unique constraint is what actually guarantees no file
            # is ever double-logged; this pre-check is just the common,
            # fast path.
            db.rollback()
            results.append(
                TagHeaderDataScanFileResult(
                    filename=filename, outcome="skipped_duplicate", detail="This file was already logged"
                )
            )
            continue

        # The header row (and, right below, its line rows) are committed
        # and truthful even if the move below fails — never rolled back,
        # since that would let the same file be re-logged later under a
        # new id/timestamp. A file that fails to move is left in place
        # and reported as an error for an operator to look at; it will
        # show as "already logged" on the next scan rather than being
        # counted twice.
        db.add_all(
            _build_line_rows(
                new_entry.id, parsed_rows, tags_by_epc, product_names_by_id, scanners_by_name, scanners_by_id
            )
        )
        db.commit()

        try:
            readed_dir.mkdir(parents=True, exist_ok=True)
            destination = readed_dir / filename
            file.replace(destination)
        except OSError as error:
            results.append(
                TagHeaderDataScanFileResult(
                    filename=filename,
                    outcome="error",
                    detail=f"Logged, but failed to move the file: {error}",
                )
            )
            continue

        results.append(TagHeaderDataScanFileResult(filename=filename, outcome="logged"))

    return results, list_header_data(db)
