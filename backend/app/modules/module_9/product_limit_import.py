# Bulk XLSX import/export for the Product Limit (Limiet) lookup (MasterData's "Data
# Upload/Download" screen): the template, the upload and the export. The
# work is done by the shared one-name lookup helpers in xlsx_common.py: a
# row with an "id" renames that record, a row without one adds a new
# product limit (limiet), and a name that's already taken is a row error.

from sqlalchemy.orm import Session

from app.db.models.product_limit import ProductLimit
from app.modules.module_9.xlsx_common import import_lookup_xlsx, lookup_export_xlsx, lookup_template_xlsx
from app.schemas.masterdata import ProductLimitImportRowResult

# The sheet's name and the column holding the product limit (limiet)'s name.
SHEET_TITLE = "Limieten"
NAME_COLUMN = "name"


def build_product_limit_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row ("id" + name)."""
    return lookup_template_xlsx(SHEET_TITLE, NAME_COLUMN)


def import_product_limits_from_xlsx(db: Session, file_bytes: bytes) -> list[ProductLimitImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""
    return import_lookup_xlsx(
        db,
        file_bytes,
        model=ProductLimit,
        field="name",
        column=NAME_COLUMN,
        duplicate_message="A limit option with this name already exists",
        make_result=lambda row_number, key, outcome, detail: ProductLimitImportRowResult(
            row_number=row_number, name=key, outcome=outcome, detail=detail
        ),
    )


def export_product_limits_to_xlsx(db: Session) -> bytes:
    """Every product limit (limiet) as a workbook, in the template's columns."""
    return lookup_export_xlsx(db, model=ProductLimit, field="name", title=SHEET_TITLE, column=NAME_COLUMN)
