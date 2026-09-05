# These tests check TagScan's landing dashboard: aggregate KPI stats
# gated by plain module access (no specific screen permission, matching
# the unconditional placeholder page it replaces).

from datetime import date, datetime, timedelta, timezone
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
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_1.screens import sync_screens as sync_tagscan_screens
from app.modules.module_1.tag_dashboard import WEEKS_OF_HISTORY, _week_start


@pytest.fixture()
def scan_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway folder standing in for the real TagScans directory,
    with an "Unreaded Tags" subfolder already present (mirroring the
    real setup — see test_header_data.py's identical fixture).
    """
    (tmp_path / "Unreaded Tags").mkdir()
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    return tmp_path


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


def _create_product(db_session: Session, *, name: str) -> Product:
    product = Product(name=name)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _create_tag(
    db_session: Session,
    *,
    epc_uid: str,
    status: str = "active",
    assigned_product_id: int | None = None,
    date_registered: datetime | None = None,
) -> RfidTag:
    tag = RfidTag(epc_uid=epc_uid, status=status, assigned_product_id=assigned_product_id)
    if date_registered is not None:
        tag.date_registered = date_registered
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_dashboard_requires_module_access(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    _create_tagscan_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-1/dashboard")

    assert response.status_code == 403


def test_dashboard_with_no_tags_returns_all_zero_stats(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-1/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["total_tags"] == 0
    assert body["unreaded_tags_count"] == 0
    assert body["assigned_tags"] == 0
    assert body["unassigned_tags"] == 0
    assert body["lost_or_damaged_tags"] == 0
    assert body["registered_this_month"] == 0
    assert [item["count"] for item in body["status_breakdown"]] == [0, 0, 0, 0, 0]
    assert len(body["registrations_by_week"]) == WEEKS_OF_HISTORY
    assert all(item["count"] == 0 for item in body["registrations_by_week"])
    assert body["top_products"] == []


def test_dashboard_unreaded_tags_count_reflects_csv_files_in_unreaded_tags(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    (scan_dirs / "Unreaded Tags" / "scan_a.csv").write_bytes(b"EPC,RSSI\nA1,70\n")
    (scan_dirs / "Unreaded Tags" / "scan_b.csv").write_bytes(b"EPC,RSSI\nB1,80\n")
    # A non-CSV file sitting in the folder must not be counted — it would
    # never be picked up by the "Tag Headerdata" screen's scan either.
    (scan_dirs / "Unreaded Tags" / "notes.txt").write_bytes(b"not a csv file")

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-1/dashboard")

    assert response.status_code == 200
    assert response.json()["unreaded_tags_count"] == 2


def test_dashboard_computes_counts_and_status_breakdown(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    product = _create_product(db_session, name="KBC Lint")

    _create_tag(db_session, epc_uid="E1", status="active", assigned_product_id=product.id)
    _create_tag(db_session, epc_uid="E2", status="active")
    _create_tag(db_session, epc_uid="E3", status="inactive")
    _create_tag(db_session, epc_uid="E4", status="lost")
    _create_tag(db_session, epc_uid="E5", status="damaged")
    _create_tag(db_session, epc_uid="E6", status="retired")

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-1/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["total_tags"] == 6
    assert body["assigned_tags"] == 1
    assert body["unassigned_tags"] == 5
    assert body["lost_or_damaged_tags"] == 2

    breakdown = {item["status"]: item["count"] for item in body["status_breakdown"]}
    assert breakdown == {"active": 2, "inactive": 1, "lost": 1, "damaged": 1, "retired": 1}


def test_dashboard_registered_this_month_only_counts_current_month(
    client: TestClient, db_session: Session
) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    now = datetime.now(timezone.utc)
    this_month = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    last_month = (this_month - timedelta(days=1)).replace(day=1)

    _create_tag(db_session, epc_uid="E1", date_registered=this_month)
    _create_tag(db_session, epc_uid="E2", date_registered=last_month)

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-1/dashboard")

    assert response.status_code == 200
    assert response.json()["registered_this_month"] == 1


def test_dashboard_top_products_ordered_by_tag_count(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    popular = _create_product(db_session, name="Popular Product")
    quiet = _create_product(db_session, name="Quiet Product")

    _create_tag(db_session, epc_uid="E1", assigned_product_id=popular.id)
    _create_tag(db_session, epc_uid="E2", assigned_product_id=popular.id)
    _create_tag(db_session, epc_uid="E3", assigned_product_id=popular.id)
    _create_tag(db_session, epc_uid="E4", assigned_product_id=quiet.id)
    _create_tag(db_session, epc_uid="E5")  # unassigned — must not show up as a "product"

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-1/dashboard")

    assert response.status_code == 200
    top_products = response.json()["top_products"]
    assert top_products[0] == {"product_name": "Popular Product", "tag_count": 3}
    assert top_products[1] == {"product_name": "Quiet Product", "tag_count": 1}
    assert len(top_products) == 2


def test_dashboard_registrations_by_week_buckets_correctly(client: TestClient, db_session: Session) -> None:
    sync_tagscan_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    this_week_start = _week_start(date.today())
    last_week_start = this_week_start - timedelta(weeks=1)

    _create_tag(
        db_session,
        epc_uid="E1",
        date_registered=datetime.combine(this_week_start, datetime.min.time(), tzinfo=timezone.utc),
    )
    _create_tag(
        db_session,
        epc_uid="E2",
        date_registered=datetime.combine(this_week_start, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=2),
    )
    _create_tag(
        db_session,
        epc_uid="E3",
        date_registered=datetime.combine(last_week_start, datetime.min.time(), tzinfo=timezone.utc),
    )

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-1/dashboard")

    assert response.status_code == 200
    weeks = response.json()["registrations_by_week"]
    counts_by_week = {item["week_start"]: item["count"] for item in weeks}
    assert counts_by_week[this_week_start.isoformat()] == 2
    assert counts_by_week[last_week_start.isoformat()] == 1
