# These tests check the "Products" screen: gated by normal module access
# + the "masterdata.products" permission, independently of
# "masterdata.season"/"roles"/"users", with a super-admin bypass and full
# CRUD — mirrors test_season.py's shape.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.product_limit import ProductLimit
from app.db.models.product_type import ProductType
from app.db.models.rfid_tag import RfidTag
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


def _required_fields(db_session: Session) -> dict:
    """The fields every create/update must send besides the name: a type,
    warehouse, category and limit (created here) and "na Kar terug"."""
    product_type = ProductType(name="Gereedschap type")
    warehouse = Warehouse(name="Hoofdmagazijn")
    category = ProductCategory(name="Algemeen")
    limit = ProductLimit(name="Ongelimiteerd")
    db_session.add_all([product_type, warehouse, category, limit])
    db_session.commit()
    return {
        "type_id": product_type.id,
        "warehouse_id": warehouse.id,
        "category_id": category.id,
        "limit_id": limit.id,
        "stock_return_to": "kar",
    }


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
    required = _required_fields(db_session)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/products", json={"name": "KBC Lint", **required})

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
    required = _required_fields(db_session)
    _login(client, "viewer@example.com")

    response = client.post("/api/modules/module-9/products", json={"name": "KBC Lint", **required})

    assert response.status_code == 403


