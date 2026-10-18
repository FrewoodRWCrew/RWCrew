# Bulk XLSX import/export for Ploegverantwoordelijken (MasterData_team_responsible,
# MasterData's "Data Upload/Download" screen): the people responsible for a
# team in a season (not RWCrew users). Season and team are given by name,
# matched ignoring case.
#
# Same rules as every MasterData import (see xlsx_common.py): a row with an
# "id" updates that person, a row without one adds a new person. The values
# are checked with the screen's own request model (name, valid email and
# phone required) and written through team_responsible_service.py, like the
# Teams > Ploegverantwoordelijken screen and Altsien Select's wizard step. On
# an update, a column missing from the sheet keeps the person's current value.

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_responsible import TeamResponsible
from app.modules.module_9.team_link_common import link_key, resolve_season, resolve_team
from app.modules.module_9.team_responsible_service import apply_team_responsible_fields, reopen_step_if_no_responsibles
from app.modules.module_9.xlsx_common import (
    ID_COLUMN,
    ImportOutcome,
    RowError,
    UploadedRow,
    build_xlsx,
    find_by_id,
    read_rows,
    run_import,
)
from app.schemas.masterdata import TeamLinkImportRowResult, TeamResponsibleCreateRequest

TEMPLATE_COLUMNS = [ID_COLUMN, "season_name", "team_name", "name", "email", "phone", "comments"]
SHEET_TITLE = "Ploegverantwoordelijken"

# The person's own fields: sheet column = request field.
_PERSON_FIELDS = ("name", "email", "phone", "comments")


def build_team_responsible_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS)


def _first_validation_message(error: ValidationError) -> str:
    """One readable line from pydantic's error, e.g. "email: value is not a valid email address"."""
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"])
    return f"{field}: {first['msg']}"


def import_team_responsibles_from_xlsx(db: Session, file_bytes: bytes) -> list[TeamLinkImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        key = link_key(row.text("team_name"), row.text("name"))
        try:
            person = find_by_id(db, TeamResponsible, row)

            # Start from the person's current values (on update), then take
            # every column the sheet has.
            season_id = person.season_id if person else None
            team_id = person.team_id if person else None
            values = {field: getattr(person, field) for field in _PERSON_FIELDS} if person else {}
            if person is None or row.has("season_name"):
                season_id = resolve_season(db, row.text("season_name")).id
            if person is None or row.has("team_name"):
                team_id = resolve_team(db, row.text("team_name")).id
            for field in _PERSON_FIELDS:
                if person is None or row.has(field):
                    values[field] = row.text(field)

            # The screen's own checks (required fields, valid email, lengths).
            try:
                payload = TeamResponsibleCreateRequest(season_id=season_id, team_id=team_id, **values)
            except ValidationError as error:
                raise ValueError(_first_validation_message(error)) from None

            old_place = (person.season_id, person.team_id) if person else None
            target = person or TeamResponsible()
            target.season_id = payload.season_id
            target.team_id = payload.team_id
            apply_team_responsible_fields(
                target, name=payload.name, email=str(payload.email), phone=payload.phone, comments=payload.comments
            )

            team_name = db.get(Team, payload.team_id).name
            if person is None:
                db.add(target)
                return link_key(team_name, payload.name), "created"
            # Moved to another team/season: re-check the wizard step it left.
            if old_place != (payload.season_id, payload.team_id):
                reopen_step_if_no_responsibles(db, *old_place)
            return link_key(team_name, payload.name), "updated"
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


def export_team_responsibles_to_xlsx(db: Session) -> bytes:
    """Every Ploegverantwoordelijke as a workbook, sorted by season, team, name."""
    rows = db.execute(
        select(
            TeamResponsible.id,
            Season.name,
            Team.name,
            TeamResponsible.name,
            TeamResponsible.email,
            TeamResponsible.phone,
            TeamResponsible.comments,
        )
        .join(Season, Season.id == TeamResponsible.season_id)
        .join(Team, Team.id == TeamResponsible.team_id)
        .order_by(Season.name, Team.name, TeamResponsible.name)
    ).all()
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS, [list(row) for row in rows])
