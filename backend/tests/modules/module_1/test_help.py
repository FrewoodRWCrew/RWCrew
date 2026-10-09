# TagScan's help manual endpoint (GET /help/pdf): module access is needed,
# and a topic of a screen the user can't view is refused — the general
# chapters (how it works, the overview) are open to everyone with access.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.tagscan_user_role import TagscanUserRole
from app.modules.module_1.screens import sync_screens
from tests.modules.module_1.test_roles import (
    _create_role_with_permissions,
    _create_tagscan_module,
    _create_user,
    _grant_module_access,
)

BASE = "/api/modules/module-1"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200


def _assert_pdf(response) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_help_needs_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_tagscan_module(db_session)
    _create_user(db_session, email="outsider@example.com")
    _login(client, "outsider@example.com")

    assert client.get(f"{BASE}/help/pdf").status_code == 403


def test_topics_follow_the_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="scanner@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(db_session, name="Lezer", screen_key="tagscan.tag-headerdata", can_view=True)
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    _login(client, "scanner@example.com")

    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"locale": "en"}))
    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"topic": "overview"}))
    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"topic": "header-data"}))
    assert client.get(f"{BASE}/help/pdf", params={"topic": "scanners"}).status_code == 404
