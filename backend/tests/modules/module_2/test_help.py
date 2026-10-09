# KarTracker's help manual endpoint (GET /help/pdf): module access is
# needed, and a topic of a screen the user can't view is refused — the
# general chapters (how it works, the overview, the phone) are open to
# everyone with access.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)

BASE = "/api/modules/module-2"


def _assert_pdf(response) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_help_needs_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    create_kartracker_module(db_session)
    create_user(db_session, email="outsider@example.com")
    login(client, "outsider@example.com")

    assert client.get(f"{BASE}/help/pdf").status_code == 403


def test_topics_follow_the_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="driver@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Chauffeur", screen_key="kartracker.actions", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "driver@example.com")

    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"locale": "en"}))
    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"topic": "phone"}))
    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"topic": "movement"}))
    assert client.get(f"{BASE}/help/pdf", params={"topic": "plan-kar"}).status_code == 404
