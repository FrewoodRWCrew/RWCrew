# Tests for the "Manuele kar beweging" screen (see module_2/router.py's
# /kar-actions endpoints): logging a kar movement into
# KarTracker_kar_actions, with the kar's team as snapshot, and updating the
# kar's own latest status/location at the same time.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_action import KarTrackerKarAction
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

BASE_URL = "/api/modules/module-2/kar-actions"


def _login_admin(client: TestClient, db_session: Session) -> None:
    """Set up the module and log in as a super admin with module access."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")


def _login_with_role(client: TestClient, db_session: Session, **permissions: bool) -> None:
    """Log in as a normal user whose role has the given permissions on the
    "kartracker.actions" screen.
    """
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(
        db_session, name="Leverancier", screen_key="kartracker.actions", **permissions
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")


def _create_status(db_session: Session, name: str) -> KarTrackerKarStatus:
    kar_status = KarTrackerKarStatus(name=name)
    db_session.add(kar_status)
    db_session.commit()
    db_session.refresh(kar_status)
    return kar_status


def _create_kar(db_session: Session, *, kar_nummer: str, status_id: int, team_id: int | None) -> KarTrackerKar:
    product = db_session.scalar(select(Product)) or Product(name="Box")
    db_session.add(product)
    db_session.commit()
    kar = KarTrackerKar(kar_nummer=kar_nummer, status_id=status_id, transport_type_id=product.id, team_id=team_id)
    db_session.add(kar)
    db_session.commit()
    db_session.refresh(kar)
    return kar


def _create_team(db_session: Session, name: str = "Scouts Wezemaal") -> Team:
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def test_logging_a_movement_stores_it_and_updates_the_kar(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    in_magazijn = _create_status(db_session, "Terug in Magazijn")
    geleverd = _create_status(db_session, "Geleverd")
    team = _create_team(db_session)
    kar = _create_kar(db_session, kar_nummer="B001", status_id=in_magazijn.id, team_id=team.id)

    response = client.post(
        BASE_URL, json={"kar_id": kar.id, "status_id": geleverd.id, "latitude": 50.97, "longitude": 4.68}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["kar_nummer"] == "B001"
    assert body["status_name"] == "Geleverd"
    assert body["team_id"] == team.id
    assert body["team_name"] == "Scouts Wezemaal"
    assert body["user_name"] == "admin@example.com"
    assert body["recorded_at"]

    # The kar's own latest state follows the logged movement.
    db_session.expire_all()
    updated_kar = db_session.get(KarTrackerKar, kar.id)
    assert updated_kar.status_id == geleverd.id
    assert updated_kar.last_latitude == 50.97
    assert updated_kar.last_longitude == 4.68
    assert updated_kar.last_recorded_at is not None


def test_team_is_a_snapshot_of_the_kars_team(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    kar_status = _create_status(db_session, "Geleverd")
    team = _create_team(db_session)
    kar_with_team = _create_kar(db_session, kar_nummer="B001", status_id=kar_status.id, team_id=team.id)
    kar_without_team = _create_kar(db_session, kar_nummer="B002", status_id=kar_status.id, team_id=None)

    client.post(BASE_URL, json={"kar_id": kar_with_team.id, "status_id": kar_status.id, "latitude": 1, "longitude": 2})
    client.post(
        BASE_URL, json={"kar_id": kar_without_team.id, "status_id": kar_status.id, "latitude": 1, "longitude": 2}
    )

    # Moving the kar to another team later doesn't rewrite its history.
    other_team = _create_team(db_session, "Chiro Haacht")
    kar_with_team.team_id = other_team.id
    db_session.commit()

    actions = {action.kar_id: action for action in db_session.scalars(select(KarTrackerKarAction)).all()}
    assert actions[kar_with_team.id].team_id == team.id
    assert actions[kar_without_team.id].team_id is None


def test_unknown_kar_or_status_is_rejected(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    kar_status = _create_status(db_session, "Geleverd")
    kar = _create_kar(db_session, kar_nummer="B001", status_id=kar_status.id, team_id=None)

    unknown_kar = client.post(BASE_URL, json={"kar_id": 999, "status_id": kar_status.id, "latitude": 1, "longitude": 2})
    unknown_status = client.post(BASE_URL, json={"kar_id": kar.id, "status_id": 999, "latitude": 1, "longitude": 2})

    assert unknown_kar.status_code == 404
    assert unknown_status.status_code == 400
    assert db_session.scalars(select(KarTrackerKarAction)).all() == []


def test_out_of_range_coordinates_are_rejected(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    kar_status = _create_status(db_session, "Geleverd")
    kar = _create_kar(db_session, kar_nummer="B001", status_id=kar_status.id, team_id=None)

    response = client.post(BASE_URL, json={"kar_id": kar.id, "status_id": kar_status.id, "latitude": 91, "longitude": 2})

    assert response.status_code == 422


def test_history_is_newest_first_and_filterable_by_kar(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    kar_status = _create_status(db_session, "Geleverd")
    first_kar = _create_kar(db_session, kar_nummer="B001", status_id=kar_status.id, team_id=None)
    second_kar = _create_kar(db_session, kar_nummer="B002", status_id=kar_status.id, team_id=None)
    for kar_id in (first_kar.id, second_kar.id, first_kar.id):
        client.post(BASE_URL, json={"kar_id": kar_id, "status_id": kar_status.id, "latitude": 1, "longitude": 2})

    all_rows = client.get(BASE_URL).json()
    first_kar_rows = client.get(BASE_URL, params={"kar_id": first_kar.id}).json()

    assert [row["kar_nummer"] for row in all_rows] == ["B001", "B002", "B001"]
    assert [row["id"] for row in all_rows] == sorted((row["id"] for row in all_rows), reverse=True)
    assert len(first_kar_rows) == 2
    assert {row["kar_id"] for row in first_kar_rows} == {first_kar.id}


def test_lookups_list_karren_with_team_and_statuses(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    kar_status = _create_status(db_session, "Geleverd")
    team = _create_team(db_session)
    _create_kar(db_session, kar_nummer="B001", status_id=kar_status.id, team_id=team.id)

    body = client.get(f"{BASE_URL}/lookups").json()

    assert body["karren"][0]["kar_nummer"] == "B001"
    assert body["karren"][0]["team_name"] == "Scouts Wezemaal"
    assert body["karren"][0]["status_id"] == kar_status.id
    assert body["statuses"] == [{"id": kar_status.id, "name": "Geleverd"}]


def test_deleting_a_movement_removes_only_the_log(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    kar_status = _create_status(db_session, "Geleverd")
    kar = _create_kar(db_session, kar_nummer="B001", status_id=kar_status.id, team_id=None)
    action_id = client.post(
        BASE_URL, json={"kar_id": kar.id, "status_id": kar_status.id, "latitude": 1, "longitude": 2}
    ).json()["id"]

    response = client.delete(f"{BASE_URL}/{action_id}")

    assert response.status_code == 204
    assert db_session.scalars(select(KarTrackerKarAction)).all() == []
    db_session.expire_all()
    assert db_session.get(KarTrackerKar, kar.id).last_latitude == 1


def test_view_only_role_can_list_but_not_log(client: TestClient, db_session: Session) -> None:
    _login_with_role(client, db_session, can_view=True)
    kar_status = _create_status(db_session, "Geleverd")
    kar = _create_kar(db_session, kar_nummer="B001", status_id=kar_status.id, team_id=None)

    assert client.get(BASE_URL).status_code == 200
    assert client.get(f"{BASE_URL}/lookups").status_code == 200
    # The map's ground-plan overlay is readable too.
    assert client.get("/api/modules/module-2/groundplans").status_code == 200
    response = client.post(BASE_URL, json={"kar_id": kar.id, "status_id": kar_status.id, "latitude": 1, "longitude": 2})
    assert response.status_code == 403


def test_user_without_actions_permission_cannot_view_history(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Roles Only", screen_key="kartracker.roles", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    assert client.get(BASE_URL).status_code == 403
    assert client.get(f"{BASE_URL}/lookups").status_code == 403
