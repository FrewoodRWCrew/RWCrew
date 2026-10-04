# Tests for TagScan's automatic background Scan (auto_scan.py): its
# settings on the Settings screen (defaults, validation, permissions) and
# one run of the job — scans when on and due, does nothing when switched
# off or when the interval hasn't passed yet.

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tagscan_settings import TagscanSettings
from app.modules.module_1.auto_scan import run_auto_scan_once
from app.modules.module_1.screens import sync_screens
from tests.modules.module_1.test_settings import (
    _create_tagscan_module,
    _create_user,
    _grant_module_access,
    _grant_settings_permission,
    _login,
)

BASE = "/api/modules/module-1"
CSV = "Scanner,EPC,RSSI (raw),Antenna,Count,Last Seen\nScan_01,E2AAA,78,1,92,10:36:07\n"


@pytest.fixture()
def source_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "Unreaded Tags").mkdir()
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    return tmp_path


def _factory(db_session: Session):
    """A session factory handing out the test's own session (not closed)."""
    return lambda: nullcontext(db_session)


def _admin(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")


def test_settings_show_auto_scan_defaults_when_nothing_saved(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _admin(client, db_session)

    body = client.get(f"{BASE}/settings").json()

    assert body["auto_scan_enabled"] is True
    assert body["auto_scan_interval_seconds"] == 60
    assert body["last_auto_scan_at"] is None


def test_saving_auto_scan_settings(client: TestClient, db_session: Session, source_dir: Path) -> None:
    _admin(client, db_session)

    response = client.put(f"{BASE}/settings/auto-scan", json={"enabled": False, "interval_seconds": 300})

    assert response.status_code == 200
    body = client.get(f"{BASE}/settings").json()
    assert (body["auto_scan_enabled"], body["auto_scan_interval_seconds"]) == (False, 300)
    # The receive folder still falls back to the .env default.
    assert body["is_override"] is False


def test_auto_scan_interval_must_be_at_least_ten_seconds(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _admin(client, db_session)

    response = client.put(f"{BASE}/settings/auto-scan", json={"enabled": True, "interval_seconds": 5})

    assert response.status_code == 422


def test_view_only_permission_cannot_change_auto_scan(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_settings_permission(db_session, user, can_view=True)
    _login(client, "viewer@example.com")

    response = client.put(f"{BASE}/settings/auto-scan", json={"enabled": False, "interval_seconds": 60})

    assert response.status_code == 403


def test_run_scans_new_csv_and_records_the_run(db_session: Session, source_dir: Path) -> None:
    (source_dir / "Unreaded Tags" / "scan.csv").write_text(CSV)
    sync_screens(db_session)

    ran = run_auto_scan_once(_factory(db_session))

    assert ran is True
    assert db_session.scalar(select(TagHeaderData.filename)) == "scan.csv"
    assert (source_dir / "Read Tags" / "scan.csv").is_file()
    row = db_session.get(TagscanSettings, 1)
    assert row.last_auto_scan_at is not None
    assert row.last_auto_scan_summary == "1 logged, 0 skipped, 0 errors"


def test_run_does_nothing_when_switched_off(db_session: Session, source_dir: Path) -> None:
    (source_dir / "Unreaded Tags" / "scan.csv").write_text(CSV)
    db_session.add(TagscanSettings(id=1, auto_scan_enabled=False, auto_scan_interval_seconds=60))
    db_session.commit()

    assert run_auto_scan_once(_factory(db_session)) is False
    assert db_session.scalar(select(TagHeaderData)) is None
    assert (source_dir / "Unreaded Tags" / "scan.csv").is_file()


def test_run_waits_for_the_interval(db_session: Session, source_dir: Path) -> None:
    last_run = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    db_session.add(
        TagscanSettings(id=1, auto_scan_enabled=True, auto_scan_interval_seconds=60, last_auto_scan_at=last_run)
    )
    db_session.commit()

    # 30 s later: not due yet; 61 s later: due.
    assert run_auto_scan_once(_factory(db_session), now=last_run + timedelta(seconds=30)) is False
    assert run_auto_scan_once(_factory(db_session), now=last_run + timedelta(seconds=61)) is True
