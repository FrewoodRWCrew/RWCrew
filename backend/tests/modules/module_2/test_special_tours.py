# Tests for KarTracker's "Speciale levertoeren" masterdata screen
# (/special-tours): CRUD, unique names, no delete while a team is linked,
# the linked teams' names and the screen rights.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_speciale_levertoer import KarTrackerSpecialeLevertoer
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.team import Team
from app.db.models.team_speciale_levertoer import TeamSpecialeLevertoer
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)
from tests.modules.module_2.test_initial_delivery import _add, _login_admin

URL = "/api/modules/module-2/special-tours"


def test_create_list_update_and_delete_a_tour(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)

    created = client.post(URL, json={"name": "Kleine wastoer", "description": "Elke ochtend"})
    assert created.status_code == 201
    tour = created.json()
    assert tour | {"id": 0} == {
        "id": 0, "name": "Kleine wastoer", "description": "Elke ochtend", "active": True, "team_names": []
    }
    client.post(URL, json={"name": "Ijsblokken"})

    # Listed by name.
    assert [row["name"] for row in client.get(URL).json()] == ["Ijsblokken", "Kleine wastoer"]

    updated = client.put(f"{URL}/{tour['id']}", json={"name": "Grote wastoer", "description": None, "active": False})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Grote wastoer"
    assert updated.json()["active"] is False

    assert client.delete(f"{URL}/{tour['id']}").status_code == 204
    assert [row["name"] for row in client.get(URL).json()] == ["Ijsblokken"]


def test_names_are_unique(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    client.post(URL, json={"name": "Ijsblokken"})
    other = client.post(URL, json={"name": "Wastoer"}).json()

    assert client.post(URL, json={"name": "Ijsblokken"}).status_code == 409
    assert client.put(f"{URL}/{other['id']}", json={"name": "Ijsblokken"}).status_code == 409


def test_linked_teams_are_listed_and_block_the_delete(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    tour = KarTrackerSpecialeLevertoer(name="Ijsblokken")
    scouts, chiro = Team(name="Scouts"), Team(name="Chiro")
    _add(db_session, tour, scouts, chiro)
    _add(
        db_session,
        TeamSpecialeLevertoer(team_id=scouts.id, levertoer_id=tour.id),
        TeamSpecialeLevertoer(team_id=chiro.id, levertoer_id=tour.id),
    )

    assert client.get(URL).json()[0]["team_names"] == ["Chiro", "Scouts"]
    response = client.delete(f"{URL}/{tour.id}")
    assert response.status_code == 400
    assert client.put(f"{URL}/9999", json={"name": "X"}).status_code == 404
    assert client.delete(f"{URL}/9999").status_code == 404


def test_needs_the_screen_rights(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="user@example.com")
    grant_module_access(db_session, user, module)
    # View only: listing works, creating doesn't.
    role = create_role_with_permissions(
        db_session, name="Kijker", screen_key="kartracker.specialelevertoeren", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "user@example.com")

    assert client.get(URL).status_code == 200
    assert client.post(URL, json={"name": "Ijsblokken"}).status_code == 403
