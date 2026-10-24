# StockMaster's (module-4) product master data: the Products screen and its
# four small lookup lists (Type, Magazijnen, Categorieën, Limieten) under the
# sidebar's "Masterdata" group, their bulk XLSX import/export ("Data
# Upload/Download") and the product statistics on the KPI page. These used
# to live in MasterData (module-9); the tables kept their MasterData_* names,
# only the screens, endpoints and rights moved here. Its own APIRouter on
# the same /api/modules/module-4 prefix (included in app/main.py) so the
# stock router.py doesn't grow even larger.
#
# Every endpoint is gated by StockMaster's custom roles per screen. The
# product picture's GET stays in router.py (plain module access, so every
# booking panel can show it); only changing it needs the Products screen.

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_limit import ProductLimit
from app.db.models.product_type import ProductType
from app.db.models.rfid_tag import RfidTag
from app.db.models.stockmaster_movement import StockMasterMovement
from app.db.models.user import User
from app.db.models.warehouse import Warehouse
from app.modules.module_4.deps import require_module_access, require_screen_permission, user_can
from app.modules.module_4.product_category_import import (
    build_product_category_template_xlsx,
    export_product_categories_to_xlsx,
    import_product_categories_from_xlsx,
)
from app.modules.module_4.product_import import (
    build_product_template_xlsx,
    export_products_to_xlsx,
    import_products_from_xlsx,
)
from app.modules.module_4.product_limit_import import (
    build_product_limit_template_xlsx,
    export_product_limits_to_xlsx,
    import_product_limits_from_xlsx,
)
from app.modules.module_4.product_stats import build_product_stats
from app.modules.module_4.product_type_import import (
    build_product_type_template_xlsx,
    export_product_types_to_xlsx,
    import_product_types_from_xlsx,
)
from app.modules.module_4.warehouse_import import (
    build_warehouse_template_xlsx,
    export_warehouses_to_xlsx,
    import_warehouses_from_xlsx,
)
from app.schemas.masterdata import (
    ProductCategoryCreateRequest,
    ProductCategoryImportResponse,
    ProductCategoryResponse,
    ProductCategoryUpdateRequest,
    ProductCreateRequest,
    ProductImportResponse,
    ProductLimitCreateRequest,
    ProductLimitImportResponse,
    ProductLimitResponse,
    ProductLimitUpdateRequest,
    ProductResponse,
    ProductTypeCreateRequest,
    ProductTypeImportResponse,
    ProductTypeResponse,
    ProductTypeUpdateRequest,
    ProductUpdateRequest,
    WarehouseCreateRequest,
    WarehouseImportResponse,
    WarehouseResponse,
    WarehouseUpdateRequest,
)
from app.schemas.stockmaster import ProductStatsResponse

router = APIRouter(prefix="/api/modules/module-4", tags=["StockMaster"])

PRODUCTS_SCREEN = "stockmaster.products"
PRODUCT_TYPES_SCREEN = "stockmaster.product-types"
WAREHOUSES_SCREEN = "stockmaster.warehouses"
PRODUCT_CATEGORIES_SCREEN = "stockmaster.product-categories"
PRODUCT_LIMITS_SCREEN = "stockmaster.product-limits"
DATA_UPLOAD_SCREEN = "stockmaster.dataupload"
KPI_SCREEN = "stockmaster.kpi"

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# The product Limiet (matched by name, ignoring case) that needs a Limietwaarde.
PERCENTAGE_LIMIT_NAME = "percentage"


# --- Product statistics (KPI page) -------------------------------------------


@router.get("/product-stats", response_model=ProductStatsResponse)
def get_product_stats(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KPI_SCREEN, "view")),
) -> ProductStatsResponse:
    """Product counts and breakdowns for the KPI page (not per season)."""
    return build_product_stats(db)


# --- Products and their lookup lists -----------------------------------------


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCTS_SCREEN, "view")),
) -> list[Product]:
    """List every product, for the Products screen's table."""
    return list(db.scalars(select(Product).order_by(Product.name)).all())


