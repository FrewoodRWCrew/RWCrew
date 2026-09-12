# These tests check the KarStatussen tile on KarTracker's "Data Upload/
# Download" screen: the XLSX template download, the bulk kar-status import
# (same "kartracker.dataupload" screen key the Karren tile uses), and the
# kar-statuses-only export. A name that already exists is rejected as an
# error, never upserted — see kar_status_import.py's own module docstring.

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _build_xlsx(header: list[str], rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _create_kar_status(db_session: Session, *, name: str = "Actief") -> KarTrackerKarStatus:
    kar_status = KarTrackerKarStatus(name=name)
    db_session.add(kar_status)
    db_session.commit()
    db_session.refresh(kar_status)
    return kar_status


def _login_as_admin(client: TestClient, db_session: Session):
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")
    return module


# --- template + export -------------------------------------------------------


def test_downloading_the_template_requires_dataupload_permission(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Kar Manager", screen_key="kartracker.karmanagement", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    response = client.get("/api/modules/module-2/kar-status-import/template")

    assert response.status_code == 403


def test_super_admin_can_download_the_template(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)

    response = client.get("/api/modules/module-2/kar-status-import/template")

    assert response.status_code == 200
    assert response.headers["content-type"] == XLSX_CONTENT_TYPE
    assert "attachment" in response.headers["content-disposition"]

    workbook = load_workbook(io.BytesIO(response.content))
    header_row = [cell.value for cell in workbook.active[1]]
    assert header_row == ["name"]


def test_export_contains_kar_statuses_sheet(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)

    response = client.get("/api/modules/module-2/kar-statuses/export")

    assert response.status_code == 200
    workbook = load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["KarStatussen"]

    rows = list(workbook["KarStatussen"].iter_rows(values_only=True))
    assert rows[0] == ("id", "name")
    assert rows[1] == (kar_status.id, kar_status.name)


# --- bulk import ---------------------------------------------------------------


def test_view_only_dataupload_permission_cannot_import_kar_statuses(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="viewer@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Uploader", screen_key="kartracker.dataupload", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "viewer@example.com")

    xlsx_bytes = _build_xlsx(["name"], [["Actief"]])
    response = client.post(
        "/api/modules/module-2/kar-status-import",
        files={"file": ("statuses.xlsx", xlsx_bytes, XLSX_CONTENT_TYPE)},
    )

    assert response.status_code == 403


def test_import_creates_new_statuses_and_rejects_duplicates(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    existing = _create_kar_status(db_session, name="Terug in Magazijn")

    # A single-column template means a row with a blank name is
    # indistinguishable from a genuinely blank trailing row, so (like
    # kar_import.py's own blank-row handling) it's silently skipped rather
    # than reported — nothing to assert for that case here.
    xlsx_bytes = _build_xlsx(
        ["name"],
        [
            ["In gebruik"],
            ["Terug in Magazijn"],
        ],
    )

    response = client.post(
        "/api/modules/module-2/kar-status-import",
        files={"file": ("statuses.xlsx", xlsx_bytes, XLSX_CONTENT_TYPE)},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    outcomes = {row["name"]: row["outcome"] for row in results}
    assert outcomes["In gebruik"] == "created"
    assert outcomes["Terug in Magazijn"] == "error"

    new_status = db_session.scalar(select(KarTrackerKarStatus).where(KarTrackerKarStatus.name == "In gebruik"))
    assert new_status is not None

    # The duplicate row didn't create a second "Terug in Magazijn" row.
    assert (
        db_session.scalar(
            select(KarTrackerKarStatus).where(KarTrackerKarStatus.name == existing.name)
        ).id
        == existing.id
    )
