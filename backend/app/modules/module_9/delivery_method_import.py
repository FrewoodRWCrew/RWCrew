# Bulk XLSX import/export for the Delivery Method lookup (MasterData's "Data
# Upload/Download" screen): the template, the upload and the export. The
# work is done by the shared one-name lookup helpers in xlsx_common.py: a
# row with an "id" renames that record, a row without one adds a new
# delivery method, and a name that's already taken is a row error.

from sqlalchemy.orm import Session

from app.db.models.delivery_method import DeliveryMethod
from app.modules.module_9.xlsx_common import import_lookup_xlsx, lookup_export_xlsx, lookup_template_xlsx
from app.schemas.masterdata import DeliveryMethodImportRowResult

# The sheet's name and the column holding the delivery method's name.
SHEET_TITLE = "DeliveryMethods"
NAME_COLUMN = "delivery_method"


def build_delivery_method_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row ("id" + name)."""
    return lookup_template_xlsx(SHEET_TITLE, NAME_COLUMN)


def import_delivery_methods_from_xlsx(db: Session, file_bytes: bytes) -> list[DeliveryMethodImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""
    return import_lookup_xlsx(
        db,
        file_bytes,
        model=DeliveryMethod,
        field="delivery_method",
        column=NAME_COLUMN,
        duplicate_message="A delivery method with this name already exists",
        make_result=lambda row_number, key, outcome, detail: DeliveryMethodImportRowResult(
            row_number=row_number, delivery_method=key, outcome=outcome, detail=detail
        ),
    )


def export_delivery_methods_to_xlsx(db: Session) -> bytes:
    """Every delivery method as a workbook, in the template's columns."""
    return lookup_export_xlsx(db, model=DeliveryMethod, field="delivery_method", title=SHEET_TITLE, column=NAME_COLUMN)
