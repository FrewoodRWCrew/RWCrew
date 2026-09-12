# These tests check KarTracker's "Data Upload/Download" screen: the XLSX
# template download, the bulk kar import (own screen key
# "kartracker.dataupload", separate from "kartracker.karmanagement"), and
# the full-database export. Unlike TagScan's tag import, a kar_nummer that
# already exists is rejected as an error, never upserted — see
# kar_import.py's own module docstring for why.

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.product import Product
from app.db.models.team import Team
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


def _create_product(db_session: Session, *, name: str = "KBC Lint") -> Product:
    product = Product(name=name)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _create_team(db_session: Session, *, name: str = "Scouts Wezemaal") -> Team:
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


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

    response = client.get("/api/modules/module-2/kar-import/template")

    assert response.status_code == 403


def test_super_admin_can_download_the_template(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)

    response = client.get("/api/modules/module-2/kar-import/template")

    assert response.status_code == 200
    assert response.headers["content-type"] == XLSX_CONTENT_TYPE
    assert "attachment" in response.headers["content-disposition"]

    workbook = load_workbook(io.BytesIO(response.content))
    header_row = [cell.value for cell in workbook.active[1]]
    assert "kar_nummer" in header_row
    assert "status_name" in header_row
    assert "transport_type_name" in header_row


def test_export_contains_karren_and_kar_statuses_sheets(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    db_session.add(KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, transport_type_id=product.id))
    db_session.commit()

    response = client.get("/api/modules/module-2/karren/export")

    assert response.status_code == 200
    workbook = load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Karren", "KarStatussen"]

    karren_rows = list(workbook["Karren"].iter_rows(values_only=True))
    assert karren_rows[0][0] == "kar_nummer"
    assert karren_rows[1][0] == "B001"
    assert karren_rows[1][1] == kar_status.name

    status_rows = list(workbook["KarStatussen"].iter_rows(values_only=True))
    assert status_rows[1] == (kar_status.id, kar_status.name)


# --- bulk import ---------------------------------------------------------------


def test_view_only_dataupload_permission_cannot_import_karren(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="viewer@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Uploader", screen_key="kartracker.dataupload", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "viewer@example.com")

    xlsx_bytes = _build_xlsx(["kar_nummer"], [["B001"]])
    response = client.post(
        "/api/modules/module-2/kar-import",
        files={"file": ("karren.xlsx", xlsx_bytes, XLSX_CONTENT_TYPE)},
    )

    assert response.status_code == 403


def test_import_creates_new_karren_and_rejects_duplicates_and_bad_lookups(
    client: TestClient, db_session: Session
) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    team = _create_team(db_session)
    db_session.add(KarTrackerKar(kar_nummer="B_EXISTING", status_id=kar_status.id, transport_type_id=product.id))
    db_session.commit()

    xlsx_bytes = _build_xlsx(
        ["kar_nummer", "status_name", "team_name", "transport_type_name"],
        [
            ["B_NEW", kar_status.name, team.name, product.name],
            ["B_EXISTING", kar_status.name, None, product.name],
            ["B_BADSTATUS", "Not A Status", None, product.name],
            ["B_BADPRODUCT", kar_status.name, None, "Not A Product"],
            [None, kar_status.name, None, product.name],
        ],
    )

    response = client.post(
        "/api/modules/module-2/kar-import",
        files={"file": ("karren.xlsx", xlsx_bytes, XLSX_CONTENT_TYPE)},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    outcomes = {row["kar_nummer"]: row["outcome"] for row in results}
    assert outcomes["B_NEW"] == "created"
    assert outcomes["B_EXISTING"] == "error"
    assert outcomes["B_BADSTATUS"] == "error"
    assert outcomes["B_BADPRODUCT"] == "error"
    missing_kar_nummer_row = next(row for row in results if row["row_number"] == 6)
    assert missing_kar_nummer_row["outcome"] == "error"

    new_kar = db_session.scalar(select(KarTrackerKar).where(KarTrackerKar.kar_nummer == "B_NEW"))
    assert new_kar is not None
    assert new_kar.team_id == team.id

    # Only one "B_EXISTING" row remains — the duplicate wasn't touched.
    assert db_session.scalar(select(KarTrackerKar).where(KarTrackerKar.kar_nummer == "B_BADSTATUS")) is None
    assert db_session.scalar(select(KarTrackerKar).where(KarTrackerKar.kar_nummer == "B_BADPRODUCT")) is None
