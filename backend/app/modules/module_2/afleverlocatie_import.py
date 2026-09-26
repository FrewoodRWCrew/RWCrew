# Bulk XLSX import/export for the Afleverlocatie master data: building the
# downloadable template, applying an uploaded workbook row by row, and
# exporting the full dataset back out. Mirrors kar_import.py's own shape.
#
# Import is best-effort: every row is validated and applied independently
# inside its own SAVEPOINT (db.begin_nested()), so one bad row rolls back
# only itself instead of aborting the whole batch. A row whose name
# already exists is REJECTED as an error rather than upserted — same rule
# as the Karren import. Unlike Altsien Kernlid, Zone and Distributiepunt
# are required on every row, since an Afleverlocatie always belongs to
# exactly one of each.

import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.user import User
from app.schemas.kartracker import AfleverlocatieImportRowResult

# The workbook's columns, in order — also the header row of the
# downloadable template. Zone/Distributiepunt are given by
# name and Altsien Kernlid by the user's email (not id), since this is filled in by a person editing a
# spreadsheet, matched against their respective tables on import.
TEMPLATE_COLUMNS = [
    "name",
    "description",
    "zone_name",
    "distributiepunt_name",
    "latitude",
    "longitude",
    "terrein_positie",
    "altsien_kernlid_email",
    "active",
]

# Accepted spellings for the optional "active" column, compared lowercase.
_TRUE_VALUES = {"true", "yes", "ja", "1", "y"}
_FALSE_VALUES = {"false", "no", "nee", "0", "n"}


def build_afleverlocatie_template_xlsx() -> bytes:
    """The downloadable XLSX template: just a bold header row. Deliberately
    no example data row — since a re-uploaded, unedited row would silently
    create a real delivery location (import rejects duplicates rather than
    upserting, so it wouldn't even get caught as "already exists" the
    first time).
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Afleverlocaties"

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


def _parse_active_cell(value: object) -> bool:
    """A blank cell means active (the default); otherwise it must be a recognisable yes/no."""
    if isinstance(value, bool):
        return value
    text = _cell_text(value)
    if text is None:
        return True
    lowered = text.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ValueError(f'active "{text}" is not a valid yes/no value')


def _resolve_zone_id(db: Session, zone_name: str | None) -> int:
    if zone_name is None:
        raise ValueError("zone_name is required")
    zone = db.scalar(select(KarTrackerZone).where(func.lower(KarTrackerZone.name) == zone_name.lower()))
    if zone is None:
        raise ValueError(f'Zone "{zone_name}" not found')
    return zone.id


def _resolve_distributiepunt_id(db: Session, distributiepunt_name: str | None) -> int:
    if distributiepunt_name is None:
        raise ValueError("distributiepunt_name is required")
    distributiepunt = db.scalar(
        select(KarTrackerDistributiepunt).where(
            func.lower(KarTrackerDistributiepunt.name) == distributiepunt_name.lower()
        )
    )
    if distributiepunt is None:
        raise ValueError(f'Distributiepunt "{distributiepunt_name}" not found')
    return distributiepunt.id


def _resolve_altsien_kernlid_id(db: Session, email: str | None) -> int | None:
    """A blank cell means "no kernlid assigned". An email that doesn't match
    a user flagged Altsien Kernlid is an error rather than silently ignored.
    """
    if email is None:
        return None
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower(), User.is_altsien_kernlid.is_(True)))
    if user is None:
        raise ValueError(f'Altsien Kernlid "{email}" not found')
    return user.id


def import_afleverlocaties_from_xlsx(db: Session, file_bytes: bytes) -> list[AfleverlocatieImportRowResult]:
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

    results: list[AfleverlocatieImportRowResult] = []

    for row_number, row in enumerate(rows, start=2):
        if row is None or all(value is None for value in row):
            continue  # a blank trailing row — nothing to report

        name = _cell_text(cell(row, "name"))
        savepoint = db.begin_nested()
        try:
            if name is None:
                raise ValueError("name is required")

            existing = db.scalar(select(KarTrackerAfleverlocatie).where(KarTrackerAfleverlocatie.name == name))
            if existing is not None:
                raise ValueError("A delivery location with this name already exists")

            new_afleverlocatie = KarTrackerAfleverlocatie(
                name=name,
                description=_cell_text(cell(row, "description")),
                zone_id=_resolve_zone_id(db, _cell_text(cell(row, "zone_name"))),
                distributiepunt_id=_resolve_distributiepunt_id(db, _cell_text(cell(row, "distributiepunt_name"))),
                latitude=float(cell(row, "latitude")) if _cell_text(cell(row, "latitude")) else None,
                longitude=float(cell(row, "longitude")) if _cell_text(cell(row, "longitude")) else None,
                terrein_positie=_cell_text(cell(row, "terrein_positie")),
                altsien_kernlid_id=_resolve_altsien_kernlid_id(db, _cell_text(cell(row, "altsien_kernlid_email"))),
                active=_parse_active_cell(cell(row, "active")),
            )
            db.add(new_afleverlocatie)

            savepoint.commit()
            results.append(
                AfleverlocatieImportRowResult(row_number=row_number, name=name, outcome="created", detail=None)
            )
        except (ValueError, IntegrityError) as error:
            savepoint.rollback()
            detail = str(error) if isinstance(error, ValueError) else "This row conflicts with existing data"
            results.append(
                AfleverlocatieImportRowResult(row_number=row_number, name=name, outcome="error", detail=detail)
            )

    db.commit()
    return results


def export_afleverlocaties_to_xlsx(db: Session) -> bytes:
    """The full Afleverlocatie dataset as an XLSX workbook, same columns
    as the import template, with Zone/Distributiepunt/Altsien Kernlid
    resolved back to names.
    """
    zones = {zone.id: zone.name for zone in db.scalars(select(KarTrackerZone)).all()}
    distributiepunten = {dp.id: dp.name for dp in db.scalars(select(KarTrackerDistributiepunt)).all()}
    kernlid_emails = {user.id: user.email for user in db.scalars(select(User)).all()}

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Afleverlocaties"
    sheet.append(TEMPLATE_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    afleverlocaties = db.scalars(select(KarTrackerAfleverlocatie).order_by(KarTrackerAfleverlocatie.name)).all()
    for afleverlocatie in afleverlocaties:
        sheet.append(
            [
                afleverlocatie.name,
                afleverlocatie.description,
                zones.get(afleverlocatie.zone_id, ""),
                distributiepunten.get(afleverlocatie.distributiepunt_id, ""),
                afleverlocatie.latitude,
                afleverlocatie.longitude,
                afleverlocatie.terrein_positie,
                kernlid_emails.get(afleverlocatie.altsien_kernlid_id),
                "yes" if afleverlocatie.active else "no",
            ]
        )
    for index, column in enumerate(TEMPLATE_COLUMNS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = max(len(column) + 2, 18)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
