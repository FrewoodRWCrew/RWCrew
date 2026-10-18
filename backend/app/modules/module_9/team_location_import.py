# Bulk XLSX import/export for the Team Location lookup (MasterData's "Data
# Upload/Download" screen): the template, the upload and the export. The
# work is done by the shared one-name lookup helpers in xlsx_common.py: a
# row with an "id" renames that record, a row without one adds a new
# team location, and a name that's already taken is a row error.

from sqlalchemy.orm import Session

from app.db.models.team_location import TeamLocation
from app.modules.module_9.xlsx_common import import_lookup_xlsx, lookup_export_xlsx, lookup_template_xlsx
from app.schemas.masterdata import TeamLocationImportRowResult

# The sheet's name and the column holding the team location's name.
SHEET_TITLE = "TeamLocations"
NAME_COLUMN = "location"


def build_team_location_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row ("id" + name)."""
    return lookup_template_xlsx(SHEET_TITLE, NAME_COLUMN)


def import_team_locations_from_xlsx(db: Session, file_bytes: bytes) -> list[TeamLocationImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""
    return import_lookup_xlsx(
        db,
        file_bytes,
        model=TeamLocation,
        field="location",
        column=NAME_COLUMN,
        duplicate_message="A team location with this name already exists",
        make_result=lambda row_number, key, outcome, detail: TeamLocationImportRowResult(
            row_number=row_number, location=key, outcome=outcome, detail=detail
        ),
    )


def export_team_locations_to_xlsx(db: Session) -> bytes:
    """Every team location as a workbook, in the template's columns."""
    return lookup_export_xlsx(db, model=TeamLocation, field="location", title=SHEET_TITLE, column=NAME_COLUMN)
