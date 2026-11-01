# Team aliases: set on the team endpoints and the Teams XLSX, refused when they
# clash with another team, and used to match a wristband scan's team name.

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.wristband.scan_service import match_team

BASE = "/api/modules/module-9"


@pytest.fixture()
def admin(client: TestClient, db_session: Session) -> TestClient:
    """Logged in as super admin with MasterData access (no role needed)."""
    from app.db.models.module import Module
    from app.db.models.user_module_access import UserModuleAccess
    from app.modules.module_9.screens import sync_screens

    sync_screens(db_session)
    module = Module(key="module-9", name="MasterData", sort_order=9)
    user = User(email="admin@example.com", hashed_password=hash_password("password123"), display_name="Admin", is_super_admin=True)
    db_session.add_all([module, user])
    db_session.flush()
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"}).status_code == 200
    return client


def _team(name: str, **fields) -> dict:
    return {"name": name, "task_ids": [], "kernlid_ids": [], "active": True, **fields}


def _upload(client: TestClient, rows: list[list]) -> list[dict]:
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    response = client.post(
        f"{BASE}/team-import",
        files={"file": ("teams.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200, response.text
    return response.json()["results"]


def test_aliases_are_stored_cleaned_and_kept_when_left_out(admin: TestClient) -> None:
    created = admin.post(
        f"{BASE}/teams", json=_team("YFU Vlaanderen", aliases=["  YFU   VL ", "yfu vl", "", "yfu vlaanderen", "Y.F.U."])
    ).json()
    # Trimmed, one per spelling, without blanks or the team's own name.
    assert created["aliases"] == ["Y.F.U.", "YFU VL"]

    # An update without the field (an older client) keeps them; an empty list clears them.
    assert admin.put(f"{BASE}/teams/{created['id']}", json=_team("YFU Vlaanderen")).json()["aliases"] == ["Y.F.U.", "YFU VL"]
    assert admin.put(f"{BASE}/teams/{created['id']}", json=_team("YFU Vlaanderen", aliases=[])).json()["aliases"] == []


def test_alias_clash_with_another_team_is_refused(admin: TestClient) -> None:
    first = admin.post(f"{BASE}/teams", json=_team("Terras", aliases=["RW Terras"])).json()
    second = admin.post(f"{BASE}/teams", json=_team("VIP")).json()

    # Another team's alias, or its name: refused, ignoring case.
    taken = admin.put(f"{BASE}/teams/{second['id']}", json=_team("VIP", aliases=["rw terras"]))
    assert taken.status_code == 400 and "already used" in taken.json()["detail"]
    named = admin.post(f"{BASE}/teams", json=_team("Nieuw", aliases=["TERRAS"]))
    assert named.status_code == 400 and "is the name of team" in named.json()["detail"]
    # Refused means nothing was created or changed.
    assert [team["name"] for team in admin.get(f"{BASE}/teams").json()] == ["Terras", "VIP"]

    # A team keeps its own alias on an update.
    assert admin.put(f"{BASE}/teams/{first['id']}", json=_team("Terras", aliases=["RW Terras"])).status_code == 200


def test_match_team_uses_name_then_alias(admin: TestClient, db_session: Session) -> None:
    created = admin.post(f"{BASE}/teams", json=_team("YFU Vlaanderen", aliases=["YFU-VL"])).json()
    assert match_team(db_session, "  yfu   vlaanderen ").id == created["id"]
    assert match_team(db_session, "yfu-vl").id == created["id"]
    assert match_team(db_session, "Iets anders") is None


def test_deleting_a_team_frees_its_aliases(admin: TestClient, db_session: Session) -> None:
    created = admin.post(f"{BASE}/teams", json=_team("Oud", aliases=["Vrij"])).json()
    assert admin.delete(f"{BASE}/teams/{created['id']}").status_code == 204
    assert admin.post(f"{BASE}/teams", json=_team("Nieuw", aliases=["Vrij"])).status_code == 201


def test_xlsx_import_and_export(admin: TestClient, db_session: Session) -> None:
    results = _upload(admin, [["id", "name", "aliases"], [None, "Terras", "RW Terras; Terras RW"], [None, "VIP", "rw terras"]])
    assert results[0]["outcome"] == "created"
    # The clash is a row error and leaves no half-made team behind.
    assert results[1]["outcome"] == "error" and "already used" in results[1]["detail"]
    teams = admin.get(f"{BASE}/teams").json()
    assert [(team["name"], team["aliases"]) for team in teams] == [("Terras", ["RW Terras", "Terras RW"])]

    # A sheet without the column leaves them unchanged.
    team_id = teams[0]["id"]
    assert _upload(admin, [["id", "description"], [team_id, "x"]])[0]["outcome"] == "updated"
    assert admin.get(f"{BASE}/teams").json()[0]["aliases"] == ["RW Terras", "Terras RW"]

    sheet = load_workbook(BytesIO(admin.get(f"{BASE}/teams/export").content)).active
    header = [cell.value for cell in sheet[1]]
    assert sheet.cell(row=2, column=header.index("aliases") + 1).value == "RW Terras; Terras RW"
    assert db_session.query(Team).count() == 1
