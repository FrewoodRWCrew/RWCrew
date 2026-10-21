# Bulk XLSX import/export for KarManagement's fleet registry: building the
# downloadable template, applying an uploaded workbook row by row, and
# exporting the full dataset back out. Kept free of FastAPI/routing
# concerns (mirrors module_1/tag_import.py), so it's easy to unit test on
# its own.
#
# Import is best-effort: every row is validated and applied independently
# inside its own SAVEPOINT (db.begin_nested()), so one bad row rolls back
# only itself instead of aborting the whole batch — the caller always gets
# back one result per row (created/updated/error), never a partial exception.
# A row whose kar_nummer already exists UPDATES that kar: every filled-in
# cell overwrites the saved value, while an empty cell keeps it (clearing a
# value stays a job for the KarManagement screen). So an edited export can
# be uploaded again as-is.

import io
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.timezone import to_belgian
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.product import Product
from app.db.models.team import Team
from app.schemas.kartracker import KarImportRowResult

# The workbook's columns, in order — also the header row of the
# downloadable template. Status/team/transport-type are given by name (not
# id), since this is filled in by a person editing a spreadsheet, matched
# against their respective lookup tables on import.
TEMPLATE_COLUMNS = [
    "kar_nummer",
    "status_name",
    "team_name",
    "transport_type_name",
    "last_latitude",
    "last_longitude",
    "last_recorded_at",
]

def build_kar_template_xlsx() -> bytes:
    """The downloadable XLSX template: just a bold header row. Deliberately
    no example data row — a re-uploaded, unedited example row would silently
    create (or update) a real kar.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Karren"

    sheet.append(TEMPLATE_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for index, column in enumerate(TEMPLATE_COLUMNS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = max(len(column) + 2, 18)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _cell_text(value: object) -> str | None:
    """Empty/blank cells mean "not set"; anything else is stringified and trimmed."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime_cell(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).strip())


def _float_or_none(value: object) -> float | None:
    """A coordinate cell: empty means "not given", anything else must be a number."""
    return float(value) if _cell_text(value) else None


def _resolve_status_id(db: Session, status_name: str | None) -> int:
    if status_name is None:
        raise ValueError("status_name is required")
    kar_status = db.scalar(select(KarTrackerKarStatus).where(KarTrackerKarStatus.name.ilike(status_name)))
    if kar_status is None:
        raise ValueError(f'Kar status "{status_name}" not found')
    return kar_status.id


def _resolve_transport_type_id(db: Session, transport_type_name: str | None) -> int:
    if transport_type_name is None:
        raise ValueError("transport_type_name is required")
    product = db.scalar(select(Product).where(Product.name.ilike(transport_type_name)))
    if product is None:
        raise ValueError(f'Transport type "{transport_type_name}" not found')
    return product.id


def _resolve_team_id(db: Session, team_name: str | None) -> int | None:
    if team_name is None:
        return None
    team = db.scalar(select(Team).where(Team.name.ilike(team_name)))
    if team is None:
        raise ValueError(f'Team "{team_name}" not found')
    return team.id


