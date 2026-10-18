# Bulk XLSX import/export for "festivals per team" (MasterData_team_festival,
# MasterData's "Data Upload/Download" screen): one row per link — season,
# team and festival, all by name (matched ignoring case). This is the same
# data as step 1 of Altsien Select's Ploeg Wizard.
#
# Upload only adds links, with the wizard's rules: the festival must be an
# active festival of that season, a link that already exists is reported
# "unchanged", and a new link un-marks the wizard's "afleverlocaties" step
# (the delivery locations must be confirmed again for the new festival).
# Links are never removed here — removing stays in the wizard, which also
# cleans up the festival's delivery location.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival
from app.modules.module_8.service import clear_step
from app.modules.module_9.team_link_common import add_link, link_key, resolve_season, resolve_team
from app.modules.module_9.xlsx_common import ImportOutcome, RowError, UploadedRow, build_xlsx, read_rows, run_import
from app.schemas.masterdata import TeamLinkImportRowResult

TEMPLATE_COLUMNS = ["season_name", "team_name", "festival_name"]
SHEET_TITLE = "FestivalsPerTeam"


def build_team_festival_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, min_width=24)


def _resolve_festival(db: Session, season: Season, festival_name: str | None) -> Festival:
    """An active festival of this season with this name (ignoring case)."""
    if festival_name is None:
        raise ValueError("festival_name is required")
    festival = db.scalar(
        select(Festival).where(
            Festival.season_id == season.id,
            Festival.name.ilike(festival_name),
            Festival.active.is_(True),
        )
    )
    if festival is None:
        raise ValueError(f'No active festival "{festival_name}" in year "{season.name}"')
    return festival


def import_team_festivals_from_xlsx(db: Session, file_bytes: bytes) -> list[TeamLinkImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        key = link_key(row.text("season_name"), row.text("team_name"), row.text("festival_name"))
        try:
            season = resolve_season(db, row.text("season_name"))
            team = resolve_team(db, row.text("team_name"))
            festival = _resolve_festival(db, season, row.text("festival_name"))
            outcome = add_link(db, TeamFestival, season_id=season.id, team_id=team.id, festival_id=festival.id)
            if outcome == "created":
                clear_step(db, season.id, team.id, "afleverlocaties")
            return link_key(season.name, team.name, festival.name), outcome
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


def export_team_festivals_to_xlsx(db: Session) -> bytes:
    """Every team ↔ festival link as a workbook, sorted by season, team, festival."""
    rows = db.execute(
        select(Season.name, Team.name, Festival.name)
        .select_from(TeamFestival)
        .join(Season, Season.id == TeamFestival.season_id)
        .join(Team, Team.id == TeamFestival.team_id)
        .join(Festival, Festival.id == TeamFestival.festival_id)
        .order_by(Season.name, Team.name, Festival.name)
    ).all()
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, [list(row) for row in rows], min_width=24)
