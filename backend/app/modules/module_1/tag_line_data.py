# Business logic backing the "Tag Linedata" screen: parsing the data
# lines out of a CSV scanned by Tag Headerdata's Scan action, matching a
# line's EPC against the current TagManagement registry and its raw
# "Scanner" value against the current Scanners registry (both when a line
# is first created and whenever it's later re-synced), and listing the
# resulting rows for that screen's table.

import csv
import io
from pathlib import Path
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.product_type import ProductType
from app.db.models.rfid_tag import RfidTag
from app.db.models.scanner import Scanner
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
    kar_nummer: str | None


def preload_tag_lookup(db: Session) -> tuple[dict[str, RfidTag], dict[int, str], dict[int, str]]:
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
    # Kar numbers by id, for the tag's KarTracker kar (see RfidTag.kar_id).
    kar_numbers_by_id = {kar.id: kar.kar_nummer for kar in db.scalars(select(KarTrackerKar)).all()}
    return tags_by_epc, product_names_by_id, kar_numbers_by_id


def match_tag(
    epc: str,
    tags_by_epc: dict[str, RfidTag],
    product_names_by_id: dict[int, str],
    kar_numbers_by_id: dict[int, str],
) -> TagMatch:
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
            kar_nummer=None,
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
        kar_nummer=kar_numbers_by_id.get(matched_tag.kar_id) if matched_tag.kar_id is not None else None,
    )


class ScannerMatch(TypedDict):
    """What one raw "Scanner" CSV value currently matches, if anything —
    the exact set of fields a TagLineData/TagHeaderData row keeps in sync
    with the Scanners registry, both when the row is first created by a
    scan and every time it's re-synced.
    """

    scanner_id: int | None
    scanner_name: str | None
    scanner_location: str | None
    scanner_technology: str | None
    scanner_type: str | None


def preload_scanner_lookup(db: Session) -> tuple[dict[str, Scanner], dict[int, Scanner], dict[int, str]]:
    """The current Scanners registry snapshot needed by match_scanner() —
    loaded once per scan/sync call (not per-row), since neither dict
    changes mid-call.

    Two dicts, because a Scanner's name plays two different roles: it's
    the matchable key used to find a FIRST match against a CSV's raw
    "Scanner" text, but — unlike RfidTag's epc_uid — it's also a rename-
    able display field, so an ALREADY-matched line must refresh its
    snapshot by the stable scanner_id it recorded, not by re-matching the
    (unchanged) raw CSV text against the (possibly renamed) name; doing
    the latter would silently un-match the line the moment its device
    got renamed. See match_scanner()'s own docstring for how this plays
    out.

    The by-name dict is keyed by a stripped, lowercased scanner name so
    matching is case-insensitive (mirroring the Product.name.ilike()
    precedent used elsewhere in this codebase for name-based lookups) —
    a CSV's "Scanner" column is free text typed/configured on the reader
    hardware, not a guaranteed-exact-case identifier.
    """
    scanners = db.scalars(select(Scanner)).all()
    scanners_by_name = {scanner.scanner.strip().lower(): scanner for scanner in scanners}
    scanners_by_id = {scanner.id: scanner for scanner in scanners}
    # A scanner's Type is a MasterData ProductType — its name by id, for the
    # "Type" snapshot (which activity the scan is for).
    type_names_by_id = {product_type.id: product_type.name for product_type in db.scalars(select(ProductType)).all()}
    return scanners_by_name, scanners_by_id, type_names_by_id


def match_scanner(
    raw_scanner: str | None,
    current_scanner_id: int | None,
    scanners_by_name: dict[str, Scanner],
    scanners_by_id: dict[int, Scanner],
    type_names_by_id: dict[int, str],
) -> ScannerMatch:
    """Resolve one row's scanner snapshot.

    If it's already matched to a scanner (current_scanner_id is set —
    i.e. this is a re-sync of a previously-matched row), refresh the
    snapshot from that SAME device by id, so a rename/relocate is picked
    up without ever re-deciding which device the raw text refers to.

    Otherwise (not yet matched — either a brand-new scan, or a previous
    sync that found nothing), look up the raw "Scanner" CSV text against
    the current registry by name, so a device registered after the fact
    can still be picked up on the next sync.

    A blank value or one with no matching Scanners record is a soft "no
    match" — it never blocks a scan, and the raw text is kept as-is by
    the caller regardless of whether this returns a match.
    """
    matched_scanner = (
        scanners_by_id.get(current_scanner_id)
        if current_scanner_id is not None
        else (scanners_by_name.get(raw_scanner.strip().lower()) if raw_scanner else None)
    )
    if matched_scanner is None:
        return ScannerMatch(
            scanner_id=None, scanner_name=None, scanner_location=None, scanner_technology=None, scanner_type=None
        )

    return ScannerMatch(
        scanner_id=matched_scanner.id,
        scanner_name=matched_scanner.scanner,
        scanner_location=matched_scanner.location,
        scanner_technology=matched_scanner.technology,
        scanner_type=type_names_by_id.get(matched_scanner.type_id),
    )