def test_create_product_with_full_field_set(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = ProductType(name="Verbruik")
    warehouse = Warehouse(name="Uitleendienst")
    category = ProductCategory(name="Gereedschap")
    limit = ProductLimit(name="Max initiële stock per kar")
    db_session.add_all([product_type, warehouse, category, limit])
    db_session.commit()
    db_session.refresh(product_type)
    db_session.refresh(warehouse)
    db_session.refresh(category)
    db_session.refresh(limit)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/products",
        json={
            "name": "KBC Lint",
            "type_id": product_type.id,
            "warehouse_id": warehouse.id,
            "warehouse_location": "4RECHTS",
            "category_id": category.id,
            "is_consumable": True,
            "is_blocked": False,
            "is_logistics_product": False,
            "is_tag_managed": True,
            "description": "Por rol",
            "stock_return_to": "free",
            "cost": 12.5,
            "limit_id": limit.id,
            "limit_value": 20,
            "max_initial_stock": 8,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["type_id"] == product_type.id
    assert body["warehouse_id"] == warehouse.id
    assert body["category_id"] == category.id
    assert body["is_consumable"] is True
    assert body["is_tag_managed"] is True
    assert body["stock_return_to"] == "free"
    assert body["cost"] == 12.5
    assert body["limit_id"] == limit.id
    assert body["limit_value"] == 20
    assert body["max_initial_stock"] == 8


def test_type_warehouse_category_and_stock_return_are_required(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    required = _required_fields(db_session)
    product = _create_product(db_session)

    # Leaving out any one of the four required fields is refused, on create and update.
    for field in required:
        payload = {"name": "KBC Lint", **{key: value for key, value in required.items() if key != field}}
        assert client.post("/api/modules/module-9/products", json=payload).status_code == 422
        assert client.put(f"/api/modules/module-9/products/{product.id}", json=payload).status_code == 422


def test_product_cost_must_not_be_negative_and_can_be_cleared(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    required = _required_fields(db_session)

    negative = client.post("/api/modules/module-9/products", json={"name": "KBC Lint", **required, "cost": -1})
    negative_max = client.post(
        "/api/modules/module-9/products", json={"name": "KBC Lint", **required, "limit_value": -1}
    )
    negative_initial = client.post(
        "/api/modules/module-9/products", json={"name": "KBC Lint", **required, "max_initial_stock": -1}
    )
    created = client.post(
        "/api/modules/module-9/products",
        json={"name": "KBC Lint", **required, "cost": 3.99, "limit_value": 5, "max_initial_stock": 4},
    )
    product_id = created.json()["id"]
    cleared = client.put(
        f"/api/modules/module-9/products/{product_id}",
        json={"name": "KBC Lint", **required, "cost": None, "is_tag_managed": True},
    )

    assert negative.status_code == 422
    assert negative_max.status_code == 422
    assert negative_initial.status_code == 422
    assert created.json()["cost"] == 3.99
    assert created.json()["limit_value"] == 5
    assert created.json()["max_initial_stock"] == 4
    assert created.json()["is_tag_managed"] is False
    assert cleared.status_code == 200
    assert cleared.json()["cost"] is None
    assert cleared.json()["max_initial_stock"] is None
    assert cleared.json()["is_tag_managed"] is True


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
    required = _required_fields(db_session)
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-9/products/{product.id}",
        json={"name": "KBC Lint 2", "is_blocked": True, **required},
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
    required = _required_fields(db_session)
    _login(client, "admin@example.com")

    response = client.put("/api/modules/module-9/products/999", json={"name": "Nope", **required})

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


# ---- Product picture --------------------------------------------------------

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-body"


def _login_super_admin(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")


def test_upload_and_read_back_a_product_image(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    product = _create_product(db_session)

    # A new product has no picture yet.
    assert client.get("/api/modules/module-9/products").json()[0]["has_image"] is False
    assert client.get(f"/api/modules/module-9/products/{product.id}/image").status_code == 404

    response = client.put(
        f"/api/modules/module-9/products/{product.id}/image",
        files={"image": ("photo.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["has_image"] is True
    assert response.json()["image_updated_at"] is not None
    image = client.get(f"/api/modules/module-9/products/{product.id}/image")
    assert image.status_code == 200
    assert image.content == PNG_BYTES
    assert image.headers["content-type"] == "image/png"


def test_product_image_must_be_an_image(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    product = _create_product(db_session)

    response = client.put(
        f"/api/modules/module-9/products/{product.id}/image",
        files={"image": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400


def test_product_image_must_be_smaller_than_5_mb(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    product = _create_product(db_session)

    response = client.put(
        f"/api/modules/module-9/products/{product.id}/image",
        files={"image": ("big.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )

    assert response.status_code == 400


def test_delete_product_image_keeps_the_product(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    product = _create_product(db_session)
    client.put(
        f"/api/modules/module-9/products/{product.id}/image",
        files={"image": ("photo.png", PNG_BYTES, "image/png")},
    )

    response = client.delete(f"/api/modules/module-9/products/{product.id}/image")

    assert response.status_code == 200
    assert response.json()["has_image"] is False
    assert client.get(f"/api/modules/module-9/products/{product.id}/image").status_code == 404
    assert len(client.get("/api/modules/module-9/products").json()) == 1


def test_create_only_role_can_attach_an_image_but_view_only_cannot(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    creator = _create_user(db_session, email="creator@example.com")
    viewer = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, creator, module)
    _grant_module_access(db_session, viewer, module)
    _grant_products_permission(db_session, creator, can_view=True, can_create=True)
    _grant_products_permission(db_session, viewer, can_view=True)
    product = _create_product(db_session)
    upload = {"image": ("photo.png", PNG_BYTES, "image/png")}

    _login(client, "viewer@example.com")
    assert client.put(f"/api/modules/module-9/products/{product.id}/image", files=upload).status_code == 403

    _login(client, "creator@example.com")
    assert client.put(f"/api/modules/module-9/products/{product.id}/image", files=upload).status_code == 200
    # Removing a picture needs "edit".
    assert client.delete(f"/api/modules/module-9/products/{product.id}/image").status_code == 403


def test_product_used_by_a_kar_or_rfid_tag_cannot_be_deleted(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    transport_type = _create_product(db_session, name="Pakket")
    tagged = _create_product(db_session, name="Lamp")
    kar_status = KarTrackerKarStatus(name="Beschikbaar")
    db_session.add(kar_status)
    db_session.flush()
    db_session.add(KarTrackerKar(kar_nummer="K1", status_id=kar_status.id, transport_type_id=transport_type.id))
    db_session.add(RfidTag(epc_uid="EPC1", assigned_product_id=tagged.id))
    db_session.commit()

    # A clear 400 instead of a database foreign-key error (500).
    kar_response = client.delete(f"/api/modules/module-9/products/{transport_type.id}")
    tag_response = client.delete(f"/api/modules/module-9/products/{tagged.id}")

    assert kar_response.status_code == 400
    assert "KarTracker" in kar_response.json()["detail"]
    assert tag_response.status_code == 400
    assert "RFID" in tag_response.json()["detail"]


def test_limit_is_required_and_percentage_needs_a_limit_value(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    required = _required_fields(db_session)
    percentage = ProductLimit(name="Percentage")
    db_session.add(percentage)
    db_session.commit()
    without_limit = {key: value for key, value in required.items() if key != "limit_id"}

    no_limit = client.post("/api/modules/module-9/products", json={"name": "KBC Lint", **without_limit})
    percentage_without_value = client.post(
        "/api/modules/module-9/products", json={"name": "KBC Lint", **required, "limit_id": percentage.id}
    )
    percentage_with_value = client.post(
        "/api/modules/module-9/products",
        json={"name": "KBC Lint", **required, "limit_id": percentage.id, "limit_value": 50},
    )
    # Other limits don't need a value.
    other_without_value = client.post("/api/modules/module-9/products", json={"name": "KBC Lint", **required})

    assert no_limit.status_code == 422
    assert percentage_without_value.status_code == 422
    assert percentage_with_value.status_code == 201
    assert percentage_with_value.json()["limit_value"] == 50
    assert other_without_value.status_code == 201