def _validate_product_lookup_ids(db: Session, payload: ProductCreateRequest | ProductUpdateRequest) -> None:
    """Make sure the type_id/warehouse_id/category_id (always given) and
    limit_id (optional) actually exist, the same way set_user_role() below
    checks role_id exists before assigning it — otherwise a bad id would
    only surface as an opaque foreign-key IntegrityError instead of a clear 404.
    """
    if db.get(ProductType, payload.type_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")
    if db.get(Warehouse, payload.warehouse_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    if db.get(ProductCategory, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")
    product_limit = db.get(ProductLimit, payload.limit_id)
    if product_limit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product limit not found")
    # The "Percentage" limit means nothing without its percentage: the Limietwaarde is required then.
    if product_limit.name.strip().lower() == PERCENTAGE_LIMIT_NAME and payload.limit_value is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A limit value is required for the Percentage limit"
        )


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCTS_SCREEN, "create")),
) -> Product:
    """Create a brand-new product."""
    _validate_product_lookup_ids(db, payload)

    new_product = Product(**payload.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCTS_SCREEN, "edit")),
) -> Product:
    """Update every field of an existing product."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    _validate_product_lookup_ids(db, payload)

    for field, value in payload.model_dump().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCTS_SCREEN, "delete")),
) -> None:
    """Permanently delete a product — unless StockMaster (module-4) has
    stock or booking history for it, which must never silently disappear.
    """
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    has_stock_history = db.scalar(
        select(StockMasterMovement.id).where(StockMasterMovement.product_id == product_id).limit(1)
    )
    if has_stock_history is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product has stock bookings in StockMaster and can't be deleted (block it instead)",
        )

    # KarTracker kars use a product as their transport type, and TagScan
    # RFID tags can be assigned to one — refuse with a clear message rather
    # than letting the database's foreign key turn it into a 500.
    used_by_kars = db.scalar(select(func.count(KarTrackerKar.id)).where(KarTrackerKar.transport_type_id == product_id))
    if used_by_kars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This product is the transport type of {used_by_kars} kar(s) in KarTracker and can't be deleted (block it instead)",
        )
    used_by_tags = db.scalar(select(func.count(RfidTag.id)).where(RfidTag.assigned_product_id == product_id))
    if used_by_tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This product is assigned to {used_by_tags} RFID tag(s) in TagScan and can't be deleted (block it instead)",
        )

    db.delete(product)
    db.commit()


# ---- Product picture -------------------------------------------------------
# One optional picture per product, uploaded separately from the JSON
# create/update above (the screen saves the fields first, then the picture).
# Stored as bytes in Postgres, the same way as KarTracker's ground plans.

ALLOWED_PRODUCT_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_PRODUCT_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB — plenty for a product photo.


def _get_product_or_404(db: Session, product_id: int) -> Product:
    """Load one product or answer 404."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def _require_product_image_change(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> User:
    """Changing a picture needs "edit" on Products, or "create" — so a role
    that may only add products can still attach a picture to a new one.
    """
    if not (
        user_can(db, current_user, PRODUCTS_SCREEN, "edit")
        or user_can(db, current_user, PRODUCTS_SCREEN, "create")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not allowed to edit on {PRODUCTS_SCREEN}")
    return current_user


@router.put("/products/{product_id}/image", response_model=ProductResponse)
def upload_product_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(_require_product_image_change),
) -> Product:
    """Set or replace a product's picture (PNG, JPEG or WebP, up to 5 MB)."""
    product = _get_product_or_404(db, product_id)

    if image.content_type not in ALLOWED_PRODUCT_IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be PNG, JPEG or WebP")
    # Read one byte past the limit so an oversized picture is detected
    # without ever buffering an unbounded upload into memory.
    contents = image.file.read(MAX_PRODUCT_IMAGE_BYTES + 1)
    if len(contents) > MAX_PRODUCT_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be smaller than 5 MB")

    product.image_data = contents
    product.image_content_type = image.content_type
    product.image_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}/image", response_model=ProductResponse)
def delete_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCTS_SCREEN, "edit")),
) -> Product:
    """Remove a product's picture; the product itself stays."""
    product = _get_product_or_404(db, product_id)
    product.image_data = None
    product.image_content_type = None
    product.image_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product)
    return product


@router.get("/product-types", response_model=list[ProductTypeResponse])
def list_product_types(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_TYPES_SCREEN, "view")),
) -> list[ProductType]:
    """List every product type, for the Type screen's table."""
    return list(db.scalars(select(ProductType).order_by(ProductType.name)).all())


@router.post("/product-types", response_model=ProductTypeResponse, status_code=status.HTTP_201_CREATED)
def create_product_type(
    payload: ProductTypeCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_TYPES_SCREEN, "create")),
) -> ProductType:
    """Create a brand-new product type."""
    new_product_type = ProductType(name=payload.name)
    db.add(new_product_type)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product type with this name already exists"
        ) from error

    db.refresh(new_product_type)
    return new_product_type