# The exact column names the real scanner hardware writes — matched by
# name (not position) so a reordered column wouldn't silently misparse.
COLUMN_SCANNER = "Scanner"
COLUMN_EPC = "EPC"
COLUMN_RSSI = "RSSI (raw)"
COLUMN_ANTENNA = "Antenna"
COLUMN_COUNT = "Count"
COLUMN_LAST_SEEN = "Last Seen"
# Optional columns: older CSVs don't have them, in which case the parsed
# value is simply None.
COLUMN_MODE = "Mode"
COLUMN_ACTION = "Action"

# Every column above — anything else is a candidate for the free-text
# "product / comments" column, see comment_column().
KNOWN_COLUMNS = {
    COLUMN_SCANNER,
    COLUMN_EPC,
    COLUMN_RSSI,
    COLUMN_ANTENNA,
    COLUMN_COUNT,
    COLUMN_LAST_SEEN,
    COLUMN_MODE,
    COLUMN_ACTION,
}
# Header names (lowercased) recognised as the "product / comments" column.
COMMENT_COLUMN_NAMES = {"comment", "comments", "product", "products", "remark", "remarks", "opmerking", "opmerkingen"}


def comment_column(fieldnames: list[str] | None) -> str | None:
    """Which CSV column holds the free-text "product / comments" value: one
    whose name is in COMMENT_COLUMN_NAMES (any case), otherwise the LAST
    column when it isn't one of the known scanner columns (the scanner app
    writes it at the end). None when the CSV has no such column.
    """
    if not fieldnames:
        return None
    for name in fieldnames:
        if name and name.strip().lower() in COMMENT_COLUMN_NAMES:
            return name
    last = fieldnames[-1]
    if last and last.strip() not in KNOWN_COLUMNS:
        return last
    return None


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


def read_csv_mode(contents: bytes) -> str | None:
    """The first non-empty "Mode" value in a CSV's raw bytes, or None when
    the column is missing or empty everywhere (e.g. an older CSV). Used by
    the device intake to decide which environment a file belongs to,
    before the file is ever written to disk.
    """
    # utf-8-sig for the same leading-BOM reason as parse_csv_rows below.
    text = contents.decode("utf-8-sig", errors="replace")
    for row in csv.DictReader(io.StringIO(text, newline="")):
        mode = (row.get(COLUMN_MODE) or "").strip()
        if mode:
            return mode
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
        reader = csv.DictReader(handle)
        csv_comment_column = comment_column(reader.fieldnames)
        for line_number, row in enumerate(reader, start=2):
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
                    "mode": (row.get(COLUMN_MODE) or "").strip() or None,
                    "action": (row.get(COLUMN_ACTION) or "").strip() or None,
                    "csv_comment": (
                        (row.get(csv_comment_column) or "").strip() or None if csv_comment_column else None
                    ),
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
    against the CURRENT TagManagement registry and its raw "scanner" text
    against the CURRENT Scanners registry, refreshing each line's
    status/product/serial/manufacturer/batch and scanner snapshot to
    match — catching a tag or scanner that was registered, reassigned, or
    renamed after the line was first scanned. Also re-resolves every
    TagHeaderData row's own scanner snapshot the same way (a scanner
    rename only takes effect there once Synchro is re-run too), though
    that isn't counted in the returned total. Returns how many lines
    actually changed.

    Cancelled lines are deliberately left untouched: cancelling a line is
    a manual override (see router.py's cancel endpoint), and a routine
    sync must never silently flip it back to converted/no_match.
    """
    tags_by_epc, product_names_by_id, kar_numbers_by_id = preload_tag_lookup(db)
    scanners_by_name, scanners_by_id, type_names_by_id = preload_scanner_lookup(db)

    lines = db.scalars(select(TagLineData).where(TagLineData.status != "cancelled")).all()

    updated_count = 0
    for line in lines:
        match: dict = {
            **match_tag(line.epc, tags_by_epc, product_names_by_id, kar_numbers_by_id),
            **match_scanner(line.scanner, line.scanner_id, scanners_by_name, scanners_by_id, type_names_by_id),
        }
        changed = any(getattr(line, field) != value for field, value in match.items())
        if not changed:
            continue
        for field, value in match.items():
            setattr(line, field, value)
        updated_count += 1

    # Each header's first non-empty scanner/mode/action among its own lines
    # (in CSV order) — the same rule a new scan uses. Fills in headers logged
    # before the header-level columns existed, whose own value is empty.
    # Cancelled lines count too: they still say which device wrote the file.
    first_values_by_header: dict[int, dict[str, str]] = {}
    all_line_values = db.execute(
        select(TagLineData.header_data_id, TagLineData.scanner, TagLineData.mode, TagLineData.action).order_by(
            TagLineData.header_data_id, TagLineData.line_number
        )
    ).all()
    for row in all_line_values:
        first_values = first_values_by_header.setdefault(row.header_data_id, {})
        for field in ("scanner", "mode", "action"):
            value = getattr(row, field)
            if value and field not in first_values:
                first_values[field] = value

    for header in db.scalars(select(TagHeaderData)).all():
        first_values = first_values_by_header.get(header.id, {})
        for field in ("scanner", "mode", "action"):
            if not getattr(header, field) and first_values.get(field):
                setattr(header, field, first_values[field])
        header_match = match_scanner(
            header.scanner, header.scanner_id, scanners_by_name, scanners_by_id, type_names_by_id
        )
        if any(getattr(header, field) != value for field, value in header_match.items()):
            for field, value in header_match.items():
                setattr(header, field, value)

    db.commit()
    return updated_count
