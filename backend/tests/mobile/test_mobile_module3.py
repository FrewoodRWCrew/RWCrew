# Tests for the phone's slice of Intervention Requests
# (/api/mobile/v1/module-3): KPI overview + the requests ("Akties") screen.
# The key rules: rights are exactly the web roles' rights, and everything
# the phone must NOT do (delete, PDF, statuses/roles admin) doesn't exist.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.teamkar_member import TeamKarMember
from tests.mobile.helpers import (
    bearer,
    create_request,
    create_status,
    create_team,
    create_user,
    get_or_create_module,
    give_requests_role,
    grant_access,
)

BASE = "/api/mobile/v1/module-3"


def _user_with_rights(db: Session, email: str, **rights: bool):
    """A user with module-3 access and a role with the given requests rights."""
    user = create_user(db, email)
    grant_access(db, user, "module-3")
    give_requests_role(db, user, **rights)
    return user


def _body(status_id: int, **overrides):
    return {"team_name": "Vereniging X", "question": "Kar stuk", "status_id": status_id, **overrides}


# --- KPI overview ----------------------------------------------------------


def test_dashboard_needs_module_access(client: TestClient, db_session: Session) -> None:
    create_user(db_session, "a@example.com")
    # The module exists, but this user was never granted access to it.
    get_or_create_module(db_session, "module-3")

    assert client.get(f"{BASE}/dashboard", headers=bearer(client, "a@example.com")).status_code == 403


def test_dashboard_numbers_match_the_web_dashboard(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)
    open_status = create_status(db_session, "Nieuw", is_open=True)
    closed_status = create_status(db_session, "Klaar", is_open=False, color="green")
    create_request(db_session, open_status.id, number="IA26_0001")
    create_request(db_session, open_status.id, number="IA26_0002")
    create_request(db_session, closed_status.id, number="IA26_0003")
    headers = bearer(client, "a@example.com")

    phone = client.get(f"{BASE}/dashboard", headers=headers).json()
    web = client.get("/api/modules/module-3/dashboard", headers=headers).json()

    assert phone == web
    assert (phone["total_requests"], phone["open_requests"], phone["closed_requests"]) == (3, 2, 1)


# --- Permissions -----------------------------------------------------------


@pytest.mark.parametrize(
    ("rights", "expected"),
    [
        ({}, (False, False, False)),
        ({"can_view": True}, (True, False, False)),
        ({"can_view": True, "can_create": True}, (True, True, False)),
        ({"can_view": True, "can_edit": True}, (True, False, True)),
    ],
)
def test_permissions_reflect_the_web_role(client: TestClient, db_session: Session, rights, expected) -> None:
    _user_with_rights(db_session, "a@example.com", **rights)

    response = client.get(f"{BASE}/permissions", headers=bearer(client, "a@example.com"))

    body = response.json()
    assert (body["can_view_requests"], body["can_create_requests"], body["can_edit_requests"]) == expected


def test_super_admin_with_module_access_can_do_everything(client: TestClient, db_session: Session) -> None:
    boss = create_user(db_session, "boss@example.com", is_super_admin=True)
    grant_access(db_session, boss, "module-3")

    body = client.get(f"{BASE}/permissions", headers=bearer(client, "boss@example.com")).json()

    assert body == {"can_view_requests": True, "can_create_requests": True, "can_edit_requests": True}


# --- Lookups ---------------------------------------------------------------


def test_lookups_return_statuses_teams_and_teamkar_without_statuses_permission(
    client: TestClient, db_session: Session
) -> None:
    # This user can view requests but has NO permission on the web's
    # "statuses" or "teamkar" screens.
    _user_with_rights(db_session, "a@example.com", can_view=True)
    create_status(db_session, "Nieuw")
    create_team(db_session, "Team A")
    member = create_user(db_session, "member@example.com")
    db_session.add(TeamKarMember(user_id=member.id))
    db_session.commit()

    body = client.get(f"{BASE}/lookups", headers=bearer(client, "a@example.com")).json()

    assert [item["name"] for item in body["statuses"]] == ["Nieuw"]
    assert [item["name"] for item in body["teams"]] == ["Team A"]
    assert [item["display_name"] for item in body["teamkar_members"]] == ["member@example.com"]