@router.put("/product-types/{product_type_id}", response_model=ProductTypeResponse)
def update_product_type(
    product_type_id: int,
    payload: ProductTypeUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_TYPES_SCREEN, "edit")),
) -> ProductType:
    """Rename an existing product type."""
    product_type = db.get(ProductType, product_type_id)
    if product_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")

    product_type.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product type with this name already exists"
        ) from error

    db.refresh(product_type)
    return product_type


@router.delete("/product-types/{product_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_type(
    product_type_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_TYPES_SCREEN, "delete")),
) -> None:
    """Permanently delete a product type, as long as no product is using it."""
    product_type = db.get(ProductType, product_type_id)
    if product_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")

    still_used = db.scalar(select(Product).where(Product.type_id == product_type_id))
    if still_used is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This product type is still used by at least one product")

    db.delete(product_type)
    db.commit()


@router.get("/warehouses", response_model=list[WarehouseResponse])
def list_warehouses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(WAREHOUSES_SCREEN, "view")),
) -> list[Warehouse]:
    """List every warehouse, for the Magazijn screen's table."""
    return list(db.scalars(select(Warehouse).order_by(Warehouse.name)).all())


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(WAREHOUSES_SCREEN, "create")),
) -> Warehouse:
    """Create a brand-new warehouse."""
    new_warehouse = Warehouse(name=payload.name)
    db.add(new_warehouse)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A warehouse with this name already exists"
        ) from error

    db.refresh(new_warehouse)
    return new_warehouse


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(WAREHOUSES_SCREEN, "edit")),
) -> Warehouse:
    """Rename an existing warehouse."""
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    warehouse.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A warehouse with this name already exists"
        ) from error

    db.refresh(warehouse)
    return warehouse


@router.delete("/warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(WAREHOUSES_SCREEN, "delete")),
) -> None:
    """Permanently delete a warehouse, as long as no product is using it."""
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    still_used = db.scalar(select(Product).where(Product.warehouse_id == warehouse_id))
    if still_used is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This warehouse is still used by at least one product")

    db.delete(warehouse)
    db.commit()


@router.get("/product-categories", response_model=list[ProductCategoryResponse])
def list_product_categories(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_CATEGORIES_SCREEN, "view")),
) -> list[ProductCategory]:
    """List every product category, for the Categorie screen's table."""
    return list(db.scalars(select(ProductCategory).order_by(ProductCategory.name)).all())


@router.post("/product-categories", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_product_category(
    payload: ProductCategoryCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_CATEGORIES_SCREEN, "create")),
) -> ProductCategory:
    """Create a brand-new product category."""
    new_product_category = ProductCategory(name=payload.name)
    db.add(new_product_category)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product category with this name already exists"
        ) from error

    db.refresh(new_product_category)
    return new_product_category


@router.put("/product-categories/{product_category_id}", response_model=ProductCategoryResponse)
def update_product_category(
    product_category_id: int,
    payload: ProductCategoryUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_CATEGORIES_SCREEN, "edit")),
) -> ProductCategory:
    """Rename an existing product category."""
    product_category = db.get(ProductCategory, product_category_id)
    if product_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")

    product_category.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product category with this name already exists"
        ) from error

    db.refresh(product_category)
    return product_category


@router.delete("/product-categories/{product_category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_category(
    product_category_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_CATEGORIES_SCREEN, "delete")),
) -> None:
    """Permanently delete a product category, as long as no product is using it."""
    product_category = db.get(ProductCategory, product_category_id)
    if product_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")

    still_used = db.scalar(select(Product).where(Product.category_id == product_category_id))
    if still_used is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This product category is still used by at least one product"
        )

    db.delete(product_category)
    db.commit()


@router.get("/product-limits", response_model=list[ProductLimitResponse])
def list_product_limits(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_LIMITS_SCREEN, "view")),
) -> list[ProductLimit]:
    """List every limit option, for the Limiet screen's table."""
    return list(db.scalars(select(ProductLimit).order_by(ProductLimit.name)).all())


@router.post("/product-limits", response_model=ProductLimitResponse, status_code=status.HTTP_201_CREATED)
def create_product_limit(
    payload: ProductLimitCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_LIMITS_SCREEN, "create")),
) -> ProductLimit:
    """Create a brand-new limit option."""
    new_product_limit = ProductLimit(name=payload.name)
    db.add(new_product_limit)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A limit option with this name already exists"
        ) from error

    db.refresh(new_product_limit)
    return new_product_limit


