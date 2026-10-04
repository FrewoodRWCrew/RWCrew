# Tests for carrying out a scanned line's action (line_processing.py):
# every freshly scanned line and file starts "new"; the pending count/list
# only offer actions with a handler ("Assignment"); processing needs a
# product per file, creates the missing tags with it (or fills it in on a
# registered tag without one) and marks lines "loaded" with a comment;
# cancelling needs a comment; and a file's own status follows its lines.

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.rfid_tag import RfidTag
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.modules.module_1.screens import sync_screens
from tests.modules.module_1.test_line_data import (
    REAL_HEADER,
    _admin_client,
    _create_product,
    _create_tag,
    _create_tagscan_module,
    _create_user,
    _grant_module_access,
    _grant_permission,
    _login,
    scan_dirs,  # noqa: F401 — pytest fixture, used by name below
)

BASE = "/api/modules/module-1"


def _write_csv(scan_dirs: Path, name: str, rows: list[tuple[str, str]]) -> None:
    """One CSV with an Action column: rows are (epc, action)."""
    body = "".join(f"Scan_01,{epc},78,1,92,10:36:07,PROD,{action}\n" for epc, action in rows)
    (scan_dirs / "Unreaded Tags" / name).write_bytes((REAL_HEADER.strip() + ",Mode,Action\n" + body).encode())


def _header_id(db_session: Session, filename: str) -> int:
    return db_session.scalar(select(TagHeaderData.id).where(TagHeaderData.filename == filename))


def _lines_by_epc(db_session: Session) -> dict[str, TagLineData]:
    db_session.expire_all()
    return {line.epc: line for line in db_session.scalars(select(TagLineData)).all()}