def test_lookups_need_the_requests_view_right(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com")

    assert client.get(f"{BASE}/lookups", headers=bearer(client, "a@example.com")).status_code == 403


# --- List ------------------------------------------------------------------


def test_list_requests_and_open_only_filter(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)
    open_status = create_status(db_session, "Nieuw", is_open=True)
    closed_status = create_status(db_session, "Klaar", is_open=False)
    create_request(db_session, open_status.id, number="IA26_0001")
    create_request(db_session, closed_status.id, number="IA26_0002")
    headers = bearer(client, "a@example.com")

    everything = client.get(f"{BASE}/intervention-requests", headers=headers).json()
    only_open = client.get(f"{BASE}/intervention-requests?open_only=true", headers=headers).json()

    assert {item["request_number"] for item in everything} == {"IA26_0001", "IA26_0002"}
    assert [item["request_number"] for item in only_open] == ["IA26_0001"]


def test_get_one_request_needs_the_view_right_and_an_existing_request(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "viewer@example.com", can_view=True)
    _user_with_rights(db_session, "creator@example.com", can_create=True)
    status = create_status(db_session)
    existing = create_request(db_session, status.id, number="IA26_0042")

    found = client.get(f"{BASE}/intervention-requests/{existing.id}", headers=bearer(client, "viewer@example.com"))
    missing = client.get(f"{BASE}/intervention-requests/9999", headers=bearer(client, "viewer@example.com"))
    denied = client.get(f"{BASE}/intervention-requests/{existing.id}", headers=bearer(client, "creator@example.com"))

    assert found.status_code == 200 and found.json()["request_number"] == "IA26_0042"
    assert missing.status_code == 404
    assert denied.status_code == 403


def test_list_needs_the_view_right(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_create=True)

    assert client.get(f"{BASE}/intervention-requests", headers=bearer(client, "a@example.com")).status_code == 403


# --- Create ----------------------------------------------------------------


def test_create_sets_the_request_number_and_needs_the_create_right(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "viewer@example.com", can_view=True)
    _user_with_rights(db_session, "creator@example.com", can_view=True, can_create=True)
    status = create_status(db_session)

    denied = client.post(
        f"{BASE}/intervention-requests", json=_body(status.id), headers=bearer(client, "viewer@example.com")
    )
    created = client.post(
        f"{BASE}/intervention-requests", json=_body(status.id), headers=bearer(client, "creator@example.com")
    )

    assert denied.status_code == 403
    assert created.status_code == 201
    assert created.json()["request_number"].startswith("IA") and created.json()["request_number"].endswith("_0001")
    # The next one gets the next number.
    second = client.post(
        f"{BASE}/intervention-requests", json=_body(status.id), headers=bearer(client, "creator@example.com")
    )
    assert second.json()["request_number"].endswith("_0002")


def test_create_rejects_unknown_references(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True, can_create=True)
    status = create_status(db_session)
    headers = bearer(client, "a@example.com")

    assert client.post(f"{BASE}/intervention-requests", json=_body(9999), headers=headers).status_code == 404
    unknown_team = {"question": "x", "status_id": status.id, "team_id": 9999}
    assert client.post(f"{BASE}/intervention-requests", json=unknown_team, headers=headers).status_code == 404
    unknown_kar = _body(status.id, team_cart_user_id=9999)
    assert client.post(f"{BASE}/intervention-requests", json=unknown_kar, headers=headers).status_code == 404


def test_create_needs_exactly_one_of_team_id_or_team_name(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True, can_create=True)
    status = create_status(db_session)
    team = create_team(db_session)
    headers = bearer(client, "a@example.com")

    both = _body(status.id, team_id=team.id)
    neither = {"question": "x", "status_id": status.id}

    assert client.post(f"{BASE}/intervention-requests", json=both, headers=headers).status_code == 422
    assert client.post(f"{BASE}/intervention-requests", json=neither, headers=headers).status_code == 422


# --- Update ----------------------------------------------------------------


def test_update_changes_fields_but_not_number_or_timestamp(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True, can_edit=True)
    open_status = create_status(db_session, "Nieuw")
    done_status = create_status(db_session, "Klaar", is_open=False, color="green")
    existing = create_request(db_session, open_status.id, number="IA26_0007")
    original_timestamp = existing.submitted_at.isoformat()

    response = client.put(
        f"{BASE}/intervention-requests/{existing.id}",
        json=_body(done_status.id, handled_by="Piet", question="Opgelost"),
        headers=bearer(client, "a@example.com"),
    )

    body = response.json()
    assert response.status_code == 200
    assert (body["status_id"], body["handled_by"], body["question"]) == (done_status.id, "Piet", "Opgelost")
    assert body["request_number"] == "IA26_0007"
    assert body["submitted_at"].startswith(original_timestamp[:19])


def test_update_needs_the_edit_right_and_an_existing_request(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "viewer@example.com", can_view=True)
    _user_with_rights(db_session, "editor@example.com", can_view=True, can_edit=True)
    status = create_status(db_session)
    existing = create_request(db_session, status.id)

    denied = client.put(
        f"{BASE}/intervention-requests/{existing.id}", json=_body(status.id), headers=bearer(client, "viewer@example.com")
    )
    missing = client.put(
        f"{BASE}/intervention-requests/9999", json=_body(status.id), headers=bearer(client, "editor@example.com")
    )

    assert denied.status_code == 403
    assert missing.status_code == 404


# --- What must NOT exist on the phone --------------------------------------


def test_delete_pdf_and_admin_endpoints_do_not_exist(client: TestClient, db_session: Session) -> None:
    boss = create_user(db_session, "boss@example.com", is_super_admin=True)
    grant_access(db_session, boss, "module-3")
    status = create_status(db_session)
    existing = create_request(db_session, status.id)
    headers = bearer(client, "boss@example.com")

    # Even the super admin cannot delete, print, or manage anything from the phone.
    assert client.delete(f"{BASE}/intervention-requests/{existing.id}", headers=headers).status_code in (404, 405)
    assert client.get(f"{BASE}/intervention-requests/{existing.id}/pdf", headers=headers).status_code == 404
    for path in ("roles", "users", "screens", "teamkar/users", "intervention-statuses"):
        assert client.get(f"{BASE}/{path}", headers=headers).status_code == 404


# --- Version gate ----------------------------------------------------------


def test_version_gate_applies(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)
    headers = bearer(client, "a@example.com")
    monkeypatch.setattr(settings, "mobile_min_app_version", "3.0.0")

    assert client.get(f"{BASE}/dashboard", headers=headers).status_code == 426
    assert client.get(f"{BASE}/dashboard", headers={**headers, "X-App-Version": "3.0.1"}).status_code == 200