@router.put("/product-limits/{product_limit_id}", response_model=ProductLimitResponse)
def update_product_limit(
    product_limit_id: int,
    payload: ProductLimitUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_LIMITS_SCREEN, "edit")),
) -> ProductLimit:
    """Rename an existing limit option."""
    product_limit = db.get(ProductLimit, product_limit_id)
    if product_limit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product limit not found")

    product_limit.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A limit option with this name already exists"
        ) from error

    db.refresh(product_limit)
    return product_limit


@router.delete("/product-limits/{product_limit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_limit(
    product_limit_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PRODUCT_LIMITS_SCREEN, "delete")),
) -> None:
    """Permanently delete a limit option, as long as no product is using it."""
    product_limit = db.get(ProductLimit, product_limit_id)
    if product_limit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product limit not found")

    still_used = db.scalar(select(Product).where(Product.limit_id == product_limit_id))
    if still_used is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This limit option is still used by at least one product")

    db.delete(product_limit)
    db.commit()



# --- Data Upload/Download: bulk XLSX import/export, one tile per table, all
# gated by the SAME "stockmaster.dataupload" screen key (never by each
# table's own screen key), like MasterData's own Data Upload/Download.


@router.get("/product-type-import/template")
def download_product_type_import_template(
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing product types."""
    return Response(
        content=build_product_type_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="product-type-import-template.xlsx"'},
    )


@router.post("/product-type-import", response_model=ProductTypeImportResponse)
def import_product_types(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "create")),
) -> ProductTypeImportResponse:
    """Bulk-import product types from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_product_types_from_xlsx(db, file.file.read())
    return ProductTypeImportResponse(results=results)


@router.get("/product-types/export")
def export_product_types_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """Every product type as an XLSX workbook."""
    return Response(
        content=export_product_types_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="stockmaster-product-types-export.xlsx"'},
    )


@router.get("/warehouse-import/template")
def download_warehouse_import_template(
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing warehouses."""
    return Response(
        content=build_warehouse_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="warehouse-import-template.xlsx"'},
    )


@router.post("/warehouse-import", response_model=WarehouseImportResponse)
def import_warehouses(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "create")),
) -> WarehouseImportResponse:
    """Bulk-import warehouses from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_warehouses_from_xlsx(db, file.file.read())
    return WarehouseImportResponse(results=results)


@router.get("/warehouses/export")
def export_warehouses_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """Every warehouse as an XLSX workbook."""
    return Response(
        content=export_warehouses_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="stockmaster-warehouses-export.xlsx"'},
    )


@router.get("/product-category-import/template")
def download_product_category_import_template(
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing product categories."""
    return Response(
        content=build_product_category_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="product-category-import-template.xlsx"'},
    )


@router.post("/product-category-import", response_model=ProductCategoryImportResponse)
def import_product_categories(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "create")),
) -> ProductCategoryImportResponse:
    """Bulk-import product categories from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_product_categories_from_xlsx(db, file.file.read())
    return ProductCategoryImportResponse(results=results)


@router.get("/product-categories/export")
def export_product_categories_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """Every product category as an XLSX workbook."""
    return Response(
        content=export_product_categories_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="stockmaster-product-categories-export.xlsx"'},
    )


@router.get("/product-limit-import/template")
def download_product_limit_import_template(
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing limit options."""
    return Response(
        content=build_product_limit_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="product-limit-import-template.xlsx"'},
    )


@router.post("/product-limit-import", response_model=ProductLimitImportResponse)
def import_product_limits(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "create")),
) -> ProductLimitImportResponse:
    """Bulk-import limit options from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_product_limits_from_xlsx(db, file.file.read())
    return ProductLimitImportResponse(results=results)


@router.get("/product-limits/export")
def export_product_limits_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """Every limit option as an XLSX workbook."""
    return Response(
        content=export_product_limits_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="stockmaster-product-limits-export.xlsx"'},
    )


@router.get("/product-import/template")
def download_product_import_template(
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing products."""
    return Response(
        content=build_product_template_xlsx(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="product-import-template.xlsx"'},
    )


@router.post("/product-import", response_model=ProductImportResponse)
def import_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "create")),
) -> ProductImportResponse:
    """Bulk-import products from an uploaded XLSX workbook: a row with an
    existing id updates it, a row without one creates a new one.
    """
    results = import_products_from_xlsx(db, file.file.read())
    return ProductImportResponse(results=results)


@router.get("/products/export")
def export_products_xlsx(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
) -> Response:
    """Every product as an XLSX workbook."""
    return Response(
        content=export_products_to_xlsx(db),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="stockmaster-products-export.xlsx"'},
    )
