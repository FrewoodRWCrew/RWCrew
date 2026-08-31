# These tests check the "Products" screen: gated by normal module access
# + the "masterdata.products" permission, independently of
# "masterdata.season"/"roles"/"users", with a super-admin bypass and full
# CRUD — mirrors test_season.py's shape.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
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


def _grant_products_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = MasterDataRole(name=f"Products Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == "masterdata.products"))
    db_session.add(
        MasterDataRolePermission(
            role_id=role.id,
            screen_id=screen.id,
            can_view=can_view,
            can_create=can_create,
            can_edit=can_edit,
            can_delete=can_delete,
        )
    )
    db_session.add(MasterDataUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _create_product(db_session: Session, *, name: str = "KBC Lint") -> Product:
    product = Product(name=name)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_user_without_module_access_cannot_list_products(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_masterdata_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/products")

    assert response.status_code == 403


def test_user_with_access_but_no_products_permission_cannot_list_products(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/products")

    assert response.status_code == 403


def test_products_permission_does_not_grant_access_to_season_screen(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_products_permission(db_session, user, can_view=True, can_create=True)
    _login(client, "viewer@example.com")

    assert client.get("/api/modules/module-9/products").status_code == 200
    assert client.get("/api/modules/module-9/seasons").status_code == 403


def test_super_admin_can_manage_products_without_an_explicit_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/products", json={"name": "KBC Lint"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "KBC Lint"
    assert body["is_consumable"] is False


def test_view_only_products_permission_cannot_create_a_product(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_products_permission(db_session, user, can_view=True)
    _login(client, "viewer@example.com")

    response = client.post("/api/modules/module-9/products", json={"name": "KBC Lint"})

    assert response.status_code == 403


def test_create_product_with_full_field_set(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    warehouse = Warehouse(name="Uitleendienst")
    category = ProductCategory(name="Gereedschap")
    db_session.add_all([warehouse, category])
    db_session.commit()
    db_session.refresh(warehouse)
    db_session.refresh(category)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/products",
        json={
            "name": "KBC Lint",
            "warehouse_id": warehouse.id,
            "warehouse_location": "4RECHTS",
            "category_id": category.id,
            "is_consumable": True,
            "is_blocked": False,
            "is_logistics_product": False,
            "description": "Por rol",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["warehouse_id"] == warehouse.id
    assert body["category_id"] == category.id
    assert body["is_consumable"] is True


def test_list_products_ordered_by_name(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _create_product(db_session, name="Zaag")
    _create_product(db_session, name="Boormachine")
    _login(client, "admin@example.com")

    response = client.get("/api/modules/module-9/products")

    assert response.status_code == 200
    assert [product["name"] for product in response.json()] == ["Boormachine", "Zaag"]


def test_super_admin_can_update_a_product(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product = _create_product(db_session, name="KBC Lint")
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-9/products/{product.id}",
        json={"name": "KBC Lint 2", "is_blocked": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "KBC Lint 2"
    assert body["is_blocked"] is True


def test_updating_a_missing_product_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.put("/api/modules/module-9/products/999", json={"name": "Nope"})

    assert response.status_code == 404


def test_super_admin_can_delete_a_product(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product = _create_product(db_session, name="KBC Lint")
    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-9/products/{product.id}")

    assert response.status_code == 204
    assert client.get("/api/modules/module-9/products").json() == []


def test_deleting_a_missing_product_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.delete("/api/modules/module-9/products/999")

    assert response.status_code == 404
