# Tests for Kar Planning's own season dropdown endpoint (module_2/router.py
# list_open_seasons): only open seasons, newest first, gated by the Kar
# Planning screen — so its users don't need MasterData to pick a season.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.season import Season
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)


def _login_with_role_on(client: TestClient, db_session: Session, screen_key: str) -> None:
    """Log in as a fresh user with view rights on one KarTracker screen."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Viewer", screen_key=screen_key, can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")


def test_seasons_lists_only_open_seasons_newest_first(client: TestClient, db_session: Session) -> None:
    _login_with_role_on(client, db_session, "kartracker.karplanning")
    db_session.add_all(
        [
            Season(name="2025", periode_open=True),
            Season(name="2026", periode_open=True),
            Season(name="2024", periode_open=False),
        ]
    )
    db_session.commit()

    response = client.get("/api/modules/module-2/seasons")

    assert response.status_code == 200
    assert [season["name"] for season in response.json()] == ["2026", "2025"]


def test_seasons_requires_the_kar_planning_screen(client: TestClient, db_session: Session) -> None:
    _login_with_role_on(client, db_session, "kartracker.karmanagement")

    assert client.get("/api/modules/module-2/seasons").status_code == 403
