# Tests for the endpoints the phone's Interventie Aanvragen screens rely on:
# the full per-action /me/permissions, the one-call /lookups for the request
# form, and fetching one request by id. All gated by the requests screen's
# own permissions, like the rest of the "Akties" screen.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_requests_user_role import InterventionRequestsUserRole
from app.db.models.intervention_status import InterventionStatus
from app.db.models.team import Team
from app.db.models.teamkar_member import TeamKarMember
from app.modules.module_3.screens import sync_screens
from tests.modules.module_3.test_roles import (
    _create_intervention_requests_module,
    _create_role_with_permissions,
    _create_user,
    _grant_module_access,
    _login,
)

REQUESTS_SCREEN = "interventionrequests.requests"


def _login_with_requests_role(client: TestClient, db_session: Session, **permissions: bool) -> None:
    """Log in as a fresh user whose only role has `permissions` on the
    requests screen (e.g. can_view=True, can_create=True).
    """
    sync_screens(db_session)
    module = _create_intervention_requests_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(db_session, name="Requests", screen_key=REQUESTS_SCREEN, **permissions)
    db_session.add(InterventionRequestsUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    _login(client, "member@example.com")


def _create_status(db_session: Session, name: str = "Nieuw") -> InterventionStatus:
    item = InterventionStatus(name=name)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_me_permissions_lists_create_edit_and_delete_separately(client: TestClient, db_session: Session) -> None:
    _login_with_requests_role(client, db_session, can_view=True, can_create=True)

    body = client.get("/api/modules/module-3/me/permissions").json()

    assert body["viewable_screen_keys"] == [REQUESTS_SCREEN]
    assert body["creatable_screen_keys"] == [REQUESTS_SCREEN]
    assert body["editable_screen_keys"] == []
    assert body["deletable_screen_keys"] == []


def test_lookups_returns_statuses_teams_and_teamkar_members(client: TestClient, db_session: Session) -> None:
    _login_with_requests_role(client, db_session, can_view=True)
    _create_status(db_session, "Nieuw")
    db_session.add(Team(name="Scouts Wezemaal"))
    teamkar_user = _create_user(db_session, email="kar@example.com")
    db_session.add(TeamKarMember(user_id=teamkar_user.id))
    db_session.commit()

    response = client.get("/api/modules/module-3/lookups")

    # The requests screen alone is enough — no MasterData "statuses" screen needed.
    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["statuses"]] == ["Nieuw"]
    assert [item["name"] for item in body["teams"]] == ["Scouts Wezemaal"]
    assert [item["display_name"] for item in body["teamkar_members"]] == ["kar@example.com"]


def test_lookups_requires_the_requests_screen(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_intervention_requests_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "member@example.com")

    assert client.get("/api/modules/module-3/lookups").status_code == 403


def test_get_one_request_by_id(client: TestClient, db_session: Session) -> None:
    _login_with_requests_role(client, db_session, can_view=True)
    new_status = _create_status(db_session)
    request = InterventionRequest(request_number="IR-0001", question="Kar vol", status_id=new_status.id)
    db_session.add(request)
    db_session.commit()

    found = client.get(f"/api/modules/module-3/intervention-requests/{request.id}")
    missing = client.get("/api/modules/module-3/intervention-requests/999999")

    assert found.status_code == 200
    assert found.json()["request_number"] == "IR-0001"
    assert missing.status_code == 404
