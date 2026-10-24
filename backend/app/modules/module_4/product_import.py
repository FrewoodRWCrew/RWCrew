# Bulk XLSX import/export for Products (MasterData's "Data Upload/Download"
# screen): the template, the upload and the export, in the same columns.
# Type, warehouse, category and Limiet are given by name, resolved against
# their lookup tables ignoring case; yes/no columns accept true/false, 1/0
# and yes/no.
#
# Same rules as every MasterData import (see xlsx_common.py): a row with an
# "id" updates that product, a row without one creates a new product.
# Product names aren't unique (the screen allows two with the same name), so
# there's no "already exists" check — which is exactly why an export must be
# re-uploaded with its id column, or every row would become a new product.
# On an update, a column missing from the sheet leaves that field alone; a
# new product needs the same fields as the Products screen.

from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_limit import ProductLimit
from app.db.models.product_type import ProductType
from app.db.models.warehouse import Warehouse
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
from app.schemas.masterdata import ProductImportRowResult

TEMPLATE_COLUMNS = [
    ID_COLUMN,
    "name",
    "type_name",
    "warehouse_name",
    "warehouse_location",
    "category_name",
    "is_consumable",
    "is_blocked",
    "is_logistics_product",
    "is_tag_managed",
    "limit_name",
    "limit_value",
    "max_initial_stock",
    "min_stock",
    "stock_return_to",
    "description",
    "cost",
]
SHEET_TITLE = "Products"

# Columns a new product can't do without (the fields the Products screen requires).
_REQUIRED_ON_CREATE = ("name", "type_name", "warehouse_name", "category_name", "limit_name")

# Where a product goes back to after "Kar terug" (StockMaster): into the kar,
# or to the free stock. Blank means "kar", the model's default.
STOCK_RETURN_TO_VALUES = ("kar", "free")

# The product Limiet (matched by name, ignoring case) that needs a Limietwaarde — same as router.py.
PERCENTAGE_LIMIT_NAME = "percentage"


def build_product_template_xlsx() -> bytes:
    """The downloadable XLSX template: just the header row."""
    return build_xlsx(SHEET_TITLE, TEMPLATE_COLUMNS)


