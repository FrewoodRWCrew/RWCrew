# Tests for the "Tag Linedata" screen: every CSV data line produced by a
# Tag Headerdata scan becomes its own row, linked to the header row it
# came from and enriched with a snapshot of its matching TagManagement
# tag (if any) — gated by "tagscan.tag-linedata", independently of every
# other module_1 screen. Also covers the manual "cancel" action, the
# only way a line's status ever becomes "cancelled".

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_type import ProductType
from app.db.models.rfid_tag import RfidTag
from app.db.models.scanner import Scanner
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.db.models.tagscan_role import TagscanRole
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_1.screens import sync_screens

REAL_HEADER = "Scanner,EPC,RSSI (raw),Antenna,Count,Last Seen\n"


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


def _grant_permission(
    db_session: Session,
    user: User,
    screen_key: str,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
) -> None:
    role = TagscanRole(name=f"Role {screen_key} {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == screen_key))
    db_session.add(
        TagscanRolePermission(
            role_id=role.id, screen_id=screen.id, can_view=can_view, can_create=can_create, can_edit=can_edit
        )
    )
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def _admin_client(client: TestClient, db_session: Session) -> User:
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")
    return admin


@pytest.fixture()
def scan_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "Unreaded Tags").mkdir()
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    return tmp_path


def _create_product(db_session: Session, *, name: str = "KBC Lint") -> Product:
    product = Product(name=name)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _create_tag(db_session: Session, **kwargs) -> RfidTag:
    tag = RfidTag(**kwargs)
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


def _create_scanner_device(db_session: Session, **kwargs) -> Scanner:
    if "type_id" not in kwargs:
        product_type = ProductType(name=f"Type for {kwargs.get('scanner', 'scanner')}")
        db_session.add(product_type)
        db_session.commit()
        db_session.refresh(product_type)
        kwargs["type_id"] = product_type.id
    kwargs.setdefault("technology", "Raspberry Pi 4")
    scanner = Scanner(**kwargs)
    db_session.add(scanner)
    db_session.commit()
    db_session.refresh(scanner)
    return scanner


