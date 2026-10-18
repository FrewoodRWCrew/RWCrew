# Bulk XLSX import/export for "Kernleden per team" (MasterData_team_kernlid,
# MasterData's "Data Upload/Download" screen): one row per link, the team by
# name and the Kernlid by the email address of their RWCrew account (which
# must be marked as Altsien Kernlid, same rule as the Teams screen). Which
# teams a Kernlid is linked to decides what they see in Altsien Select.
#
# Upload only adds links: a link that already exists is reported
# "unchanged", never duplicated, and links are never removed here —
# removing stays on the Teams screen.

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.team import Team
from app.db.models.team_kernlid import TeamKernlid
from app.db.models.user import User
from app.modules.module_9.team_link_common import add_link, link_key, resolve_team
from app.modules.module_9.xlsx_common import ImportOutcome, RowError, UploadedRow, build_xlsx, read_rows, run_import
from app.schemas.masterdata import TeamLinkImportRowResult

TEMPLATE_COLUMNS = ["team_name", "user_email"]
SHEET_TITLE = "KernledenPerTeam"


def build_team_kernlid_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, min_width=28)


def _resolve_kernlid(db: Session, email: str | None) -> User:
    """The RWCrew user with this email (ignoring case), who must be an Altsien Kernlid."""
    if email is None:
        raise ValueError("user_email is required")
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None:
        raise ValueError(f'User "{email}" not found')
    if not user.is_altsien_kernlid:
        raise ValueError(f'User "{email}" is not an Altsien Kernlid')
    return user


def import_team_kernleden_from_xlsx(db: Session, file_bytes: bytes) -> list[TeamLinkImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        key = link_key(row.text("team_name"), row.text("user_email"))
        try:
            team = resolve_team(db, row.text("team_name"))
            user = _resolve_kernlid(db, row.text("user_email"))
            outcome = add_link(db, TeamKernlid, team_id=team.id, altsien_kernlid_id=user.id)
            return link_key(team.name, user.email), outcome
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


def export_team_kernleden_to_xlsx(db: Session) -> bytes:
    """Every team ↔ Kernlid link as a workbook, sorted by team then email."""
    rows = db.execute(
        select(Team.name, User.email)
        .join(TeamKernlid, TeamKernlid.team_id == Team.id)
        .join(User, User.id == TeamKernlid.altsien_kernlid_id)
        .order_by(Team.name, User.email)
    ).all()
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, [list(row) for row in rows], min_width=28)
