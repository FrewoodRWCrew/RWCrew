# These tests check MasterData's landing dashboard ("Masterdata
# Overview"): aggregate KPI stats gated by plain module access (no
# specific screen permission), mirroring
# backend/tests/modules/module_1/test_dashboard.py.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_type import ProductType
from app.db.models.season import Season
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.db.models.warehouse import Warehouse
from app.modules.module_9.screens import sync_screens


def _create_user(db_session: Session, *, email: str, is_super_admin: bool = False) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        display_name=email,
        is_super_admin=is_super_admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_masterdata_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-9"))
    if module is not None:
        return module
    module = Module(key="module-9", name="MasterData", sort_order=9)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


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


def _create_season(db_session: Session, *, name: str) -> Season:
    season = Season(name=name)
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


def test_dashboard_requires_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_masterdata_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/dashboard")

    assert response.status_code == 403


def test_dashboard_with_no_data_returns_all_zero_stats(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-9/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["total_products"] == 0
    assert body["total_seasons"] == 0
    assert body["blocked_products"] == 0
    assert body["consumable_products"] == 0
    assert body["logistics_products"] == 0
    assert body["products_missing_classification"] == 0
    # Only the trailing "Unassigned" (name=None) bucket exists — zero-filled.
    assert body["products_by_type"] == [{"type_name": None, "count": 0}]
    assert body["products_by_category"] == [{"category_name": None, "count": 0}]
    assert body["products_by_warehouse"] == [{"warehouse_name": None, "count": 0}]


def test_dashboard_computes_stat_tile_counts(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    _create_season(db_session, name="Summer 2026")
    _create_season(db_session, name="Winter 2026")

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

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-9/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["total_products"] == 2
    assert body["total_seasons"] == 2
    assert body["blocked_products"] == 1
    assert body["consumable_products"] == 1
    assert body["logistics_products"] == 1
    # Only the fully unclassified product is missing ALL THREE fields; the
    # classified one has every lookup set, so it doesn't count.
    assert body["products_missing_classification"] == 1


def test_dashboard_breakdowns_are_zero_filled_and_ordered_with_unassigned_last(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    type_a = _create_product_type(db_session, name="Zebra Type")
    type_b = _create_product_type(db_session, name="Alpha Type")

    _create_product(db_session, name="P1", type_id=type_a.id)
    _create_product(db_session, name="P2", type_id=type_a.id)
    _create_product(db_session, name="P3", type_id=type_b.id)
    _create_product(db_session, name="P4")  # no type — falls into "Unassigned"

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-9/dashboard")

    assert response.status_code == 200
    products_by_type = response.json()["products_by_type"]
    # Ordered by lookup name ("Alpha Type" before "Zebra Type", both before
    # the trailing Unassigned bucket), zero-filled for types with no products.
    assert products_by_type == [
        {"type_name": "Alpha Type", "count": 1},
        {"type_name": "Zebra Type", "count": 2},
        {"type_name": None, "count": 1},
    ]
