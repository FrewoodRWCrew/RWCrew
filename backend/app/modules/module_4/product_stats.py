# Product statistics for StockMaster's KPI page: how many products there
# are, how many are blocked/consumable/logistics or miss a classification,
# and how they spread over the Type/Categorie/Magazijn lookup lists. Moved
# here from MasterData's dashboard together with the product screens. Kept
# free of FastAPI/routing concerns so it's easy to unit test on its own.
#
# None of these lookup lists has a timestamp, so there's no time series:
# each breakdown counts products per lookup row (every row gets an entry,
# zero-filled), plus one trailing "unassigned" entry.

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_type import ProductType
from app.db.models.warehouse import Warehouse
from app.schemas.stockmaster import ProductStatsBreakdownItem, ProductStatsResponse


def _breakdown(db: Session, lookup_model, fk_column) -> list[ProductStatsBreakdownItem]:
    """Count Product rows per row of one lookup table (Type/Category/
    Warehouse), ordered by the lookup's own name, plus one trailing
    (name=None) entry for products whose FK is null — appended even when its
    count is 0, so the chart's categories never shift around.
    """
    rows = db.execute(
        select(lookup_model.name, func.count(Product.id))
        .select_from(lookup_model)
        .outerjoin(Product, fk_column == lookup_model.id)
        .group_by(lookup_model.id, lookup_model.name)
        .order_by(lookup_model.name)
    ).all()

    unassigned_count = db.scalar(select(func.count()).select_from(Product).where(fk_column.is_(None)))

    return [ProductStatsBreakdownItem(name=name, count=count) for name, count in rows] + [
        ProductStatsBreakdownItem(name=None, count=unassigned_count or 0)
    ]


def build_product_stats(db: Session) -> ProductStatsResponse:
    """The product tiles and the three breakdown charts of the KPI page."""

    # One count per tile.
    def count(*conditions) -> int:
        query = select(func.count()).select_from(Product)
        if conditions:
            query = query.where(*conditions)
        return db.scalar(query) or 0

    return ProductStatsResponse(
        total_products=count(),
        blocked_products=count(Product.is_blocked),
        consumable_products=count(Product.is_consumable),
        logistics_products=count(Product.is_logistics_product),
        products_missing_classification=count(
            (Product.type_id.is_(None)) | (Product.warehouse_id.is_(None)) | (Product.category_id.is_(None))
        ),
        products_by_type=_breakdown(db, ProductType, Product.type_id),
        products_by_category=_breakdown(db, ProductCategory, Product.category_id),
        products_by_warehouse=_breakdown(db, Warehouse, Product.warehouse_id),
    )
