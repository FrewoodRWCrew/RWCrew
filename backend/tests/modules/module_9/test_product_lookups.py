# These tests check the four product lookup screens — Type, Magazijn
# (Warehouse), Categorie (ProductCategory), and Limiet (ProductLimit) —
# nested under Products. All four share the exact same bare id+unique-name
# shape and endpoint behavior as Season (see test_season.py), so their CRUD
# + permission-gating behavior is tested once via parametrize instead of
# copy-pasted four times; what's specific to each — how Product actually
# references it — is tested separately below.

import pytest
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
from app.db.models.product_limit import ProductLimit
from app.db.models.product_type import ProductType
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.db.models.warehouse import Warehouse
from app.modules.module_9.screens import sync_screens

LOOKUP_ENTITIES = [
    ("product-types", "masterdata.product-types"),
    ("warehouses", "masterdata.warehouses"),
    ("product-categories", "masterdata.product-categories"),
    ("product-limits", "masterdata.product-limits"),
]

LOOKUP_FIELDS = [
    ("product-types", "type_id", ProductType),
    ("warehouses", "warehouse_id", Warehouse),
    ("product-categories", "category_id", ProductCategory),
    ("product-limits", "limit_id", ProductLimit),
]


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


def _grant_permission(
    db_session: Session,
    user: User,
    screen_key: str,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = MasterDataRole(name=f"{screen_key} Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == screen_key))
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


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


@pytest.mark.parametrize("path_segment,screen_key", LOOKUP_ENTITIES)
def test_user_without_permission_cannot_list(
    client: TestClient, db_session: Session, path_segment: str, screen_key: str
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.get(f"/api/modules/module-9/{path_segment}")

    assert response.status_code == 403


@pytest.mark.parametrize("path_segment,screen_key", LOOKUP_ENTITIES)
def test_super_admin_can_create_list_rename_and_delete(
    client: TestClient, db_session: Session, path_segment: str, screen_key: str
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    create_response = client.post(f"/api/modules/module-9/{path_segment}", json={"name": "Alpha"})
    assert create_response.status_code == 201
    entity_id = create_response.json()["id"]

    list_response = client.get(f"/api/modules/module-9/{path_segment}")
    assert list_response.status_code == 200
    assert [row["name"] for row in list_response.json()] == ["Alpha"]

    update_response = client.put(f"/api/modules/module-9/{path_segment}/{entity_id}", json={"name": "Beta"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Beta"

    delete_response = client.delete(f"/api/modules/module-9/{path_segment}/{entity_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/modules/module-9/{path_segment}").json() == []


@pytest.mark.parametrize("path_segment,screen_key", LOOKUP_ENTITIES)
def test_view_only_permission_cannot_create(
    client: TestClient, db_session: Session, path_segment: str, screen_key: str
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_permission(db_session, user, screen_key, can_view=True)
    _login(client, "viewer@example.com")

    response = client.post(f"/api/modules/module-9/{path_segment}", json={"name": "Alpha"})

    assert response.status_code == 403


@pytest.mark.parametrize("path_segment,screen_key", LOOKUP_ENTITIES)
def test_creating_a_duplicate_name_is_rejected(
    client: TestClient, db_session: Session, path_segment: str, screen_key: str
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    client.post(f"/api/modules/module-9/{path_segment}", json={"name": "Alpha"})
    response = client.post(f"/api/modules/module-9/{path_segment}", json={"name": "Alpha"})

    assert response.status_code == 409


@pytest.mark.parametrize("path_segment,screen_key", LOOKUP_ENTITIES)
def test_renaming_or_deleting_a_missing_entity_returns_404(
    client: TestClient, db_session: Session, path_segment: str, screen_key: str
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    assert client.put(f"/api/modules/module-9/{path_segment}/999", json={"name": "Nope"}).status_code == 404
    assert client.delete(f"/api/modules/module-9/{path_segment}/999").status_code == 404


# --- How Product actually references these lookups -----------------------


@pytest.mark.parametrize("path_segment,field_name,model", LOOKUP_FIELDS)
def test_creating_a_product_with_an_unknown_lookup_id_returns_404(
    client: TestClient, db_session: Session, path_segment: str, field_name: str, model: type
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/products", json={"name": "KBC Lint", field_name: 999})

    assert response.status_code == 404


@pytest.mark.parametrize("path_segment,field_name,model", LOOKUP_FIELDS)
def test_deleting_a_lookup_value_still_used_by_a_product_is_rejected(
    client: TestClient, db_session: Session, path_segment: str, field_name: str, model: type
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    entity = model(name="Alpha")
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)

    db_session.add(Product(name="KBC Lint", **{field_name: entity.id}))
    db_session.commit()

    response = client.delete(f"/api/modules/module-9/{path_segment}/{entity.id}")

    assert response.status_code == 400