def import_karren_from_xlsx(db: Session, file_bytes: bytes) -> list[KarImportRowResult]:
    """Apply every row of an uploaded XLSX workbook's active sheet,
    returning one result per row. Row numbers match the actual
    spreadsheet row (header is row 1, so data starts at row 2) — matching
    what a person sees if they open the file themselves.
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

    results: list[KarImportRowResult] = []
    # Kar numbers already handled in this file, so a repeated one is caught
    # instead of silently updating the same kar twice.
    seen_kar_nummers: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        if row is None or all(value is None for value in row):
            continue  # a blank trailing row — nothing to report

        kar_nummer = _cell_text(cell(row, "kar_nummer"))
        savepoint = db.begin_nested()
        try:
            if kar_nummer is None:
                raise ValueError("kar_nummer is required")
            if kar_nummer in seen_kar_nummers:
                raise ValueError("This kar number appears more than once in the file")
            seen_kar_nummers.add(kar_nummer)

            status_name = _cell_text(cell(row, "status_name"))
            team_name = _cell_text(cell(row, "team_name"))
            transport_type_name = _cell_text(cell(row, "transport_type_name"))
            latitude = _float_or_none(cell(row, "last_latitude"))
            longitude = _float_or_none(cell(row, "last_longitude"))
            recorded_at = _parse_datetime_cell(cell(row, "last_recorded_at"))

            existing = db.scalar(select(KarTrackerKar).where(KarTrackerKar.kar_nummer == kar_nummer))
            if existing is not None:
                # Update: only the filled-in cells overwrite, empty ones keep the saved value.
                if status_name is not None:
                    existing.status_id = _resolve_status_id(db, status_name)
                if team_name is not None:
                    existing.team_id = _resolve_team_id(db, team_name)
                if transport_type_name is not None:
                    existing.transport_type_id = _resolve_transport_type_id(db, transport_type_name)
                if latitude is not None:
                    existing.last_latitude = latitude
                if longitude is not None:
                    existing.last_longitude = longitude
                if recorded_at is not None:
                    existing.last_recorded_at = recorded_at
                db.flush()
                outcome = "updated"
            else:
                # New kar: status and transport type are required.
                db.add(
                    KarTrackerKar(
                        kar_nummer=kar_nummer,
                        status_id=_resolve_status_id(db, status_name),
                        team_id=_resolve_team_id(db, team_name),
                        transport_type_id=_resolve_transport_type_id(db, transport_type_name),
                        last_latitude=latitude,
                        last_longitude=longitude,
                        last_recorded_at=recorded_at,
                    )
                )
                outcome = "created"

            savepoint.commit()
            results.append(KarImportRowResult(row_number=row_number, kar_nummer=kar_nummer, outcome=outcome, detail=None))
        except (ValueError, IntegrityError) as error:
            savepoint.rollback()
            detail = str(error) if isinstance(error, ValueError) else "This row conflicts with existing data"
            results.append(
                KarImportRowResult(row_number=row_number, kar_nummer=kar_nummer, outcome="error", detail=detail)
            )

    db.commit()
    return results


def export_karren_to_xlsx(db: Session) -> bytes:
    """The full KarTracker dataset as a two-sheet workbook: every kar
    (with its status/team/transport-type resolved to names, matching the
    import template's own columns) plus every kar status.
    """
    kar_statuses = {status.id: status.name for status in db.scalars(select(KarTrackerKarStatus)).all()}
    products = {product.id: product.name for product in db.scalars(select(Product)).all()}
    teams = {team.id: team.name for team in db.scalars(select(Team)).all()}

    workbook = Workbook()

    karren_sheet = workbook.active
    karren_sheet.title = "Karren"
    karren_sheet.append(TEMPLATE_COLUMNS)
    for cell in karren_sheet[1]:
        cell.font = Font(bold=True)

    karren = db.scalars(select(KarTrackerKar).order_by(KarTrackerKar.kar_nummer)).all()
    for kar in karren:
        karren_sheet.append(
            [
                kar.kar_nummer,
                kar_statuses.get(kar.status_id, ""),
                teams.get(kar.team_id, "") if kar.team_id is not None else "",
                products.get(kar.transport_type_id, ""),
                kar.last_latitude,
                kar.last_longitude,
                # Excel has no timezones: write the Belgian wall-clock time.
                to_belgian(kar.last_recorded_at).replace(tzinfo=None) if kar.last_recorded_at else None,
            ]
        )
    for index, column in enumerate(TEMPLATE_COLUMNS, start=1):
        karren_sheet.column_dimensions[get_column_letter(index)].width = max(len(column) + 2, 18)

    statuses_sheet = workbook.create_sheet("KarStatussen")
    statuses_sheet.append(["id", "name"])
    for cell in statuses_sheet[1]:
        cell.font = Font(bold=True)
    for status_id, status_name in sorted(kar_statuses.items(), key=lambda item: item[1]):
        statuses_sheet.append([status_id, status_name])
    statuses_sheet.column_dimensions["A"].width = 8
    statuses_sheet.column_dimensions["B"].width = 24

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
