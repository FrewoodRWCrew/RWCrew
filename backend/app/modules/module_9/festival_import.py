# Bulk XLSX import/export for Festivals (MasterData's "Data Upload/Download"
# screen): the template, the upload and the export, in the same columns. The
# season is given by name, resolved ignoring case.
#
# Same rules as every MasterData import (see xlsx_common.py): a row with an
# "id" updates that festival, a row without one creates a new festival.
# Festival names aren't unique (the screen allows two with the same name),
# so there's no "already exists" check. On an update, a column missing from
# the sheet leaves that field alone; a new festival needs name, both dates
# and the season.

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.season import Season
from app.modules.module_9.xlsx_common import (
    ID_COLUMN,
    ImportOutcome,
    RowError,
    UploadedRow,
    build_xlsx,
    cell_text,
    find_by_id,
    parse_yes_no,
    read_rows,
    run_import,
)
from app.schemas.masterdata import FestivalImportRowResult

TEMPLATE_COLUMNS = [ID_COLUMN, "name", "start_date", "end_date", "season_name", "active"]
SHEET_TITLE = "Festivals"

# Columns a new festival can't do without.
_REQUIRED_ON_CREATE = ("name", "start_date", "end_date", "season_name")


def build_festival_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS)


def _parse_date_cell(column: str, value: object) -> date:
    """A date cell (an Excel date, or text as YYYY-MM-DD) — required."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = cell_text(value)
    if text is None:
        raise ValueError(f"{column} is required")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f'{column} "{text}" is not a date (use YYYY-MM-DD)') from None


def _resolve_season_id(db: Session, season_name: str | None) -> int:
    if season_name is None:
        raise ValueError("season_name is required")
    season = db.scalar(select(Season).where(Season.name.ilike(season_name)))
    if season is None:
        raise ValueError(f'Year "{season_name}" not found')
    return season.id


def import_festivals_from_xlsx(db: Session, file_bytes: bytes) -> list[FestivalImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        name = row.text("name")
        try:
            festival = find_by_id(db, Festival, row)
            if festival is None:
                for column in _REQUIRED_ON_CREATE:
                    if row.text(column) is None and not isinstance(row.value(column), date):
                        raise ValueError(f"{column} is required")

            # Each column's model field and parser — only the columns the
            # sheet has (on create, the required ones are all there).
            parsers = {
                "name": ("name", lambda value: _required_text("name", value)),
                "start_date": ("start_date", lambda value: _parse_date_cell("start_date", value)),
                "end_date": ("end_date", lambda value: _parse_date_cell("end_date", value)),
                "season_name": ("season_id", lambda value: _resolve_season_id(db, cell_text(value))),
                "active": ("active", lambda value: parse_yes_no("active", value, default=True)),
            }
            fields = {field: parse(row.value(column)) for column, (field, parse) in parsers.items() if row.has(column)}

            if festival is None:
                db.add(Festival(**fields))
                return name, "created"
            for field, value in fields.items():
                setattr(festival, field, value)
            return name or festival.name, "updated"
        except ValueError as error:
            raise RowError(str(error), name) from None

    return run_import(
        read_rows(file_bytes),
        db,
        apply_row,
        lambda row_number, key, outcome, detail: FestivalImportRowResult(
            row_number=row_number, name=key, outcome=outcome, detail=detail
        ),
    )


def _required_text(column: str, value: object) -> str:
    """A text cell that may not be blank."""
    text = cell_text(value)
    if text is None:
        raise ValueError(f"{column} is required")
    return text


def export_festivals_to_xlsx(db: Session) -> bytes:
    """Every festival as a workbook, with its season resolved back to a name."""
    seasons = {season.id: season.name for season in db.scalars(select(Season)).all()}
    festivals = db.scalars(select(Festival).order_by(Festival.name)).all()
    return build_xlsx(
        SHEET_TITLE,
        TEMPLATE_COLUMNS,
        [
            [
                festival.id,
                festival.name,
                festival.start_date,
                festival.end_date,
                seasons.get(festival.season_id, ""),
                "yes" if festival.active else "no",
            ]
            for festival in festivals
        ],
    )
