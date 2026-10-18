# Bulk XLSX import/export for the Team Task lookup (MasterData's "Data
# Upload/Download" screen): the template, the upload and the export. The
# work is done by the shared one-name lookup helpers in xlsx_common.py: a
# row with an "id" renames that record, a row without one adds a new
# team task, and a name that's already taken is a row error.

from sqlalchemy.orm import Session

from app.db.models.team_task import TeamTask
from app.modules.module_9.xlsx_common import import_lookup_xlsx, lookup_export_xlsx, lookup_template_xlsx
from app.schemas.masterdata import TeamTaskImportRowResult

# The sheet's name and the column holding the team task's name.
SHEET_TITLE = "TeamTasks"
NAME_COLUMN = "team_tasks"


def build_team_task_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row ("id" + name)."""
    return lookup_template_xlsx(SHEET_TITLE, NAME_COLUMN)


def import_team_tasks_from_xlsx(db: Session, file_bytes: bytes) -> list[TeamTaskImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""
    return import_lookup_xlsx(
        db,
        file_bytes,
        model=TeamTask,
        field="team_tasks",
        column=NAME_COLUMN,
        duplicate_message="A team task with this name already exists",
        make_result=lambda row_number, key, outcome, detail: TeamTaskImportRowResult(
            row_number=row_number, team_tasks=key, outcome=outcome, detail=detail
        ),
    )


def export_team_tasks_to_xlsx(db: Session) -> bytes:
    """Every team task as a workbook, in the template's columns."""
    return lookup_export_xlsx(db, model=TeamTask, field="team_tasks", title=SHEET_TITLE, column=NAME_COLUMN)
