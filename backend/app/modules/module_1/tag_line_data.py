# Business logic backing the "Tag Linedata" screen: parsing the data
# lines out of a CSV scanned by Tag Headerdata's Scan action, matching a
# line's EPC against the current TagManagement registry (both when a
# line is first created and whenever it's later re-synced), and listing
# the resulting rows for that screen's table.

import csv
from pathlib import Path
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData


class TagMatch(TypedDict):
    """What one EPC currently matches, if anything — the exact set of
    fields a TagLineData row keeps in sync with TagManagement, both when
    the row is first created by a scan and every time it's re-synced.
    """

    status: str
    rfid_tag_id: int | None
    assigned_product_name: str | None
    assigned_serial_number: str | None
    manufacturer: str | None
    batch_number: str | None


def preload_tag_lookup(db: Session) -> tuple[dict[str, RfidTag], dict[int, str]]:
    """The current registry snapshot needed by match_tag() — loaded once
    per scan/sync call (not per-row), since neither list changes mid-call.

    Keyed by a STRIPPED epc_uid: RfidTagCreateRequest/RfidTagUpdateRequest
    already trim it on every create/update (see schemas/tagscan.py), but
    this also protects against any row that predates that validator or
    was ever inserted outside the API (e.g. a stray trailing tab pasted
    from a spreadsheet) — a scanned CSV's EPC is stripped too (see
    parse_csv_rows), so an untrimmed registry key would otherwise never
    match, silently.
    """
    tags_by_epc = {tag.epc_uid.strip(): tag for tag in db.scalars(select(RfidTag)).all()}
    product_names_by_id = {product.id: product.name for product in db.scalars(select(Product)).all()}
    return tags_by_epc, product_names_by_id


def match_tag(epc: str, tags_by_epc: dict[str, RfidTag], product_names_by_id: dict[int, str]) -> TagMatch:
    """Look up one EPC against the pre-loaded registry snapshot."""
    matched_tag = tags_by_epc.get(epc)
    if matched_tag is None:
        return TagMatch(
            status="no_match",
            rfid_tag_id=None,
            assigned_product_name=None,
            assigned_serial_number=None,
            manufacturer=None,
            batch_number=None,
        )

    return TagMatch(
        status="converted",
        rfid_tag_id=matched_tag.id,
        assigned_product_name=(
            product_names_by_id.get(matched_tag.assigned_product_id)
            if matched_tag.assigned_product_id is not None
            else None
        ),
        assigned_serial_number=matched_tag.assigned_serial_number,
        manufacturer=matched_tag.manufacturer,
        batch_number=matched_tag.batch_number,
    )

# The exact column names the real scanner hardware writes — matched by
# name (not position) so a reordered column wouldn't silently misparse.
COLUMN_SCANNER = "Scanner"
COLUMN_EPC = "EPC"
COLUMN_RSSI = "RSSI (raw)"
COLUMN_ANTENNA = "Antenna"
COLUMN_COUNT = "Count"
COLUMN_LAST_SEEN = "Last Seen"


def _parse_int(value: str | None) -> int | None:
    """Best-effort int parsing — a blank or non-numeric cell becomes None
    rather than aborting the whole row.
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def parse_csv_rows(file: Path) -> list[dict]:
    """Every data row in a CSV, keyed by the real column names above.
    Skips a row entirely if its EPC cell is empty (e.g. a trailing blank
    line at the end of the file) — TagLineData.epc is required, and an
    empty EPC carries no information worth logging.
    """
    rows: list[dict] = []
    # utf-8-sig, not plain utf-8: scanner software (and Excel-edited
    # CSVs in general) commonly write a leading UTF-8 BOM. Under plain
    # utf-8 that BOM decodes as a stray U+FEFF character glued onto the
    # first header name ("﻿Scanner"), which would then never match
    # COLUMN_SCANNER — utf-8-sig strips a BOM if present (and is
    # otherwise identical to utf-8 when there isn't one).
    with file.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        # start=2: the header row is physical line 1, so the first data
        # row is line 2 — line_number can then point straight back to the
        # exact row in the source file.
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            epc = (row.get(COLUMN_EPC) or "").strip()
            if not epc:
                continue
            rows.append(
                {
                    "line_number": line_number,
                    "scanner": (row.get(COLUMN_SCANNER) or "").strip() or None,
                    "epc": epc,
                    "rssi": _parse_int(row.get(COLUMN_RSSI)),
                    "antenna": _parse_int(row.get(COLUMN_ANTENNA)),
                    "count": _parse_int(row.get(COLUMN_COUNT)),
                    "last_seen": (row.get(COLUMN_LAST_SEEN) or "").strip() or None,
                }
            )
    return rows


def list_line_data(db: Session) -> list[tuple[TagLineData, str]]:
    """Every logged line, newest-scanned file first, paired with its
    header file's filename (denormalized here via a join, for the
    screen's table).

    Ordered by header_data_id (not created_at): every line from one scan
    is inserted in a single commit, so they all share the exact same
    server-side timestamp — sorting by created_at alone leaves ties
    broken in whatever order Postgres happens to return them, which is
    NOT guaranteed to match the CSV. header_data_id is unique per file
    and assigned strictly in scan order, and line_number is the row's
    own physical position in that CSV — together they deterministically
    reproduce "newest file first, lines in the same order as the CSV".
    """
    rows = db.execute(
        select(TagLineData, TagHeaderData.filename)
        .join(TagHeaderData, TagLineData.header_data_id == TagHeaderData.id)
        .order_by(TagLineData.header_data_id.desc(), TagLineData.line_number.asc())
    ).all()
    return [(line, filename) for line, filename in rows]


def list_lines_for_header(db: Session, header_id: int) -> list[TagLineData]:
    """Every logged line for one specific file, in CSV order — for the
    PDF summary, which already has the header row (and hence its
    filename) in hand, so it queries this directly instead of fetching
    every line in the whole database via list_line_data just to filter
    down to one header_data_id in Python.
    """
    return list(
        db.scalars(
            select(TagLineData).where(TagLineData.header_data_id == header_id).order_by(TagLineData.line_number)
        ).all()
    )


def sync_line_data(db: Session) -> int:
    """The "Synchro" action: re-check every non-cancelled line's EPC
    against the CURRENT TagManagement registry, and refresh its status
    and product/serial/manufacturer/batch snapshot to match — catching a
    tag that was registered, reassigned, or renamed after the line was
    first scanned. Returns how many lines actually changed.

    Cancelled lines are deliberately left untouched: cancelling a line is
    a manual override (see router.py's cancel endpoint), and a routine
    sync must never silently flip it back to converted/no_match.
    """
    tags_by_epc, product_names_by_id = preload_tag_lookup(db)

    lines = db.scalars(select(TagLineData).where(TagLineData.status != "cancelled")).all()

    updated_count = 0
    for line in lines:
        match = match_tag(line.epc, tags_by_epc, product_names_by_id)
        changed = any(getattr(line, field) != value for field, value in match.items())
        if not changed:
            continue
        for field, value in match.items():
            setattr(line, field, value)
        updated_count += 1

    db.commit()
    return updated_count
