# Bulk XLSX import/export for the Leverdata (delivery + pick-up date per
# festival, the "Festivals_leverdatum" table): building the downloadable
# template, applying an uploaded workbook row by row, and exporting the
# saved dates back out. Same overall shape as afleverlocatie_import.py.
#
# Unlike the other KarTracker imports this one UPSERTS: there is at most one
# Leverdatum row per festival and the "Delivery Dates" screen itself updates
# in place, so a festival that already has dates gets them overwritten
# instead of the row being rejected. A festival is identified by season name
# + festival name, since festival names are only unique within a season.
#
# A row with both dates blank is skipped (never deletes a record) — that
# keeps the pre-filled template and an unedited export safe to re-upload.
# Clearing dates stays a job for the Delivery Dates screen.

import io
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.season import Season
from app.schemas.kartracker import LeverdatumImportRowResult

# The workbook's columns, in order — also the header row of the template.
TEMPLATE_COLUMNS = ["season_name", "festival_name", "delivery_date", "pickup_date"]

# How date cells are displayed in the generated workbooks.
_DATE_NUMBER_FORMAT = "DD/MM/YYYY"

# Accepted spellings for a date typed as text.
_DATE_TEXT_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


def _new_sheet() -> tuple[Workbook, object]:
    """A fresh workbook whose only sheet has the bold header row."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Leverdata"
    sheet.append(TEMPLATE_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    return workbook, sheet


def _finish_sheet(workbook: Workbook, sheet) -> bytes:
    """Widen the columns, format the date cells and serialise the workbook."""
    for index, column in enumerate(TEMPLATE_COLUMNS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = max(len(column) + 2, 18)

    # Columns C and D hold the dates; show them the Belgian way.
    for row in sheet.iter_rows(min_row=2, min_col=3, max_col=4):
        for cell in row:
            cell.number_format = _DATE_NUMBER_FORMAT

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _active_festival_rows(db: Session):
    """Every active festival with its season name and saved dates (if any),
    ordered season → start date → name. Outer join so festivals without a
    Leverdatum row still get a line.
    """
    return db.execute(
        select(Season.name, Festival.name, KarTrackerLeverdatum.delivery_date, KarTrackerLeverdatum.pickup_date)
        .join(Season, Season.id == Festival.season_id)
        .outerjoin(KarTrackerLeverdatum, KarTrackerLeverdatum.festival_id == Festival.id)
        .where(Festival.active.is_(True))
        .order_by(Season.name, Festival.start_date, Festival.name)
    ).all()


def build_leverdatum_template_xlsx(db: Session) -> bytes:
    """The downloadable template: header plus one row per active festival
    with empty dates, so the user only has to type the dates. Safe to
    re-upload unedited, since rows without dates are skipped.
    """
    workbook, sheet = _new_sheet()
    for season_name, festival_name, _delivery, _pickup in _active_festival_rows(db):
        sheet.append([season_name, festival_name, None, None])
    return _finish_sheet(workbook, sheet)


def export_leverdata_to_xlsx(db: Session) -> bytes:
    """Every active festival with its saved dates, same columns as the template."""
    workbook, sheet = _new_sheet()
    for season_name, festival_name, delivery_date, pickup_date in _active_festival_rows(db):
        sheet.append([season_name, festival_name, delivery_date, pickup_date])
    return _finish_sheet(workbook, sheet)


def _cell_text(value: object) -> str | None:
    """Empty/blank cells mean "not set"; anything else is stringified and trimmed."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_date_cell(value: object, column: str) -> date | None:
    """A real Excel date cell, or text in one of the accepted formats; blank = no date."""
    # openpyxl hands back datetime for date-formatted cells (datetime is a date subclass, check it first).
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = _cell_text(value)
    if text is None:
        return None
    for date_format in _DATE_TEXT_FORMATS:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    raise ValueError(f'{column} "{text}" is not a valid date (use DD/MM/YYYY)')


def _resolve_festival(db: Session, season_name: str | None, festival_name: str | None) -> Festival:
    """The active festival with this name in the season with this name (both case-insensitive)."""
    if season_name is None:
        raise ValueError("season_name is required")
    if festival_name is None:
        raise ValueError("festival_name is required")

    season = db.scalar(select(Season).where(func.lower(Season.name) == season_name.lower()))
    if season is None:
        raise ValueError(f'Season "{season_name}" not found')

    festival = db.scalar(
        select(Festival).where(
            Festival.season_id == season.id,
            func.lower(Festival.name) == festival_name.lower(),
            Festival.active.is_(True),
        )
    )
    if festival is None:
        raise ValueError(f'Active festival "{festival_name}" not found in season "{season.name}"')
    return festival


def import_leverdata_from_xlsx(db: Session, file_bytes: bytes) -> list[LeverdatumImportRowResult]:
    """Apply every row of an uploaded workbook's active sheet, one result per
    row. Row numbers match the spreadsheet (header is row 1, data from row 2).
    """
    workbook = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)

    header_row = next(rows, None)
    if header_row is None:
        return []

    column_index = {str(name).strip().lower(): index for index, name in enumerate(header_row) if name is not None}

    def cell(row: tuple, key: str) -> object:
        index = column_index.get(key)
        return row[index] if index is not None and index < len(row) else None

    results: list[LeverdatumImportRowResult] = []
    # Festivals already handled earlier in this file — a second row for the
    # same festival is an error rather than silently overwriting the first.
    seen_festival_ids: set[int] = set()

    for row_number, row in enumerate(rows, start=2):
        if row is None or all(value is None for value in row):
            continue  # a blank trailing row — nothing to report

        festival_name = _cell_text(cell(row, "festival_name"))
        savepoint = db.begin_nested()
        try:
            festival = _resolve_festival(db, _cell_text(cell(row, "season_name")), festival_name)
            festival_name = festival.name  # report the stored spelling

            if festival.id in seen_festival_ids:
                raise ValueError("This festival appears more than once in the file")
            seen_festival_ids.add(festival.id)

            delivery_date = _parse_date_cell(cell(row, "delivery_date"), "delivery_date")
            pickup_date = _parse_date_cell(cell(row, "pickup_date"), "pickup_date")

            # No dates at all: leave whatever is saved untouched.
            if delivery_date is None and pickup_date is None:
                savepoint.rollback()
                results.append(
                    LeverdatumImportRowResult(
                        row_number=row_number, festival_name=festival_name, outcome="skipped", detail=None
                    )
                )
                continue

            # Same rule as the Delivery Dates screen.
            if delivery_date and pickup_date and pickup_date < delivery_date:
                raise ValueError("The pick-up date can't be before the delivery date")

            existing = db.scalar(select(KarTrackerLeverdatum).where(KarTrackerLeverdatum.festival_id == festival.id))
            if existing is not None:
                # Already registered: overwrite in place, never a second line.
                existing.delivery_date = delivery_date
                existing.pickup_date = pickup_date
                outcome = "updated"
            else:
                db.add(
                    KarTrackerLeverdatum(
                        festival_id=festival.id, delivery_date=delivery_date, pickup_date=pickup_date
                    )
                )
                outcome = "created"

            db.flush()
            savepoint.commit()
            results.append(
                LeverdatumImportRowResult(
                    row_number=row_number, festival_name=festival_name, outcome=outcome, detail=None
                )
            )
        except (ValueError, IntegrityError) as error:
            savepoint.rollback()
            detail = str(error) if isinstance(error, ValueError) else "This row conflicts with existing data"
            results.append(
                LeverdatumImportRowResult(
                    row_number=row_number, festival_name=festival_name, outcome="error", detail=detail
                )
            )

    db.commit()
    return results
