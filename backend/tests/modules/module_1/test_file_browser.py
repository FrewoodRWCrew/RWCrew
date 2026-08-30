# Tests for TagScan's read-only Explorer-style file browser (the
# Dashboard screen's real content): folder tree, per-folder file listing,
# and file content preview — all gated by the existing "tagscan.dashboard"
# view permission, plus the path-traversal guard in file_browser.py.

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
from app.modules.module_1.screens import sync_screens


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
    module = Module(key="module-1", name="TagScan", sort_order=1)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _grant_dashboard_view(db_session: Session, user: User) -> None:
    role = TagscanRole(name="Viewer")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == "tagscan.dashboard"))
    db_session.add(TagscanRolePermission(role_id=role.id, screen_id=screen.id, can_view=True))
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


@pytest.fixture()
def source_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway folder standing in for the real TagScans directory,
    with one subfolder and a couple of files, for these tests to browse.
    """
    # Written as raw bytes (not write_text) so the exact content is known
    # regardless of the host OS's newline translation — the preview
    # endpoint reads bytes as-is, matching what a real CSV file would
    # look like verbatim.
    (tmp_path / "2026-08-23").mkdir()
    (tmp_path / "2026-08-23" / "scan.csv").write_bytes(b"EPC,RSSI\nABC123,70\n")
    (tmp_path / "root-file.csv").write_bytes(b"EPC,RSSI\nDEF456,80\n")

    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    return tmp_path


def _viewer_client(client: TestClient, db_session: Session) -> User:
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    _grant_dashboard_view(db_session, user)
    _login(client, "member@example.com")
    return user


def test_user_without_dashboard_permission_gets_403_on_every_endpoint(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "member@example.com")

    assert client.get("/api/modules/module-1/files/tree").status_code == 403
    assert client.get("/api/modules/module-1/files").status_code == 403
    assert client.get("/api/modules/module-1/files/content", params={"path": "root-file.csv"}).status_code == 403


def test_folder_tree_reflects_the_real_directory_structure(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.get("/api/modules/module-1/files/tree")

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == ""
    assert [child["name"] for child in body["children"]] == ["2026-08-23"]
    assert body["children"][0]["path"] == "2026-08-23"


def test_listing_files_returns_only_direct_children(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session)

    root_response = client.get("/api/modules/module-1/files")
    assert root_response.status_code == 200
    root_files = [entry["name"] for entry in root_response.json()]
    assert root_files == ["root-file.csv"]

    subfolder_response = client.get("/api/modules/module-1/files", params={"path": "2026-08-23"})
    assert subfolder_response.status_code == 200
    subfolder_files = [entry["name"] for entry in subfolder_response.json()]
    assert subfolder_files == ["scan.csv"]


def test_file_content_preview_returns_the_real_text(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.get("/api/modules/module-1/files/content", params={"path": "root-file.csv"})

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "EPC,RSSI\nDEF456,80\n"
    assert body["truncated"] is False


def test_path_traversal_attempt_is_rejected(client: TestClient, db_session: Session, source_dir: Path) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.get("/api/modules/module-1/files/content", params={"path": "../outside.txt"})

    assert response.status_code == 400


def test_missing_file_returns_404(client: TestClient, db_session: Session, source_dir: Path) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.get("/api/modules/module-1/files/content", params={"path": "does-not-exist.csv"})

    assert response.status_code == 404
