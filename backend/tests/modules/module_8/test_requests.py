# Tests for Altsien Select's special requests: the Kernlid adds them from
# the wizard (editable only while New), the organisation follows them up.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.modules.module_8.conftest import AltsienWorld, login

BASE = "/api/modules/module-8"


def _create_request(client: TestClient, world: AltsienWorld, text: str = "Extra frigo aub"):
    return client.post(
        f"{BASE}/wizard/{world.own_team.id}/requests?season_id={world.season.id}", json={"text": text}
    )


def test_new_request_starts_in_the_first_status(as_kernlid: TestClient, world: AltsienWorld) -> None:
    response = _create_request(as_kernlid, world)

    assert response.status_code == 201
    body = response.json()
    assert body["status_name"] == "New"
    assert body["editable_by_me"] is True


def test_kernlid_can_edit_and_delete_while_new(as_kernlid: TestClient, world: AltsienWorld) -> None:
    request_id = _create_request(as_kernlid, world).json()["id"]

    edited = as_kernlid.put(f"{BASE}/wizard/{world.own_team.id}/requests/{request_id}", json={"text": "Twee frigo's"})
    assert edited.json()["text"] == "Twee frigo's"

    deleted = as_kernlid.delete(f"{BASE}/wizard/{world.own_team.id}/requests/{request_id}")
    assert deleted.status_code == 204


def test_kernlid_cannot_see_the_follow_up_list(as_kernlid: TestClient, world: AltsienWorld) -> None:
    assert as_kernlid.get(f"{BASE}/requests?season_id={world.season.id}").status_code == 403


def test_organisation_follow_up_locks_the_request_for_the_kernlid(
    client: TestClient, world: AltsienWorld, make_user
) -> None:
    make_user("kernlid@example.com", world.kernlid_role, [world.own_team])
    make_user("org@example.com", world.organisation_role)
    login(client, "kernlid@example.com")
    request_id = _create_request(client, world).json()["id"]

    login(client, "org@example.com")
    listed = client.get(f"{BASE}/requests?season_id={world.season.id}")
    assert [item["id"] for item in listed.json()] == [request_id]
    followed = client.put(
        f"{BASE}/requests/{request_id}",
        json={"status_id": world.status_in_progress.id, "organisation_note": "We bekijken het"},
    )
    assert followed.status_code == 200
    assert followed.json()["status_name"] == "In Progress"

    login(client, "kernlid@example.com")
    edit = client.put(f"{BASE}/wizard/{world.own_team.id}/requests/{request_id}", json={"text": "Toch niet"})
    assert edit.status_code == 400


def test_status_in_use_cannot_be_deleted(
    client: TestClient, world: AltsienWorld, make_user, db_session: Session
) -> None:
    make_user("kernlid@example.com", world.kernlid_role, [world.own_team])
    login(client, "kernlid@example.com")
    _create_request(client, world)
    # A plain Kernlid has no rights on the statuses screen at all.
    assert client.delete(f"{BASE}/request-statuses/{world.status_new.id}").status_code == 403

    admin = make_user("admin@example.com", None)
    admin.is_super_admin = True
    db_session.commit()
    login(client, "admin@example.com")

    assert client.delete(f"{BASE}/request-statuses/{world.status_new.id}").status_code == 400
    assert client.delete(f"{BASE}/request-statuses/{world.status_completed.id}").status_code == 204
