# These tests check the "Scanners" master-data screen: gated by normal
# module access + the "tagscan.scanners" permission, independently of
# "tagscan.tag-management"/others, with a super-admin bypass, full CRUD,
# and a delete guard while a scanner is still referenced by logged CSV
# data — mirrors test_tags.py's shape.

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.product_type import ProductType
from app.db.models.scanner import Scanner
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tagscan_role import TagscanRole
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_1.screens import sync_screens as sync_tagscan_screens


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


def _create_tagscan_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-1"))
    if module is not None:
        return module
    module = Module(key="module-1", name="Tagscan", sort_order=1)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _grant_screen_permission(
    db_session: Session,
    user: User,
    screen_key: str,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = TagscanRole(name=f"{screen_key} Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == screen_key))
    db_session.add(
        TagscanRolePermission(
            role_id=role.id,
            screen_id=screen.id,
            can_view=can_view,
            can_create=can_create,
            can_edit=can_edit,
            can_delete=can_delete,
        )
    )
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _grant_scanner_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    _grant_screen_permission(
        db_session,
        user,
        "tagscan.scanners",
        can_view=can_view,
        can_create=can_create,
        can_edit=can_edit,
        can_delete=can_delete,
    )


def _create_product_type(db_session: Session, *, name: str = "Reader Hardware") -> ProductType:
    product_type = ProductType(name=name)
    db_session.add(product_type)
    db_session.commit()
    db_session.refresh(product_type)
    return product_type


def _create_scanner(
    db_session: Session,
    *,
    scanner: str = "Scan-01",
    type_id: int,
    technology: str = "Raspberry Pi 4",
) -> Scanner:
    row = Scanner(scanner=scanner, type_id=type_id, technology=technology)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_user_without_module_access_cannot_list_scanners(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    _create_tagscan_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-1/scanners")

    assert response.status_code == 403


def test_user_with_access_but_no_scanners_permission_cannot_list_scanners(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-1/scanners")

    assert response.status_code == 403


def test_scanners_permission_does_not_grant_access_to_tag_management_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_scanner_permission(db_session, user, can_view=True, can_create=True)
    _login(client, "viewer@example.com")

    assert client.get("/api/modules/module-1/scanners").status_code == 200
    assert client.get("/api/modules/module-1/tags").status_code == 403


def test_super_admin_can_create_a_scanner_without_an_explicit_role(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={"scanner": "Scan-01", "type_id": product_type.id, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["scanner"] == "Scan-01"
    assert body["type_id"] == product_type.id
    assert body["technology"] == "Raspberry Pi 4"


def test_view_only_scanners_permission_cannot_create_a_scanner(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_scanner_permission(db_session, user, can_view=True)
    product_type = _create_product_type(db_session)
    _login(client, "viewer@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={"scanner": "Scan-01", "type_id": product_type.id, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 403


def test_view_only_scanners_permission_cannot_update_or_delete(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_scanner_permission(db_session, user, can_view=True)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    _login(client, "viewer@example.com")

    update_response = client.put(
        f"/api/modules/module-1/scanners/{scanner.id}",
        json={"scanner": "Scan-01", "type_id": product_type.id, "technology": "Raspberry Pi 5"},
    )
    delete_response = client.delete(f"/api/modules/module-1/scanners/{scanner.id}")

    assert update_response.status_code == 403
    assert delete_response.status_code == 403


def test_create_scanner_with_full_field_set(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={
            "scanner": "Scan-01",
            "type_id": product_type.id,
            "technology": "Raspberry Pi 5",
            "location": "Warehouse A, Dock 3",
            "description": "Main intake reader",
            "info1": "info one",
            "info2": "info two",
            "info3": "info three",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["technology"] == "Raspberry Pi 5"
    assert body["location"] == "Warehouse A, Dock 3"
    assert body["description"] == "Main intake reader"
    assert body["info1"] == "info one"
    assert body["info2"] == "info two"
    assert body["info3"] == "info three"


def test_creating_a_scanner_strips_whitespace_from_the_name(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={"scanner": "  Scan-01\t", "type_id": product_type.id, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 201
    assert response.json()["scanner"] == "Scan-01"


def test_creating_a_scanner_with_an_invalid_technology_returns_422(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={"scanner": "Scan-01", "type_id": product_type.id, "technology": "Raspberry Pi 2"},
    )

    assert response.status_code == 422


def test_creating_a_scanner_without_a_type_id_returns_422(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={"scanner": "Scan-01", "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 422


def test_creating_a_scanner_with_an_unknown_type_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={"scanner": "Scan-01", "type_id": 999, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 404


def test_creating_a_scanner_with_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _create_scanner(db_session, scanner="Scan-01", type_id=product_type.id)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/scanners",
        json={"scanner": "Scan-01", "type_id": product_type.id, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 409


def test_list_scanners_ordered_by_name(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _create_scanner(db_session, scanner="Scan-ZZZ", type_id=product_type.id)
    _create_scanner(db_session, scanner="Scan-AAA", type_id=product_type.id)
    _login(client, "admin@example.com")

    response = client.get("/api/modules/module-1/scanners")

    assert response.status_code == 200
    assert [row["scanner"] for row in response.json()] == ["Scan-AAA", "Scan-ZZZ"]


def test_super_admin_can_update_a_scanner(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, scanner="Scan-01", type_id=product_type.id)
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-1/scanners/{scanner.id}",
        json={
            "scanner": "Scan-01-Renamed",
            "type_id": product_type.id,
            "technology": "Raspberry Pi 5",
            "location": "New location",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scanner"] == "Scan-01-Renamed"
    assert body["technology"] == "Raspberry Pi 5"
    assert body["location"] == "New location"


def test_updating_a_missing_scanner_returns_404(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _login(client, "admin@example.com")

    response = client.put(
        "/api/modules/module-1/scanners/999",
        json={"scanner": "Nope", "type_id": product_type.id, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 404


def test_updating_a_scanner_with_an_unknown_type_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-1/scanners/{scanner.id}",
        json={"scanner": "Scan-01", "type_id": 999, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 404


def test_updating_a_scanner_to_a_name_colliding_with_another_returns_409(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    _create_scanner(db_session, scanner="Scan-01", type_id=product_type.id)
    scanner_2 = _create_scanner(db_session, scanner="Scan-02", type_id=product_type.id)
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-1/scanners/{scanner_2.id}",
        json={"scanner": "Scan-01", "type_id": product_type.id, "technology": "Raspberry Pi 4"},
    )

    assert response.status_code == 409


def test_super_admin_can_delete_an_unused_scanner(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-1/scanners/{scanner.id}")

    assert response.status_code == 204
    assert client.get("/api/modules/module-1/scanners").json() == []


def test_deleting_a_missing_scanner_returns_404(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.delete("/api/modules/module-1/scanners/999")

    assert response.status_code == 404


def test_generating_an_api_key_requires_edit_permission(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_scanner_permission(db_session, user, can_view=True)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    _login(client, "viewer@example.com")

    response = client.post(f"/api/modules/module-1/scanners/{scanner.id}/api-key")

    assert response.status_code == 403


def test_generating_an_api_key_returns_a_usable_plaintext_key_once(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    _login(client, "admin@example.com")

    response = client.post(f"/api/modules/module-1/scanners/{scanner.id}/api-key")

    assert response.status_code == 200
    api_key = response.json()["api_key"]
    assert api_key.startswith(f"module1_{scanner.id}_")

    listed = client.get("/api/modules/module-1/scanners").json()[0]
    assert listed["has_api_key"] is True
    assert listed["api_key_last_used_at"] is None


def test_generating_a_new_api_key_invalidates_the_previous_one(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    _login(client, "admin@example.com")

    first_key = client.post(f"/api/modules/module-1/scanners/{scanner.id}/api-key").json()["api_key"]
    second_key = client.post(f"/api/modules/module-1/scanners/{scanner.id}/api-key").json()["api_key"]

    first_attempt = client.post(
        "/api/public/tagscan-intake",
        headers={"X-API-Key": first_key},
        files={"file": ("scan.csv", b"EPC,RSSI\n", "text/csv")},
    )
    second_attempt = client.post(
        "/api/public/tagscan-intake",
        headers={"X-API-Key": second_key},
        files={"file": ("scan.csv", b"EPC,RSSI\n", "text/csv")},
    )

    assert first_attempt.status_code == 401
    assert second_attempt.status_code == 201


def test_revoking_an_api_key_blocks_further_uploads(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    _login(client, "admin@example.com")

    api_key = client.post(f"/api/modules/module-1/scanners/{scanner.id}/api-key").json()["api_key"]
    revoke_response = client.delete(f"/api/modules/module-1/scanners/{scanner.id}/api-key")
    upload_response = client.post(
        "/api/public/tagscan-intake",
        headers={"X-API-Key": api_key},
        files={"file": ("scan.csv", b"EPC,RSSI\n", "text/csv")},
    )

    assert revoke_response.status_code == 204
    assert upload_response.status_code == 401
    assert client.get("/api/modules/module-1/scanners").json()[0]["has_api_key"] is False


def test_deleting_a_scanner_still_referenced_by_a_header_row_returns_400(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    product_type = _create_product_type(db_session)
    scanner = _create_scanner(db_session, type_id=product_type.id)
    db_session.add(
        TagHeaderData(
            filename="Reader-Log.csv",
            line_count=1,
            scanner="Scan-01",
            scanner_id=scanner.id,
            scanner_name=scanner.scanner,
            scanner_location=scanner.location,
            scanner_technology=scanner.technology,
        )
    )
    db_session.commit()
    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-1/scanners/{scanner.id}")

    assert response.status_code == 400
