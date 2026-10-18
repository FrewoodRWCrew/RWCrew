# Bulk XLSX import/export for Seasons (MasterData's "Data Upload/Download"
# screen): the template, the upload and the export, in the same columns:
# "id", the season's name and "periode_open" (whether Altsien Kernleden may
# still change their choices for it, see Altsien Select's season lock).
#
# Same rules as every MasterData import (see xlsx_common.py): a row with an
# "id" updates that season, a row without one creates a new season, and a
# name another season already has is a row error. A missing periode_open
# column leaves an existing season's value alone; a new one is then closed,
# the screen's own default.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.season import Season
from app.modules.module_9.xlsx_common import (
    ID_COLUMN,
    ImportOutcome,
    RowError,
    UploadedRow,
    build_xlsx,
    find_by_id,
    parse_yes_no,
    read_rows,
    run_import,
)
from app.schemas.masterdata import SeasonImportRowResult

TEMPLATE_COLUMNS = [ID_COLUMN, "name", "periode_open"]
SHEET_TITLE = "Years"


def build_season_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row. Deliberately no
    example row — re-uploaded unedited, it would create a real season."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, min_width=24)


def import_seasons_from_xlsx(db: Session, file_bytes: bytes) -> list[SeasonImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        name = row.text("name")
        try:
            if name is None:
                raise ValueError("name is required")
            season = find_by_id(db, Season, row)

            # The name must stay unique: another season with it is an error.
            clash = db.scalar(select(Season).where(Season.name == name))
            if clash is not None and clash is not season:
                raise ValueError("A year with this name already exists")

            if season is None:
                periode_open = parse_yes_no("periode_open", row.value("periode_open"), default=False)
                db.add(Season(name=name, periode_open=periode_open))
                return name, "created"

            season.name = name
            if row.has("periode_open"):
                season.periode_open = parse_yes_no("periode_open", row.value("periode_open"), default=False)
            return name, "updated"
        except ValueError as error:
            raise RowError(str(error), name) from None

    return run_import(
        read_rows(file_bytes),
        db,
        apply_row,
        lambda row_number, key, outcome, detail: SeasonImportRowResult(
            row_number=row_number, name=key, outcome=outcome, detail=detail
        ),
    )


def export_seasons_to_xlsx(db: Session) -> bytes:
    """Every season as a workbook, in the template's columns."""
    seasons = db.scalars(select(Season).order_by(Season.name)).all()
    return build_xlsx(
        SHEET_TITLE,
        TEMPLATE_COLUMNS,
        [[season.id, season.name, "yes" if season.periode_open else "no"] for season in seasons],
        min_width=24,
    )