def test_scan_handles_a_leading_utf8_bom_without_breaking_column_matching(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    # Excel/scanner software commonly writes a UTF-8 BOM at the start of
    # a CSV. Decoded as plain utf-8, that BOM glues onto the first header
    # name ("﻿Scanner"), which would then never match COLUMN_SCANNER
    # and silently leave every row's "scanner" field None.
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        ("﻿" + REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode("utf-8")
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    line = db_session.scalar(select(TagLineData))
    assert line.scanner == "Scan_01"
    assert line.epc == "E2AAA"


def test_scan_creates_one_line_row_per_data_row_with_raw_fields(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E28011704000021CDFDB54EE,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    scan_response = client.post("/api/modules/module-1/header-data/scan")
    assert scan_response.status_code == 200
    assert scan_response.json()["results"][0]["outcome"] == "logged"

    lines = db_session.scalars(select(TagLineData)).all()
    assert len(lines) == 1
    line = lines[0]
    assert line.line_number == 2
    assert line.scanner == "Scan_01"
    assert line.epc == "E28011704000021CDFDB54EE"
    assert line.rssi == 78
    assert line.antenna == 1
    assert line.count == 92
    assert line.last_seen == "10:36:07"
    assert line.status == "no_match"
    assert line.rfid_tag_id is None

    header = db_session.scalar(select(TagHeaderData))
    assert line.header_data_id == header.id


def test_scan_stores_mode_and_action_on_header_and_lines(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    # The first row has empty Mode/Action cells: the header takes the first
    # non-empty value in the file, and that row falls back to it.
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (
            REAL_HEADER.strip()
            + ",Mode,Action\n"
            + "Scan_01,E2AAA,78,1,92,10:36:07,,\n"
            + "Scan_01,E2BBB,70,1,10,10:36:08,Inbound,Register\n"
            + "Scan_01,E2CCC,71,1,11,10:36:09,Outbound,Remove\n"
        ).encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    header = db_session.scalar(select(TagHeaderData))
    assert header.mode == "Inbound"
    assert header.action == "Register"

    lines = {line.epc: line for line in db_session.scalars(select(TagLineData)).all()}
    assert (lines["E2AAA"].mode, lines["E2AAA"].action) == ("Inbound", "Register")
    assert (lines["E2BBB"].mode, lines["E2BBB"].action) == ("Inbound", "Register")
    assert (lines["E2CCC"].mode, lines["E2CCC"].action) == ("Outbound", "Remove")

    # Both the header list and the line list expose the new fields.
    header_json = client.get("/api/modules/module-1/header-data").json()[0]
    assert (header_json["mode"], header_json["action"]) == ("Inbound", "Register")
    line_json = {row["epc"]: row for row in client.get("/api/modules/module-1/line-data").json()}
    assert (line_json["E2CCC"]["mode"], line_json["E2CCC"]["action"]) == ("Outbound", "Remove")


def test_scan_without_mode_and_action_columns_leaves_them_null(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    header = db_session.scalar(select(TagHeaderData))
    line = db_session.scalar(select(TagLineData))
    assert header.mode is None and header.action is None
    assert line.mode is None and line.action is None


def test_matched_epc_is_converted_and_enriched_from_tag_management(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    product = _create_product(db_session, name="KBC Lint")
    tag = _create_tag(
        db_session,
        epc_uid="E28011704000021CDFDB54EE",
        assigned_product_id=product.id,
        assigned_serial_number="SN-001",
        manufacturer="Impinj",
        batch_number="B-42",
    )
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E28011704000021CDFDB54EE,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    line = db_session.scalar(select(TagLineData))
    assert line.status == "converted"
    assert line.rfid_tag_id == tag.id
    assert line.assigned_product_name == "KBC Lint"
    assert line.assigned_serial_number == "SN-001"
    assert line.manufacturer == "Impinj"
    assert line.batch_number == "B-42"


def test_unmatched_epc_is_no_match_with_null_snapshot_fields(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,DOES-NOT-EXIST,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    line = db_session.scalar(select(TagLineData))
    assert line.status == "no_match"
    assert line.rfid_tag_id is None
    assert line.assigned_product_name is None
    assert line.assigned_serial_number is None
    assert line.manufacturer is None
    assert line.batch_number is None


def test_matched_scanner_is_enriched_from_scanners_registry(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    scanner = _create_scanner_device(
        db_session, scanner="Scan_01", technology="Raspberry Pi 5", location="Warehouse A"
    )
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    line = db_session.scalar(select(TagLineData))
    assert line.scanner_id == scanner.id
    assert line.scanner_name == "Scan_01"
    assert line.scanner_location == "Warehouse A"
    assert line.scanner_technology == "Raspberry Pi 5"

    header = db_session.scalar(select(TagHeaderData))
    assert header.scanner == "Scan_01"
    assert header.scanner_id == scanner.id
    assert header.scanner_name == "Scan_01"
    assert header.scanner_location == "Warehouse A"
    assert header.scanner_technology == "Raspberry Pi 5"


def test_unmatched_scanner_leaves_snapshot_fields_null_but_keeps_raw_text(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Unknown_Scanner,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    line = db_session.scalar(select(TagLineData))
    assert line.scanner == "Unknown_Scanner"
    assert line.scanner_id is None
    assert line.scanner_name is None
    assert line.scanner_location is None
    assert line.scanner_technology is None

    header = db_session.scalar(select(TagHeaderData))
    assert header.scanner == "Unknown_Scanner"
    assert header.scanner_id is None


def test_scanner_matching_is_case_insensitive(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    scanner = _create_scanner_device(db_session, scanner="Scan_01")
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    line = db_session.scalar(select(TagLineData))
    assert line.scanner_id == scanner.id


def test_trailing_blank_line_produces_no_extra_row(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post("/api/modules/module-1/header-data/scan")

    lines = db_session.scalars(select(TagLineData)).all()
    assert len(lines) == 1


def test_user_without_permission_gets_403_on_list_and_cancel(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    assert client.get("/api/modules/module-1/line-data").status_code == 403
    assert client.post("/api/modules/module-1/line-data/1/cancel").status_code == 403


def test_view_only_permission_cannot_cancel(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_permission(db_session, user, "tagscan.tag-linedata", can_view=True)
    _login(client, "viewer@example.com")

    response = client.post("/api/modules/module-1/line-data/1/cancel")

    assert response.status_code == 403


def test_cancelling_an_unknown_line_returns_404(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    _admin_client(client, db_session)

    response = client.post("/api/modules/module-1/line-data/999/cancel")

    assert response.status_code == 404


def test_cancel_sets_status_and_is_reflected_in_the_list(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")
    line = db_session.scalar(select(TagLineData))

    cancel_response = client.post(f"/api/modules/module-1/line-data/{line.id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    list_response = client.get("/api/modules/module-1/line-data")
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "cancelled"


def test_list_line_data_includes_header_filename(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    (scan_dirs / "Unreaded Tags" / "my_scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")

    response = client.get("/api/modules/module-1/line-data")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["header_filename"] == "my_scan.csv"


def test_lines_from_one_file_are_listed_in_the_same_order_as_the_csv(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    # A single scan commits every line from a file in one transaction, so
    # they can all end up with the exact same created_at timestamp —
    # ordering must rely on line_number, not created_at, to reproduce the
    # CSV's own row order every time.
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (
            REAL_HEADER
            + "Scan_01,E2AAA,78,1,92,10:36:01\n"
            + "Scan_01,E2BBB,79,1,93,10:36:02\n"
            + "Scan_01,E2CCC,80,1,94,10:36:03\n"
            + "Scan_01,E2DDD,81,1,95,10:36:04\n"
        ).encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")

    response = client.get("/api/modules/module-1/line-data")

    assert response.status_code == 200
    body = response.json()
    assert [entry["epc"] for entry in body] == ["E2AAA", "E2BBB", "E2CCC", "E2DDD"]
    assert [entry["line_number"] for entry in body] == [2, 3, 4, 5]


def test_newest_scanned_file_is_listed_first(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    (scan_dirs / "Unreaded Tags" / "a_scan.csv").write_bytes((REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode())
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")

    (scan_dirs / "Unreaded Tags" / "b_scan.csv").write_bytes((REAL_HEADER + "Scan_01,E2BBB,78,1,92,10:36:07\n").encode())
    client.post("/api/modules/module-1/header-data/scan")

    response = client.get("/api/modules/module-1/line-data")

    assert response.status_code == 200
    assert [entry["header_filename"] for entry in response.json()] == ["b_scan.csv", "a_scan.csv"]


# --- Synchro (re-check every line's match against TagManagement) -----------


def test_sync_converts_a_line_once_its_tag_is_registered_afterwards(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")
    line = db_session.scalar(select(TagLineData))
    assert line.status == "no_match"

    # The tag only gets registered in TagManagement after the scan ran.
    product = _create_product(db_session, name="KBC Lint")
    tag = _create_tag(
        db_session,
        epc_uid="E2AAA",
        assigned_product_id=product.id,
        assigned_serial_number="SN-001",
        manufacturer="Impinj",
        batch_number="B-42",
    )

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 1
    entry = body["entries"][0]
    assert entry["status"] == "converted"
    assert entry["rfid_tag_id"] == tag.id
    assert entry["assigned_product_name"] == "KBC Lint"
    assert entry["assigned_serial_number"] == "SN-001"
    assert entry["manufacturer"] == "Impinj"
    assert entry["batch_number"] == "B-42"


def test_sync_reflects_a_product_rename_on_an_already_converted_line(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    product = _create_product(db_session, name="Old Name")
    _create_tag(db_session, epc_uid="E2AAA", assigned_product_id=product.id)
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")
    line = db_session.scalar(select(TagLineData))
    assert line.assigned_product_name == "Old Name"

    product.name = "New Name"
    db_session.commit()

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 1
    assert body["entries"][0]["assigned_product_name"] == "New Name"


def test_sync_leaves_cancelled_lines_untouched(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    product = _create_product(db_session, name="KBC Lint")
    _create_tag(db_session, epc_uid="E2AAA", assigned_product_id=product.id)
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")
    line = db_session.scalar(select(TagLineData))
    client.post(f"/api/modules/module-1/line-data/{line.id}/cancel")

    # If sync didn't skip cancelled lines, this rename would flip it back
    # to converted with the new product name.
    product.name = "New Name"
    db_session.commit()

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 0
    entry = body["entries"][0]
    assert entry["status"] == "cancelled"
    assert entry["assigned_product_name"] == "KBC Lint"


def test_sync_reflects_a_scanner_rename_on_an_already_matched_line(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    scanner = _create_scanner_device(db_session, scanner="Old Scanner Name", location="Old Location")
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Old Scanner Name,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")
    line = db_session.scalar(select(TagLineData))
    assert line.scanner_name == "Old Scanner Name"

    scanner.scanner = "New Scanner Name"
    scanner.location = "New Location"
    db_session.commit()

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["updated_count"] == 1
    entry = body["entries"][0]
    assert entry["scanner_name"] == "New Scanner Name"
    assert entry["scanner_location"] == "New Location"

    header = db_session.scalar(select(TagHeaderData))
    assert header.scanner_name == "New Scanner Name"
    assert header.scanner_location == "New Location"


def test_sync_leaves_cancelled_lines_scanner_snapshot_untouched(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    scanner = _create_scanner_device(db_session, scanner="Old Scanner Name")
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Old Scanner Name,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")
    line = db_session.scalar(select(TagLineData))
    client.post(f"/api/modules/module-1/line-data/{line.id}/cancel")

    scanner.scanner = "New Scanner Name"
    db_session.commit()

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 200
    entry = response.json()["entries"][0]
    assert entry["status"] == "cancelled"
    assert entry["scanner_name"] == "Old Scanner Name"


def test_sync_reports_zero_updates_when_nothing_changed(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 200
    assert response.json()["updated_count"] == 0


def test_view_only_permission_cannot_sync(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_permission(db_session, user, "tagscan.tag-linedata", can_view=True)
    _login(client, "viewer@example.com")

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 403


def test_sync_matches_a_tag_whose_epc_uid_has_stray_whitespace(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    # Simulates a row that predates the epc_uid-trimming validator (or
    # was inserted outside the API) — a trailing tab, invisible in most
    # UIs, that would otherwise make an identical EPC silently never match.
    product = _create_product(db_session, name="KBC Lint")
    tag = _create_tag(db_session, epc_uid="E2AAA\t", assigned_product_id=product.id)
    (scan_dirs / "Unreaded Tags" / "scan.csv").write_bytes(
        (REAL_HEADER + "Scan_01,E2AAA,78,1,92,10:36:07\n").encode()
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post("/api/modules/module-1/header-data/scan")

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 200
    entry = response.json()["entries"][0]
    assert entry["status"] == "converted"
    assert entry["rfid_tag_id"] == tag.id
    assert entry["assigned_product_name"] == "KBC Lint"


def test_user_without_permission_cannot_sync(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.post("/api/modules/module-1/line-data/sync")

    assert response.status_code == 403
