# Aggregate KPI stats for MasterData's landing dashboard ("Masterdata
# Overview"). Kept free of FastAPI/routing concerns, mirroring
# app/modules/module_1/tag_dashboard.py, so it's easy to unit test on its
# own.
#
# Unlike TagScan's dashboard, none of the masterdata models have a
# timestamp column, so there's no time-series chart here — instead, three
# breakdown charts group Product by each of its three lookup foreign keys
# (Type/Category/Warehouse). Each lookup list is itself small master data
# (a handful of rows, managed by hand on its own screen), so — unlike
# TagScan's top-5-product cap — every lookup row gets its own breakdown
# entry, with no LIMIT needed.

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_type import ProductType
from app.db.models.season import Season
from app.db.models.warehouse import Warehouse
from app.schemas.masterdata import (
    MasterDataCategoryBreakdownItem,
    MasterDataDashboardResponse,
    MasterDataTypeBreakdownItem,
    MasterDataWarehouseBreakdownItem,
)


def _breakdown(db: Session, lookup_model, fk_column):
    """Count Product rows per row of one lookup table (Type/Category/
    Warehouse), ordered by the lookup's own name, plus one trailing
    (name=None, count) entry for products whose FK is null — appended even
    when its count is 0, the same zero-fill approach tag_dashboard.py uses
    for its fixed-enum status_breakdown, so the chart's categories never
    shift around based on what data happens to exist.
    """
    rows = db.execute(
        select(lookup_model.name, func.count(Product.id))
        .select_from(lookup_model)
        .outerjoin(Product, fk_column == lookup_model.id)
        .group_by(lookup_model.id, lookup_model.name)
        .order_by(lookup_model.name)
    ).all()

    unassigned_count = db.scalar(select(func.count()).select_from(Product).where(fk_column.is_(None)))

    return [(name, count) for name, count in rows] + [(None, unassigned_count)]


def build_dashboard_stats(db: Session) -> MasterDataDashboardResponse:
    total_products = db.scalar(select(func.count()).select_from(Product))
    total_seasons = db.scalar(select(func.count()).select_from(Season))
    blocked_products = db.scalar(select(func.count()).select_from(Product).where(Product.is_blocked))
    consumable_products = db.scalar(select(func.count()).select_from(Product).where(Product.is_consumable))
    logistics_products = db.scalar(select(func.count()).select_from(Product).where(Product.is_logistics_product))
    products_missing_classification = db.scalar(
        select(func.count())
        .select_from(Product)
        .where(
            (Product.type_id.is_(None)) | (Product.warehouse_id.is_(None)) | (Product.category_id.is_(None))
        )
    )

    products_by_type = [
        MasterDataTypeBreakdownItem(type_name=name, count=count)
        for name, count in _breakdown(db, ProductType, Product.type_id)
    ]
    products_by_category = [
        MasterDataCategoryBreakdownItem(category_name=name, count=count)
        for name, count in _breakdown(db, ProductCategory, Product.category_id)
    ]
    products_by_warehouse = [
        MasterDataWarehouseBreakdownItem(warehouse_name=name, count=count)
        for name, count in _breakdown(db, Warehouse, Product.warehouse_id)
    ]

    return MasterDataDashboardResponse(
        total_products=total_products,
        total_seasons=total_seasons,
        blocked_products=blocked_products,
        consumable_products=consumable_products,
        logistics_products=logistics_products,
        products_missing_classification=products_missing_classification,
        products_by_type=products_by_type,
        products_by_category=products_by_category,
        products_by_warehouse=products_by_warehouse,
    )
