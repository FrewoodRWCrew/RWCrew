# Tests for the "Tag Headerdata" screen: scanning TagScan's "Unreaded
# Tags" intake subfolder for CSV files, logging each one exactly once
# (id, filename, created_at, line_count), and moving it into "Read
# Tags" — gated by the "tagscan.tag-headerdata" permission, independently
# of every other module_1 screen.

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
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
    module = Module(key="module-1", name="Tagscan", sort_order=1)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _grant_header_data_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_delete: bool = False,
) -> None:
    role = TagscanRole(name=f"Header Data Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == "tagscan.tag-headerdata"))
    db_session.add(
        TagscanRolePermission(
            role_id=role.id, screen_id=screen.id, can_view=can_view, can_create=can_create, can_delete=can_delete
        )
    )
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def _viewer_client(
    client: TestClient, db_session: Session, *, can_create: bool = True, can_delete: bool = False
) -> User:
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    _grant_header_data_permission(db_session, user, can_view=True, can_create=can_create, can_delete=can_delete)
    _login(client, "member@example.com")
    return user


@pytest.fixture()
def scan_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway folder standing in for the real TagScans directory,
    with an "Unreaded Tags" subfolder already present (mirroring the
    real setup) but "Read Tags" deliberately absent, so tests exercise
    the lazy folder-creation path by default.
    """
    (tmp_path / "Unreaded Tags").mkdir()
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    return tmp_path


def test_user_without_permission_gets_403_on_list_and_scan(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    assert client.get("/api/modules/module-1/header-data").status_code == 403
    assert client.post("/api/modules/module-1/header-data/scan").status_code == 403


def test_scan_with_no_unreaded_tags_folder_returns_empty_result(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No scan_dirs fixture here — the source root exists, but "Unreaded
    # Tags" itself does not.
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["entries"] == []


def test_scan_logs_new_csv_files_counts_data_lines_and_moves_them(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan_a.csv").write_bytes(b"EPC,RSSI\nA1,70\nA2,71\n")
    (scan_dirs / "Unreaded Tags" / "scan_b.csv").write_bytes(b"EPC,RSSI\nB1,80\nB2,81\nB3,82\nB4,83\nB5,84\n")
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 200
    body = response.json()
    outcomes_by_filename = {r["filename"]: r["outcome"] for r in body["results"]}
    assert outcomes_by_filename == {"scan_a.csv": "logged", "scan_b.csv": "logged"}

    # line_count is the number of DATA lines logged to Tag Linedata (the
    # CSV's own header row is never counted) — 2 and 5 here, matching how
    # many rows each file actually produced, not the raw physical line
    # count (3 and 6).
    line_counts_by_filename = {e["filename"]: e["line_count"] for e in body["entries"]}
    assert line_counts_by_filename == {"scan_a.csv": 2, "scan_b.csv": 5}

    assert not (scan_dirs / "Unreaded Tags" / "scan_a.csv").exists()
    assert not (scan_dirs / "Unreaded Tags" / "scan_b.csv").exists()
    assert (scan_dirs / "Read Tags" / "scan_a.csv").exists()
    assert (scan_dirs / "Read Tags" / "scan_b.csv").exists()

    list_response = client.get("/api/modules/module-1/header-data")
    assert list_response.status_code == 200
    assert {e["filename"] for e in list_response.json()} == {"scan_a.csv", "scan_b.csv"}


def test_line_count_excludes_the_header_row_and_a_trailing_blank_line(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    # 1 header row + 2 data rows + 1 trailing blank line = 4 physical
    # lines, but only 2 rows are ever logged to Tag Linedata — line_count
    # must match that 2, not the raw physical line count.
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(b"EPC,RSSI\nA1,70\nA2,71\n\n")
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 200
    assert response.json()["entries"][0]["line_count"] == 2


def test_scan_creates_read_tags_folder_if_missing(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    assert not (scan_dirs / "Read Tags").exists()
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(b"EPC,RSSI\nA1,70\n")
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 200
    assert (scan_dirs / "Read Tags" / "scan.csv").exists()


def test_scan_ignores_non_csv_files(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(b"EPC,RSSI\nA1,70\n")
    (scan_dirs / "Unreaded Tags" / "notes.txt").write_bytes(b"not a csv file")
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 200
    filenames = {r["filename"] for r in response.json()["results"]}
    assert filenames == {"scan.csv"}
    assert (scan_dirs / "Unreaded Tags" / "notes.txt").exists()


def test_second_scan_does_not_relog_an_already_processed_file(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(b"EPC,RSSI\nA1,70\n")
    sync_screens(db_session)
    _viewer_client(client, db_session)

    first = client.post("/api/modules/module-1/header-data/scan")
    assert first.json()["results"][0]["outcome"] == "logged"

    # Simulate the same filename being re-delivered into Unreaded Tags.
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(b"EPC,RSSI\nA1,70\n")
    second = client.post("/api/modules/module-1/header-data/scan")

    assert second.status_code == 200
    assert second.json()["results"] == [
        {"filename": "scan.csv", "outcome": "skipped_duplicate", "detail": "This file was already logged"}
    ]
    # The duplicate is left in place — never silently deleted or moved.
    assert (scan_dirs / "Unreaded Tags" / "scan.csv").exists()
    # Only one row was ever logged for this filename.
    rows = db_session.scalars(select(TagHeaderData).where(TagHeaderData.filename == "scan.csv")).all()
    assert len(rows) == 1


def test_duplicate_filename_race_is_handled_via_integrity_error(
    client: TestClient, db_session: Session, scan_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A genuine TOCTOU race: another request's INSERT lands between this
    # scan's "already logged?" pre-check and its own commit. The pre-check
    # alone can never catch that — only the DB's own unique constraint
    # can — so the pre-check is forced here to (wrongly) report "not
    # found" while the conflicting row is already committed, proving the
    # `except IntegrityError` branch itself handles it, not just the
    # pre-check (which a naive test could satisfy without ever reaching
    # that branch, by pre-inserting the row before the pre-check runs).
    db_session.add(TagHeaderData(filename="dup.csv", line_count=1))
    db_session.commit()
    (scan_dirs / "Unreaded Tags" / "dup.csv").write_bytes(b"EPC,RSSI\nA1,70\n")
    sync_screens(db_session)
    _viewer_client(client, db_session)

    original_scalar = db_session.scalar

    def scalar_that_misses_the_race(statement, *args, **kwargs):
        froms = statement.get_final_froms() if hasattr(statement, "get_final_froms") else []
        if any(getattr(table, "name", None) == "Tagscan_header_data" for table in froms):
            return None
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(db_session, "scalar", scalar_that_misses_the_race)

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 200
    assert response.json()["results"] == [
        {"filename": "dup.csv", "outcome": "skipped_duplicate", "detail": "This file was already logged"}
    ]
    rows = db_session.scalars(select(TagHeaderData).where(TagHeaderData.filename == "dup.csv")).all()
    assert len(rows) == 1


def test_view_only_permission_cannot_trigger_scan(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session, can_create=False)

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 403


def test_super_admin_can_scan_without_explicit_role(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(b"EPC,RSSI\nA1,70\n")
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-1/header-data/scan")

    assert response.status_code == 200
    assert response.json()["results"][0]["outcome"] == "logged"


def test_list_header_data_ordered_newest_first(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session)
    # Explicit, distinct timestamps — SQLite's CURRENT_TIMESTAMP only has
    # one-second resolution, so relying on server_default alone for two
    # inserts made back-to-back would be flaky.
    db_session.add(TagHeaderData(filename="first.csv", line_count=1, created_at=datetime(2026, 1, 1, 10, 0, 0)))
    db_session.add(TagHeaderData(filename="second.csv", line_count=2, created_at=datetime(2026, 1, 1, 10, 0, 1)))
    db_session.commit()

    response = client.get("/api/modules/module-1/header-data")

    assert response.status_code == 200
    assert [e["filename"] for e in response.json()] == ["second.csv", "first.csv"]


def test_delete_removes_header_and_its_line_rows_and_allows_relogging(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        b"Scanner,EPC,RSSI (raw),Antenna,Count,Last Seen\nScan_01,E2AAA,78,1,92,10:36:07\n"
    )
    sync_screens(db_session)
    _viewer_client(client, db_session, can_delete=True)
    client.post("/api/modules/module-1/header-data/scan")
    header = db_session.scalar(select(TagHeaderData).where(TagHeaderData.filename == "scan.csv"))
    assert db_session.scalar(select(TagLineData).where(TagLineData.header_data_id == header.id)) is not None

    response = client.delete(f"/api/modules/module-1/header-data/{header.id}")

    assert response.status_code == 204
    assert db_session.get(TagHeaderData, header.id) is None
    assert db_session.scalar(select(TagLineData).where(TagLineData.header_data_id == header.id)) is None

    # The physical file was left untouched (already moved to Read Tags by
    # the scan) — delete only removes the database rows.
    assert (scan_dirs / "Read Tags" / "scan.csv").exists()

    # Dropping the same filename back into Unreaded Tags and scanning
    # again now logs it as new, rather than "already logged".
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        b"Scanner,EPC,RSSI (raw),Antenna,Count,Last Seen\nScan_01,E2AAA,78,1,92,10:36:07\n"
    )
    rescan = client.post("/api/modules/module-1/header-data/scan")
    assert rescan.json()["results"] == [{"filename": "scan.csv", "outcome": "logged", "detail": None}]


def test_deleting_an_unknown_header_row_returns_404(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session, can_delete=True)

    response = client.delete("/api/modules/module-1/header-data/999")

    assert response.status_code == 404


def test_view_only_permission_cannot_delete(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session, can_delete=False)
    db_session.add(TagHeaderData(filename="scan.csv", line_count=1))
    db_session.commit()

    response = client.delete("/api/modules/module-1/header-data/1")

    assert response.status_code == 403


# --- PDF summary -------------------------------------------------------


def test_pdf_download_returns_a_valid_pdf(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    product = Product(name="KBC Lint")
    db_session.add(product)
    db_session.commit()
    db_session.add(RfidTag(epc_uid="E2AAA", assigned_product_id=product.id))
    db_session.commit()

    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        b"Scanner,EPC,RSSI (raw),Antenna,Count,Last Seen\n"
        b"Scan_01,E2AAA,78,1,92,10:36:07\n"
        b"Scan_01,E2ZZZ,78,1,92,10:36:08\n"
    )
    sync_screens(db_session)
    _viewer_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")
    header = db_session.scalar(select(TagHeaderData))

    response = client.get(f"/api/modules/module-1/header-data/{header.id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_pdf_content_disposition_escapes_special_characters_in_filename(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    # A raw quote/backslash can never come from a real Windows-sourced
    # filename, but the header-building code must never produce a
    # broken/injectable Content-Disposition header for any string it's
    # given — insert one directly rather than via a real scan.
    header = TagHeaderData(filename='weird"name\\.csv', line_count=0)
    db_session.add(header)
    db_session.commit()
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.get(f"/api/modules/module-1/header-data/{header.id}/pdf")

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    # Exactly the two quotes surrounding filename="..." — none embedded
    # from the filename itself, so nothing can break out of that value.
    assert disposition.count('"') == 2
    assert "filename*=UTF-8''" in disposition


def test_pdf_download_for_unknown_header_returns_404(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_screens(db_session)
    _viewer_client(client, db_session)

    response = client.get("/api/modules/module-1/header-data/999/pdf")

    assert response.status_code == 404


def test_user_without_permission_cannot_download_pdf(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")
    db_session.add(TagHeaderData(filename="scan.csv", line_count=1))
    db_session.commit()

    response = client.get("/api/modules/module-1/header-data/1/pdf")

    assert response.status_code == 403
