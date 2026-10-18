# Bulk XLSX import/export for Teams (MasterData's "Data Upload/Download"
# screen): the template, the upload and the export, in the same columns.
# Location and delivery method are given by name, resolved ignoring case.
#
# Scope note: this tile only covers Team's own fields (name, location,
# delivery method, description, active). Its links have tiles of their own:
# tasks per team (team_team_task_import.py), Kernleden per team
# (team_kernlid_import.py), festivals per team (team_festival_import.py) and
# Ploegverantwoordelijken (team_responsible_import.py).
#
# Same rules as every MasterData import (see xlsx_common.py): a row with an
# "id" updates that team, a row without one creates a new team, and a name
# another team already has is a row error (Team.name is unique). On an
# update, a column missing from the sheet leaves that field alone.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.delivery_method import DeliveryMethod
from app.db.models.team import Team
from app.db.models.team_location import TeamLocation
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
from app.schemas.masterdata import TeamImportRowResult

TEMPLATE_COLUMNS = [ID_COLUMN, "name", "location_name", "delivery_method_name", "description", "active"]
SHEET_TITLE = "Teams"


def build_team_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row. Deliberately no
    example row — re-uploaded unedited, it would create a real team."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS)


def _resolve_location_id(db: Session, location_name: str | None) -> int | None:
    if location_name is None:
        return None
    location = db.scalar(select(TeamLocation).where(TeamLocation.location.ilike(location_name)))
    if location is None:
        raise ValueError(f'Team location "{location_name}" not found')
    return location.id


def _resolve_delivery_method_id(db: Session, delivery_method_name: str | None) -> int | None:
    if delivery_method_name is None:
        return None
    delivery_method = db.scalar(
        select(DeliveryMethod).where(DeliveryMethod.delivery_method.ilike(delivery_method_name))
    )
    if delivery_method is None:
        raise ValueError(f'Delivery method "{delivery_method_name}" not found')
    return delivery_method.id


def import_teams_from_xlsx(db: Session, file_bytes: bytes) -> list[TeamImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        name = row.text("name")
        try:
            team = find_by_id(db, Team, row)
            if (team is None or row.has("name")) and name is None:
                raise ValueError("name is required")

            # The name must stay unique: another team with it is an error.
            if name is not None:
                clash = db.scalar(select(Team).where(Team.name == name))
                if clash is not None and clash is not team:
                    raise ValueError("A team with this name already exists")

            # Each column's model field and parser — only the columns the sheet has.
            parsers = {
                "name": ("name", cell_text),
                "location_name": ("location_id", lambda value: _resolve_location_id(db, cell_text(value))),
                "delivery_method_name": (
                    "delivery_method_id",
                    lambda value: _resolve_delivery_method_id(db, cell_text(value)),
                ),
                "description": ("description", cell_text),
                "active": ("active", lambda value: parse_yes_no("active", value, default=True)),
            }
            fields = {field: parse(row.value(column)) for column, (field, parse) in parsers.items() if row.has(column)}

            if team is None:
                db.add(Team(**fields))
                return name, "created"
            for field, value in fields.items():
                setattr(team, field, value)
            return name or team.name, "updated"
        except ValueError as error:
            raise RowError(str(error), name) from None

    return run_import(
        read_rows(file_bytes),
        db,
        apply_row,
        lambda row_number, key, outcome, detail: TeamImportRowResult(
            row_number=row_number, name=key, outcome=outcome, detail=detail
        ),
    )


def export_teams_to_xlsx(db: Session) -> bytes:
    """Every team's own fields as a workbook, with its location/delivery
    method resolved back to names to match the template's columns."""
    locations = {location.id: location.location for location in db.scalars(select(TeamLocation)).all()}
    delivery_methods = {method.id: method.delivery_method for method in db.scalars(select(DeliveryMethod)).all()}

    teams = db.scalars(select(Team).order_by(Team.name)).all()
    return build_xlsx(
        SHEET_TITLE,
        TEMPLATE_COLUMNS,
        [
            [
                team.id,
                team.name,
                locations.get(team.location_id, "") if team.location_id is not None else "",
                delivery_methods.get(team.delivery_method_id, "") if team.delivery_method_id is not None else "",
                team.description,
                "yes" if team.active else "no",
            ]
            for team in teams
        ],
    )
