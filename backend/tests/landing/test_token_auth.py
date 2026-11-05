# The Raspberry Pi app's login: the same accounts and tokens as the website,
# but handed over in the response body and sent back as an
# "Authorization: Bearer" header (it has no cookies). Checks the login, the
# Bearer way in, the rotated refresh, logout and the login history's "pi".

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.login_history import LoginHistory
from tests.landing.test_auth import _create_user


def _token_login(client: TestClient, password: str = "correct-password"):
    return client.post("/api/auth/token", json={"email": "pi@example.com", "password": password})


def test_token_login_gives_tokens_without_cookies(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="pi@example.com", password="correct-password")

    response = _token_login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "pi@example.com"
    assert body["access_token"] and body["refresh_token"]
    assert body["access_expires_at"] <= body["session_expires_at"]
    # No cookies: the Pi keeps the tokens itself.
    assert "rwcrew_access_token" not in response.cookies
    # The login history says it came from the Pi app.
    assert db_session.scalar(select(LoginHistory.source).order_by(LoginHistory.id.desc()).limit(1)) == "pi"


def test_wrong_password_is_rejected(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="pi@example.com", password="correct-password")

    assert _token_login(client, "wrong").status_code == 401


def test_bearer_header_logs_the_request_in(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="pi@example.com", password="correct-password")
    access_token = _token_login(client).json()["access_token"]

    assert client.get("/api/auth/me").status_code == 401
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200 and me.json()["email"] == "pi@example.com"
    # A refresh token or garbage is no access token.
    refresh_token = _token_login(client).json()["refresh_token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh_token}"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_refresh_rotates_and_logout_ends_the_session(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="pi@example.com", password="correct-password")
    first = _token_login(client).json()

    renewed = client.post("/api/auth/token/refresh", json={"refresh_token": first["refresh_token"]})
    assert renewed.status_code == 200
    second = renewed.json()
    assert second["refresh_token"] != first["refresh_token"]
    # The session keeps its end: renewing never extends the login.
    assert second["session_expires_at"] == first["session_expires_at"]
    # The old refresh token is used up.
    assert client.post("/api/auth/token/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401

    assert client.post("/api/auth/token/logout", json={"refresh_token": second["refresh_token"]}).json() == {"logged_out": True}
    assert client.post("/api/auth/token/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401
