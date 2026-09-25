# These tests check the login-related API endpoints end-to-end: logging
# in with correct/incorrect credentials, reading "who am I", refreshing a
# session, and logging out. They use the FastAPI TestClient, which sends
# real HTTP requests to our app (backed by a temporary test database, see
# conftest.py) and follows cookies the same way a browser would.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.user import User


def _create_user(db_session: Session, *, email: str, password: str, is_active: bool = True) -> User:
    """Test helper: insert a user directly into the database, bypassing the API."""
    user = User(email=email, hashed_password=hash_password(password), display_name="Test User", is_active=is_active)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_with_correct_credentials_succeeds(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="user@example.com", password="correct-password")

    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    # The login response should also have set our two auth cookies.
    assert "rwcrew_access_token" in response.cookies
    assert "rwcrew_refresh_token" in response.cookies


def test_login_with_wrong_password_is_rejected(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="user@example.com", password="correct-password")

    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong-password"})

    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "anything"})

    assert response.status_code == 401


def test_login_for_a_disabled_account_is_rejected(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="disabled@example.com", password="correct-password", is_active=False)

    response = client.post("/api/auth/login", json={"email": "disabled@example.com", "password": "correct-password"})

    assert response.status_code == 401


def test_me_without_logging_in_is_rejected(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_after_logging_in_returns_the_logged_in_user(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="user@example.com", password="correct-password")
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_logout_then_me_is_rejected_again(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="user@example.com", password="correct-password")
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 401


def test_refresh_issues_a_new_working_session(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="user@example.com", password="correct-password")
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200

    # The refreshed session should still be able to call protected endpoints.
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200


def test_reusing_an_already_rotated_refresh_token_is_rejected(client: TestClient, db_session: Session) -> None:
    # This is the "reuse detection" behaviour: once a refresh token has
    # been used once, using that SAME token text again must fail — it was
    # already replaced by a new one. This protects against a stolen
    # refresh token being used after the real user has already refreshed.
    _create_user(db_session, email="user@example.com", password="correct-password")
    login_response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})
    original_refresh_token = login_response.cookies["rwcrew_refresh_token"]

    # Use it once — this should succeed and rotate it (the shared client's
    # cookie jar now holds a brand-new refresh token afterwards).
    first_refresh = client.post("/api/auth/refresh")
    assert first_refresh.status_code == 200

    # Now try to use that SAME original token again, from a separate
    # client that has never seen the rotated replacement.
    replay_client = TestClient(client.app)
    replay_client.cookies.set("rwcrew_refresh_token", original_refresh_token)
    second_refresh = replay_client.post("/api/auth/refresh")

    assert second_refresh.status_code == 401


def test_refresh_never_extends_the_login_session(client: TestClient, db_session: Session) -> None:
    # The session ends a fixed number of hours after the password was
    # entered; renewing must keep that end, and once it has passed the user
    # has to log in again.
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.db.models.refresh_token import RefreshToken

    _create_user(db_session, email="user@example.com", password="correct-password")
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})
    login_end = db_session.scalars(select(RefreshToken)).one().expires_at

    assert client.post("/api/auth/refresh").status_code == 200
    ends = {record.expires_at for record in db_session.scalars(select(RefreshToken))}
    assert ends == {login_end}

    # Pretend the 6 hours have passed: the refresh must now be refused.
    for record in db_session.scalars(select(RefreshToken)):
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    assert client.post("/api/auth/refresh").status_code == 401
