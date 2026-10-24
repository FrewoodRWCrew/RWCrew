# These tests check the product statistics on StockMaster's KPI page
# (GET /product-stats, moved here from MasterData's dashboard): gated by the
# "stockmaster.kpi" screen, all products (not per season).

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_type import ProductType
from app.db.models.stockmaster_role import StockMasterRole
from app.db.models.stockmaster_role_permission import StockMasterRolePermission
from app.db.models.stockmaster_screen import StockMasterScreen
from app.db.models.stockmaster_user_role import StockMasterUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.db.models.warehouse import Warehouse
from app.modules.module_4.screens import sync_screens

URL = "/api/modules/module-4/product-stats"


def _viewer(client: TestClient, db_session: Session, *, kpi: bool = True) -> None:
    """Log in a StockMaster user, with or without "view" on the KPI screen."""
    sync_screens(db_session)
    module = Module(key="module-4", name="StockMaster", sort_order=4)
    user = User(email="viewer@example.com", hashed_password=hash_password("password123"), display_name="Viewer")
    role = StockMasterRole(name="KPI")
    db_session.add_all([module, user, role])
    db_session.flush()
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.add(StockMasterUserRole(user_id=user.id, role_id=role.id))
    screen = db_session.scalar(select(StockMasterScreen).where(StockMasterScreen.key == "stockmaster.kpi"))
    db_session.add(
        StockMasterRolePermission(
            role_id=role.id, screen_id=screen.id, can_view=kpi, can_create=False, can_edit=False, can_delete=False
        )
    )
    db_session.commit()
    client.post("/api/auth/login", json={"email": "viewer@example.com", "password": "password123"})


def _create_product_type(db_session: Session, *, name: str) -> ProductType:
    product_type = ProductType(name=name)
    db_session.add(product_type)
    db_session.commit()
    db_session.refresh(product_type)
    return product_type


def _create_product_category(db_session: Session, *, name: str) -> ProductCategory:
    category = ProductCategory(name=name)
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def _create_warehouse(db_session: Session, *, name: str) -> Warehouse:
    warehouse = Warehouse(name=name)
    db_session.add(warehouse)
    db_session.commit()
    db_session.refresh(warehouse)
    return warehouse


def _create_product(
    db_session: Session,
    *,
    name: str,
    type_id: int | None = None,
    warehouse_id: int | None = None,
    category_id: int | None = None,
    is_blocked: bool = False,
    is_consumable: bool = False,
    is_logistics_product: bool = False,
) -> Product:
    product = Product(
        name=name,
        type_id=type_id,
        warehouse_id=warehouse_id,
        category_id=category_id,
        is_blocked=is_blocked,
        is_consumable=is_consumable,
        is_logistics_product=is_logistics_product,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product



def test_product_stats_need_the_kpi_screen(client: TestClient, db_session: Session) -> None:
    _viewer(client, db_session, kpi=False)

    assert client.get(URL).status_code == 403


def test_product_stats_with_no_data_are_all_zero(client: TestClient, db_session: Session) -> None:
    _viewer(client, db_session)

    response = client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["total_products"] == 0
    assert body["blocked_products"] == 0
    assert body["consumable_products"] == 0
    assert body["logistics_products"] == 0
    assert body["products_missing_classification"] == 0
    # Only the trailing "Unassigned" (name=None) bucket exists — zero-filled.
    assert body["products_by_type"] == [{"name": None, "count": 0}]
    assert body["products_by_category"] == [{"name": None, "count": 0}]
    assert body["products_by_warehouse"] == [{"name": None, "count": 0}]


def test_product_stats_compute_the_tile_counts(client: TestClient, db_session: Session) -> None:
    _viewer(client, db_session)
    product_type = _create_product_type(db_session, name="Textile")
    warehouse = _create_warehouse(db_session, name="Main Warehouse")
    category = _create_product_category(db_session, name="Apparel")
    _create_product(
        db_session,
        name="Fully Classified",
        type_id=product_type.id,
        warehouse_id=warehouse.id,
        category_id=category.id,
        is_blocked=True,
        is_consumable=True,
        is_logistics_product=True,
    )
    _create_product(db_session, name="Unclassified")

    body = client.get(URL).json()

    assert body["total_products"] == 2
    assert body["blocked_products"] == 1
    assert body["consumable_products"] == 1
    assert body["logistics_products"] == 1
    # Only the unclassified product misses a lookup.
    assert body["products_missing_classification"] == 1


def test_product_stats_breakdowns_are_zero_filled_and_ordered_with_unassigned_last(
    client: TestClient, db_session: Session
) -> None:
    _viewer(client, db_session)
    type_a = _create_product_type(db_session, name="Zebra Type")
    type_b = _create_product_type(db_session, name="Alpha Type")
    _create_product_type(db_session, name="Middle Type")
    _create_product(db_session, name="P1", type_id=type_a.id)
    _create_product(db_session, name="P2", type_id=type_a.id)
    _create_product(db_session, name="P3", type_id=type_b.id)
    _create_product(db_session, name="P4")  # no type — falls into "Unassigned"

    products_by_type = client.get(URL).json()["products_by_type"]

    assert products_by_type == [
        {"name": "Alpha Type", "count": 1},
        {"name": "Middle Type", "count": 0},
        {"name": "Zebra Type", "count": 2},
        {"name": None, "count": 1},
    ]