def test_scan_starts_header_and_lines_as_new(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    _write_csv(scan_dirs, "scan.csv", [("E2AAA", "Assignment")])
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post(f"{BASE}/header-data/scan")

    header_json = client.get(f"{BASE}/header-data").json()[0]
    line_json = client.get(f"{BASE}/line-data").json()[0]
    assert header_json["process_status"] == "new"
    assert line_json["process_status"] == "new"
    assert line_json["process_comment"] is None


def test_pending_only_counts_new_assignment_lines(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    # Case and surrounding spaces don't matter; other actions have no
    # handler yet, so they're not offered.
    _write_csv(scan_dirs, "scan.csv", [("E2AAA", "Assignment"), ("E2BBB", " assignment "), ("E2CCC", "Inventory")])
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post(f"{BASE}/header-data/scan")

    assert client.get(f"{BASE}/line-data/pending/count").json() == {"count": 2}
    pending = client.get(f"{BASE}/line-data/pending").json()
    assert sorted(row["epc"] for row in pending) == ["E2AAA", "E2BBB"]


def test_process_creates_missing_tags_with_the_files_product(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    product = _create_product(db_session, name="KBC Lint")
    other = _create_product(db_session, name="Kar")
    _create_tag(db_session, epc_uid="E2EMPTY", status="active")
    _create_tag(db_session, epc_uid="E2OTHER", status="active", assigned_product_id=other.id)
    _write_csv(
        scan_dirs,
        "scan.csv",
        [("E2NEW", "Assignment"), ("E2EMPTY", "Assignment"), ("E2OTHER", "Assignment"), ("E2NEW", "Assignment")],
    )
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post(f"{BASE}/header-data/scan")

    response = client.post(
        f"{BASE}/line-data/pending/process",
        json={"files": [{"header_data_id": _header_id(db_session, "scan.csv"), "product_id": product.id}]},
    )

    assert response.status_code == 200
    body = response.json()
    # The same EPC twice in one batch: the second one finds the tag the
    # first one just created.
    assert [row["outcome"] for row in body["results"]] == ["created", "assigned", "exists", "exists"]
    assert body["remaining_count"] == 0

    db_session.expire_all()
    tags = {tag.epc_uid: tag for tag in db_session.scalars(select(RfidTag)).all()}
    assert tags["E2NEW"].assigned_product_id == product.id
    assert tags["E2NEW"].date_assigned is not None
    assert tags["E2EMPTY"].assigned_product_id == product.id
    # A tag that already had another product is never changed.
    assert tags["E2OTHER"].assigned_product_id == other.id

    lines = db_session.scalars(select(TagLineData).order_by(TagLineData.line_number)).all()
    assert [line.process_status for line in lines] == ["loaded"] * 4
    assert lines[0].process_comment == "Tag created for KBC Lint"
    assert lines[1].process_comment == "Product KBC Lint assigned to existing tag"
    assert lines[2].process_comment == "Tag already assigned to Kar — not changed"
    assert lines[3].process_comment == "Tag already assigned to KBC Lint"
    # Matched right away (no Synchro needed), with the product snapshot.
    assert all(line.status == "converted" for line in lines)
    assert lines[0].assigned_product_name == "KBC Lint"

    header = db_session.scalar(select(TagHeaderData))
    assert header.process_status == "loaded"
    assert header.process_comment == "4 loaded"


def test_process_requires_a_product(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    _write_csv(scan_dirs, "scan.csv", [("E2AAA", "Assignment")])
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post(f"{BASE}/header-data/scan")
    header_id = _header_id(db_session, "scan.csv")

    assert client.post(f"{BASE}/line-data/pending/process", json={"files": []}).status_code == 422
    assert (
        client.post(f"{BASE}/line-data/pending/process", json={"files": [{"header_data_id": header_id}]}).status_code
        == 422
    )
    unknown = client.post(
        f"{BASE}/line-data/pending/process", json={"files": [{"header_data_id": header_id, "product_id": 999}]}
    )
    assert unknown.status_code == 404
    # Nothing was created or changed.
    assert db_session.scalar(select(RfidTag)) is None
    assert _lines_by_epc(db_session)["E2AAA"].process_status == "new"


def test_process_only_the_given_files(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    product = _create_product(db_session)
    _write_csv(scan_dirs, "a.csv", [("E2AAA", "Assignment")])
    _write_csv(scan_dirs, "b.csv", [("E2BBB", "Assignment")])
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post(f"{BASE}/header-data/scan")

    body = client.post(
        f"{BASE}/line-data/pending/process",
        json={"files": [{"header_data_id": _header_id(db_session, "a.csv"), "product_id": product.id}]},
    ).json()

    assert [row["epc"] for row in body["results"]] == ["E2AAA"]
    assert body["remaining_count"] == 1
    lines = _lines_by_epc(db_session)
    assert lines["E2BBB"].process_status == "new"
    headers = {header.filename: header for header in db_session.scalars(select(TagHeaderData)).all()}
    assert headers["a.csv"].process_status == "loaded"
    assert headers["b.csv"].process_status == "new"


def test_products_list_for_the_dialog(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    _create_product(db_session, name="Zeil")
    _create_product(db_session, name="Kar")
    sync_screens(db_session)
    _admin_client(client, db_session)

    response = client.get(f"{BASE}/products")

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Kar", "Zeil"]


def test_cancel_requires_a_comment_and_updates_line_and_header(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    _write_csv(scan_dirs, "scan.csv", [("E2AAA", "Assignment")])
    sync_screens(db_session)
    _admin_client(client, db_session)
    client.post(f"{BASE}/header-data/scan")
    line_id = _lines_by_epc(db_session)["E2AAA"].id

    assert client.post(f"{BASE}/line-data/{line_id}/process-cancel", json={"comment": "   "}).status_code == 422

    response = client.post(f"{BASE}/line-data/{line_id}/process-cancel", json={"comment": "Wrong scanner"})

    assert response.status_code == 200
    assert response.json()["process_status"] == "cancelled"
    assert response.json()["process_comment"] == "Wrong scanner"
    assert client.get(f"{BASE}/line-data/pending/count").json() == {"count": 0}
    header = db_session.scalar(select(TagHeaderData))
    db_session.refresh(header)
    assert header.process_status == "cancelled"
    assert header.process_comment == "1 cancelled"
    # Cancelling never creates a tag.
    assert db_session.scalar(select(RfidTag)) is None


def test_cancel_unknown_line_returns_404(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    _admin_client(client, db_session)

    response = client.post(f"{BASE}/line-data/999/process-cancel", json={"comment": "x"})

    assert response.status_code == 404


def test_file_without_lines_is_loaded_at_scan_time(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    (scan_dirs / "Unreaded Tags" / "empty.csv").write_bytes(REAL_HEADER.encode())
    sync_screens(db_session)
    _admin_client(client, db_session)

    client.post(f"{BASE}/header-data/scan")

    header = db_session.scalar(select(TagHeaderData))
    assert (header.process_status, header.process_comment) == ("loaded", "No lines")


def test_count_needs_only_module_access_but_list_needs_view(
    client: TestClient, db_session: Session, scan_dirs: Path
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    assert client.get(f"{BASE}/line-data/pending/count").status_code == 200
    assert client.get(f"{BASE}/line-data/pending").status_code == 403
    assert client.get(f"{BASE}/products").status_code == 403
    assert (
        client.post(
            f"{BASE}/line-data/pending/process", json={"files": [{"header_data_id": 1, "product_id": 1}]}
        ).status_code
        == 403
    )
    assert client.post(f"{BASE}/line-data/1/process-cancel", json={"comment": "x"}).status_code == 403


def test_process_needs_tag_create_permission_too(client: TestClient, db_session: Session, scan_dirs: Path) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="editor@example.com")
    _grant_module_access(db_session, user, module)
    _grant_permission(db_session, user, "tagscan.tag-linedata", can_view=True, can_edit=True)
    _login(client, "editor@example.com")

    response = client.post(
        f"{BASE}/line-data/pending/process", json={"files": [{"header_data_id": 1, "product_id": 1}]}
    )

    assert response.status_code == 403
