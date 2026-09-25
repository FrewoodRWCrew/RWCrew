# These tests check the two ways a password can change: a super admin
# resetting someone else's (PATCH /api/admin/users/{id}) and a user changing
# their own (POST /api/auth/change-password). Both must end old sessions.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.user import User
from app.main import app

OLD = "old-password-1"
NEW = "brand-new-pass-2"


def _user(db_session: Session, email: str, *, is_super_admin: bool = False) -> User:
    user = User(email=email, hashed_password=hash_password(OLD), display_name=email, is_super_admin=is_super_admin)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client: TestClient, email: str, password: str = OLD) -> int:
    return client.post("/api/auth/login", json={"email": email, "password": password}).status_code


def test_admin_can_reset_a_password_and_old_sessions_end(client: TestClient, db_session: Session) -> None:
    _user(db_session, "admin@example.com", is_super_admin=True)
    target = _user(db_session, "user@example.com")
    _login(client, "admin@example.com")

    # The target user has a live session in a second "browser".
    victim = TestClient(app)
    assert _login(victim, "user@example.com") == 200

    response = client.patch(f"/api/admin/users/{target.id}", json={"password": NEW})
    assert response.status_code == 200

    # Old password no longer works, the new one does, and the old session can't be renewed.
    assert _login(TestClient(app), "user@example.com", OLD) == 401
    assert _login(TestClient(app), "user@example.com", NEW) == 200
    assert victim.post("/api/auth/refresh").status_code == 401


def test_reset_password_needs_super_admin_and_min_length(client: TestClient, db_session: Session) -> None:
    _user(db_session, "admin@example.com", is_super_admin=True)
    target = _user(db_session, "user@example.com")
    _user(db_session, "other@example.com")

    _login(client, "other@example.com")
    assert client.patch(f"/api/admin/users/{target.id}", json={"password": NEW}).status_code == 403

    admin = TestClient(app)
    _login(admin, "admin@example.com")
    assert admin.patch(f"/api/admin/users/{target.id}", json={"password": "short"}).status_code == 422


def test_user_can_change_own_password(client: TestClient, db_session: Session) -> None:
    _user(db_session, "user@example.com")
    _login(client, "user@example.com")
    other_session = TestClient(app)
    _login(other_session, "user@example.com")

    response = client.post("/api/auth/change-password", json={"current_password": OLD, "new_password": NEW})
    assert response.status_code == 200

    # This session stays logged in; the other one is ended; only the new password logs in.
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/refresh").status_code == 200
    assert other_session.post("/api/auth/refresh").status_code == 401
    assert _login(TestClient(app), "user@example.com", OLD) == 401
    assert _login(TestClient(app), "user@example.com", NEW) == 200


def test_change_password_rejects_wrong_current_or_same_password(client: TestClient, db_session: Session) -> None:
    _user(db_session, "user@example.com")
    _login(client, "user@example.com")

    wrong = client.post("/api/auth/change-password", json={"current_password": "nope-nope-1", "new_password": NEW})
    assert wrong.status_code == 400
    same = client.post("/api/auth/change-password", json={"current_password": OLD, "new_password": OLD})
    assert same.status_code == 400
    # Not logged in at all.
    assert TestClient(app).post("/api/auth/change-password", json={"current_password": OLD, "new_password": NEW}).status_code == 401
