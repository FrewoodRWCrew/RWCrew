# Atelier's help manual endpoint (GET /help/pdf): module access is needed,
# and a topic of a screen the user can't view is refused.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.atelier_user_role import AtelierUserRole
from app.modules.module_5.screens import sync_screens

from tests.modules.module_5.test_roles import (
    _create_atelier_module,
    _create_role_with_permissions,
    _create_user,
    _grant_module_access,
    _login,
)

BASE = "/api/modules/module-5"


def _assert_pdf(response) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_full_manual_and_one_topic(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    user = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, user, module)
    _login(client, "admin@example.com")

    _assert_pdf(client.get(f"{BASE}/help/pdf"))
    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"locale": "en", "topic": "roles"}))


def test_help_needs_module_access(client: TestClient, db_session: Session) -> None:
    _create_atelier_module(db_session)
    _create_user(db_session, email="outsider@example.com")
    _login(client, "outsider@example.com")

    assert client.get(f"{BASE}/help/pdf").status_code == 403


def test_topic_of_a_hidden_screen_is_not_found(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    user = _create_user(db_session, email="reader@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(db_session, name="Lezer", screen_key="atelier.kpi", can_view=True)
    db_session.add(AtelierUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    _login(client, "reader@example.com")

    _assert_pdf(client.get(f"{BASE}/help/pdf"))
    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"topic": "overview"}))
    assert client.get(f"{BASE}/help/pdf", params={"topic": "roles"}).status_code == 404
