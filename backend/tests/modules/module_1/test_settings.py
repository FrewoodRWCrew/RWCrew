# Tests for TagScan's "Settings" screen: the DB-backed override of the
# receive-folder path (falling back to the .env-configured default), gated
# by the "tagscan.settings" permission independently of every other screen
# — see app/modules/module_1/router.py's get_settings/update_settings.

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.tagscan_role import TagscanRole
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_1.screens import sync_screens as sync_tagscan_screens


def _create_user(db_session: Session, *, email: str, is_super_admin: bool = False) -> User:
    user = User(email=email, hashed_password=hash_password("password123"), display_name=email, is_super_admin=is_super_admin)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_tagscan_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-1"))
    if module is not None:
        return module
    module = Module(key="module-1", name="TagScan", sort_order=1)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _grant_settings_permission(
    db_session: Session, user: User, *, can_view: bool = False, can_edit: bool = False
) -> None:
    role = TagscanRole(name=f"Settings Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == "tagscan.settings"))
    db_session.add(
        TagscanRolePermission(role_id=role.id, screen_id=screen.id, can_view=can_view, can_edit=can_edit)
    )
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


@pytest.fixture()
def default_source_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path / "default-intake"))
    return tmp_path


def test_user_without_settings_permission_cannot_view_settings(
    client: TestClient, db_session: Session, default_source_dir: Path
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "member@example.com")

    response = client.get("/api/modules/module-1/settings")

    assert response.status_code == 403


def test_get_settings_returns_env_default_when_nothing_saved(
    client: TestClient, db_session: Session, default_source_dir: Path
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_settings_permission(db_session, user, can_view=True)
    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-1/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["receive_folder_path"] == settings.tagscan_source_dir
    assert body["is_override"] is False


def test_view_only_permission_cannot_update_settings(
    client: TestClient, db_session: Session, default_source_dir: Path
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_settings_permission(db_session, user, can_view=True)
    _login(client, "viewer@example.com")

    response = client.put(
        "/api/modules/module-1/settings",
        json={"receive_folder_path": str(default_source_dir / "custom")},
    )

    assert response.status_code == 403


def test_saving_a_new_receive_folder_is_reflected_on_get(
    client: TestClient, db_session: Session, default_source_dir: Path
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")
    custom_path = default_source_dir / "custom-intake"

    update_response = client.put("/api/modules/module-1/settings", json={"receive_folder_path": str(custom_path)})
    get_response = client.get("/api/modules/module-1/settings")

    assert update_response.status_code == 200
    assert update_response.json() == {"receive_folder_path": str(custom_path), "is_override": True}
    assert get_response.json() == {"receive_folder_path": str(custom_path), "is_override": True}
    # The endpoint actually created the folder, failing fast if it couldn't.
    assert custom_path.is_dir()


def test_saved_override_is_what_the_file_browser_and_scan_actually_use(
    client: TestClient, db_session: Session, default_source_dir: Path
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")
    custom_path = default_source_dir / "custom-intake"
    (custom_path / "Unreaded Tags").mkdir(parents=True)
    (custom_path / "Unreaded Tags" / "root-file.csv").write_bytes(b"EPC,RSSI\nABC,1\n")

    client.put("/api/modules/module-1/settings", json={"receive_folder_path": str(custom_path)})
    files_response = client.get("/api/modules/module-1/files", params={"path": "Unreaded Tags"})

    assert files_response.status_code == 200
    assert [entry["name"] for entry in files_response.json()] == ["root-file.csv"]