def _cell_text(value: object) -> str | None:
    """Empty/blank cells mean "not set"; anything else is stringified and trimmed."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_TRUE_CELL_VALUES = {"1", "true", "yes"}
_FALSE_CELL_VALUES = {"0", "false", "no"}


def _parse_bool_cell(column_name: str, value: object) -> bool:
    """Blank means False, matching the model's own default=False. Any
    other value must be a recognized true/false spelling — a typo (e.g.
    "tru") is rejected as an error instead of silently becoming True,
    which is how a permissive "anything non-blank is truthy" rule would
    otherwise treat it.
    """
    text = _cell_text(value)
    if text is None:
        return False
    normalized = text.lower()
    if normalized in _TRUE_CELL_VALUES:
        return True
    if normalized in _FALSE_CELL_VALUES:
        return False
    raise ValueError(f'{column_name} "{text}" is not recognized — use "true"/"false", "1"/"0", or "yes"/"no"')


def _parse_non_negative_int_cell(column_name: str, value: object) -> int | None:
    """Blank means "not set". Otherwise a whole number of 0 or more —
    anything else is rejected as an error."""
    text = _cell_text(value)
    if text is None:
        return None
    try:
        number = Decimal(text.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f'{column_name} "{text}" is not a number') from None
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError(f'{column_name} "{text}" must be a whole number of 0 or more')
    return int(number)


def _parse_cost_cell(value: object) -> Decimal | None:
    """Blank means "unknown". Otherwise a number of euro, not negative,
    rounded to cents — anything else is rejected as an error."""
    text = _cell_text(value)
    if text is None:
        return None
    try:
        cost = Decimal(text.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f'cost "{text}" is not a number') from None
    if not cost.is_finite() or cost < 0:
        raise ValueError(f'cost "{text}" must be 0 or more')
    # The column holds 10 digits with 2 decimals: refuse what doesn't fit (before
    # quantize, which would raise on a huge number instead of this row error).
    if cost >= Decimal("100000000"):
        raise ValueError(f'cost "{text}" must be less than 100000000')
    return cost.quantize(Decimal("0.01"))


def _parse_stock_return_to_cell(value: object) -> str:
    """The "stock_return_to" cell: "kar" or "free" (ignoring case); blank means "kar"."""
    text = _cell_text(value)
    if text is None:
        return "kar"
    if text.lower() not in STOCK_RETURN_TO_VALUES:
        raise ValueError(f'stock_return_to "{text}" is not recognized — use "kar" or "free"')
    return text.lower()


def _required_text(column: str, value: object) -> str:
    """A text cell that may not be blank."""
    text = _cell_text(value)
    if text is None:
        raise ValueError(f"{column} is required")
    return text


def _resolve_type_id(db: Session, type_name: str | None) -> int | None:
    if type_name is None:
        return None
    product_type = db.scalar(select(ProductType).where(ProductType.name.ilike(type_name)))
    if product_type is None:
        raise ValueError(f'Type "{type_name}" not found')
    return product_type.id


def _resolve_warehouse_id(db: Session, warehouse_name: str | None) -> int | None:
    if warehouse_name is None:
        return None
    warehouse = db.scalar(select(Warehouse).where(Warehouse.name.ilike(warehouse_name)))
    if warehouse is None:
        raise ValueError(f'Warehouse "{warehouse_name}" not found')
    return warehouse.id


def _resolve_category_id(db: Session, category_name: str | None) -> int | None:
    if category_name is None:
        return None
    category = db.scalar(select(ProductCategory).where(ProductCategory.name.ilike(category_name)))
    if category is None:
        raise ValueError(f'Category "{category_name}" not found')
    return category.id


def _resolve_limit_id(db: Session, limit_name: str | None) -> int | None:
    if limit_name is None:
        return None
    product_limit = db.scalar(select(ProductLimit).where(ProductLimit.name.ilike(limit_name)))
    if product_limit is None:
        raise ValueError(f'Limit "{limit_name}" not found')
    return product_limit.id


def import_products_from_xlsx(db: Session, file_bytes: bytes) -> list[ProductImportRowResult]:
    """Apply every row of an uploaded workbook, one result per row."""

    def apply_row(row: UploadedRow) -> tuple[str | None, ImportOutcome]:
        name = row.text("name")
        try:
            product = find_by_id(db, Product, row)
            if product is None:
                for column in _REQUIRED_ON_CREATE:
                    if row.text(column) is None:
                        raise ValueError(f"{column} is required")

            # Each column's model field and parser — only the columns the
            # sheet has (on create, the required ones are all there). Type,
            # warehouse, category and Limiet can't be emptied, like on the screen.
            parsers = {
                "name": ("name", lambda value: _required_text("name", value)),
                "type_name": ("type_id", lambda value: _resolve_type_id(db, _required_text("type_name", value))),
                "warehouse_name": (
                    "warehouse_id",
                    lambda value: _resolve_warehouse_id(db, _required_text("warehouse_name", value)),
                ),
                "warehouse_location": ("warehouse_location", _cell_text),
                "category_name": (
                    "category_id",
                    lambda value: _resolve_category_id(db, _required_text("category_name", value)),
                ),
                "is_consumable": ("is_consumable", lambda value: _parse_bool_cell("is_consumable", value)),
                "is_blocked": ("is_blocked", lambda value: _parse_bool_cell("is_blocked", value)),
                "is_logistics_product": (
                    "is_logistics_product",
                    lambda value: _parse_bool_cell("is_logistics_product", value),
                ),
                "is_tag_managed": ("is_tag_managed", lambda value: _parse_bool_cell("is_tag_managed", value)),
                "limit_name": ("limit_id", lambda value: _resolve_limit_id(db, _required_text("limit_name", value))),
                "limit_value": ("limit_value", lambda value: _parse_non_negative_int_cell("limit_value", value)),
                "max_initial_stock": (
                    "max_initial_stock",
                    lambda value: _parse_non_negative_int_cell("max_initial_stock", value),
                ),
                "min_stock": ("min_stock", lambda value: _parse_non_negative_int_cell("min_stock", value)),
                "stock_return_to": ("stock_return_to", _parse_stock_return_to_cell),
                "description": ("description", _cell_text),
                "cost": ("cost", _parse_cost_cell),
            }
            fields = {field: parse(row.value(column)) for column, (field, parse) in parsers.items() if row.has(column)}

            # The "Percentage" Limiet means nothing without its percentage
            # (same rule as the screen) — checked on the values after this row.
            limit_id = fields.get("limit_id", product.limit_id if product else None)
            limit_value = fields.get("limit_value", product.limit_value if product else None)
            limit = db.get(ProductLimit, limit_id) if limit_id is not None else None
            if limit is not None and limit.name.lower() == PERCENTAGE_LIMIT_NAME and limit_value is None:
                raise ValueError("limit_value is required for the Percentage limit")

            if product is None:
                db.add(Product(**fields))
                return name, "created"
            for field, value in fields.items():
                setattr(product, field, value)
            return name or product.name, "updated"
        except ValueError as error:
            raise RowError(str(error), name) from None

    return run_import(
        read_rows(file_bytes),
        db,
        apply_row,
        lambda row_number, key, outcome, detail: ProductImportRowResult(
            row_number=row_number, name=key, outcome=outcome, detail=detail
        ),
    )


def export_products_to_xlsx(db: Session) -> bytes:
    """Every product as a workbook, with its lookups resolved back to names
    to match the template's own columns."""
    types = {product_type.id: product_type.name for product_type in db.scalars(select(ProductType)).all()}
    warehouses = {warehouse.id: warehouse.name for warehouse in db.scalars(select(Warehouse)).all()}
    categories = {category.id: category.name for category in db.scalars(select(ProductCategory)).all()}
    limits = {product_limit.id: product_limit.name for product_limit in db.scalars(select(ProductLimit)).all()}

    products = db.scalars(select(Product).order_by(Product.name)).all()
    return build_xlsx(
        SHEET_TITLE,
        TEMPLATE_COLUMNS,
        [
            [
                product.id,
                product.name,
                types.get(product.type_id, "") if product.type_id is not None else "",
                warehouses.get(product.warehouse_id, "") if product.warehouse_id is not None else "",
                product.warehouse_location,
                categories.get(product.category_id, "") if product.category_id is not None else "",
                product.is_consumable,
                product.is_blocked,
                product.is_logistics_product,
                product.is_tag_managed,
                limits.get(product.limit_id, "") if product.limit_id is not None else "",
                product.limit_value,
                product.max_initial_stock,
                product.min_stock,
                product.stock_return_to,
                product.description,
                float(product.cost) if product.cost is not None else None,
            ]
            for product in products
        ],
    )
