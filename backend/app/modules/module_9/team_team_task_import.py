# Bulk XLSX import/export for "tasks per team" (MasterData_team_team_task,
# MasterData's "Data Upload/Download" screen): one row per link, the team and
# the task given by name (matched ignoring case).
#
# Upload only adds links: a link that already exists is reported
# "unchanged", never duplicated, and links are never removed here —
# removing stays on the Teams screen.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.team import Team
from app.db.models.team_task import TeamTask
from app.db.models.team_team_task import TeamTeamTask
from app.modules.module_9.team_link_common import add_link, link_key, resolve_team
from app.modules.module_9.xlsx_common import ImportOutcome, RowError, UploadedRow, build_xlsx, read_rows, run_import
from app.schemas.masterdata import TeamLinkImportRowResult

TEMPLATE_COLUMNS = ["team_name", "team_task"]
SHEET_TITLE = "TeamTasksPerTeam"


def build_team_team_task_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, min_width=24)


def _resolve_task(db: Session, task_name: str | None) -> TeamTask:
    if task_name is None:
        raise ValueError("team_task is required")
    task = db.scalar(select(TeamTask).where(TeamTask.team_tasks.ilike(task_name)))
    if task is None:
        raise ValueError(f'Team task "{task_name}" not found')
    return task


def import_team_team_tasks_from_xlsx(db: Session, file_bytes: bytes) -> list[TeamLinkImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        key = link_key(row.text("team_name"), row.text("team_task"))
        try:
            team = resolve_team(db, row.text("team_name"))
            task = _resolve_task(db, row.text("team_task"))
            outcome = add_link(db, TeamTeamTask, team_id=team.id, team_task_id=task.id)
            return link_key(team.name, task.team_tasks), outcome
        except ValueError as error:
            raise RowError(str(error), key) from None

    return run_import(
        read_rows(file_bytes),
        db,
        apply_row,
        lambda row_number, key, outcome, detail: TeamLinkImportRowResult(
            row_number=row_number, key=key, outcome=outcome, detail=detail
        ),
    )


def export_team_team_tasks_to_xlsx(db: Session) -> bytes:
    """Every team ↔ task link as a workbook, sorted by team then task."""
    rows = db.execute(
        select(Team.name, TeamTask.team_tasks)
        .join(TeamTeamTask, TeamTeamTask.team_id == Team.id)
        .join(TeamTask, TeamTask.id == TeamTeamTask.team_task_id)
        .order_by(Team.name, TeamTask.team_tasks)
    ).all()
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, [list(row) for row in rows], min_width=24)
