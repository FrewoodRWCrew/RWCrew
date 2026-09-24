# These tests cover the smartphone app's login API (/api/mobile/v1/auth/*):
# tokens in the JSON body instead of cookies, Bearer-token access to
# protected endpoints, refresh-token rotation/reuse detection, and the
# minimum-app-version gate. They also confirm the web app's cookie login
# still works unchanged next to the new Bearer path.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User
from app.mobile.version_gate import parse_version

BASE = "/api/mobile/v1/auth"


def _create_user(db_session: Session, *, email: str = "phone@example.com", password: str = "correct-password") -> User:
    """Test helper: insert a user directly into the database."""
    user = User(email=email, hashed_password=hash_password(password), display_name="Phone User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client: TestClient, email: str = "phone@example.com", password: str = "correct-password"):
    return client.post(f"{BASE}/login", json={"email": email, "password": password})


def test_mobile_login_returns_tokens_in_the_body_not_cookies(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)

    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] == settings.access_token_minutes * 60
    assert body["user"]["email"] == "phone@example.com"
    # Nothing must be set as a cookie for the phone.
    assert "rwcrew_access_token" not in response.cookies


def test_mobile_login_with_wrong_password_is_rejected(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)

    assert _login(client, password="wrong").status_code == 401


def test_bearer_token_grants_access_to_a_protected_endpoint(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)
    access_token = _login(client).json()["access_token"]

    response = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "phone@example.com"


def test_bearer_token_also_works_on_existing_web_endpoints(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)
    access_token = _login(client).json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200


def test_missing_or_garbage_bearer_token_is_rejected(client: TestClient) -> None:
    assert client.get(f"{BASE}/me").status_code == 401
    assert client.get(f"{BASE}/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    assert client.get(f"{BASE}/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_a_refresh_token_cannot_be_used_as_an_access_token(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)
    refresh_token = _login(client).json()["refresh_token"]

    response = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {refresh_token}"})

    assert response.status_code == 401


def test_refresh_rotates_tokens_and_rejects_reuse_of_the_old_one(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)
    old_refresh_token = _login(client).json()["refresh_token"]

    first = client.post(f"{BASE}/refresh", json={"refresh_token": old_refresh_token})
    assert first.status_code == 200
    assert first.json()["refresh_token"] != old_refresh_token

    # Presenting the already-used token again must fail.
    reused = client.post(f"{BASE}/refresh", json={"refresh_token": old_refresh_token})
    assert reused.status_code == 401

    # The new token, on the other hand, keeps working.
    second = client.post(f"{BASE}/refresh", json={"refresh_token": first.json()["refresh_token"]})
    assert second.status_code == 200


def test_logout_revokes_the_refresh_token(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)
    refresh_token = _login(client).json()["refresh_token"]

    assert client.post(f"{BASE}/logout", json={"refresh_token": refresh_token}).status_code == 200
    assert client.post(f"{BASE}/refresh", json={"refresh_token": refresh_token}).status_code == 401


def test_web_cookie_login_still_works_unchanged(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)

    login = client.post("/api/auth/login", json={"email": "phone@example.com", "password": "correct-password"})

    assert login.status_code == 200
    assert "rwcrew_access_token" in login.cookies
    assert client.get("/api/auth/me").status_code == 200


def test_cookie_wins_over_a_bearer_header(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)
    client.post("/api/auth/login", json={"email": "phone@example.com", "password": "correct-password"})

    # A garbage Bearer header must not break a valid cookie session.
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 200


def test_version_gate_allows_everything_by_default(client: TestClient, db_session: Session) -> None:
    _create_user(db_session)

    assert _login(client).status_code == 200


def test_version_gate_rejects_old_or_unversioned_apps(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_user(db_session)
    monkeypatch.setattr(settings, "mobile_min_app_version", "1.2.0")
    body = {"email": "phone@example.com", "password": "correct-password"}

    # No version header, or an older version: 426 Upgrade Required.
    assert client.post(f"{BASE}/login", json=body).status_code == 426
    assert client.post(f"{BASE}/login", json=body, headers={"X-App-Version": "1.1.9"}).status_code == 426
    assert client.post(f"{BASE}/login", json=body, headers={"X-App-Version": "garbage"}).status_code == 426

    # The minimum itself, newer versions, and test pre-release builds pass.
    assert client.post(f"{BASE}/login", json=body, headers={"X-App-Version": "1.2.0"}).status_code == 200
    assert client.post(f"{BASE}/login", json=body, headers={"X-App-Version": "1.10.0"}).status_code == 200
    assert client.post(f"{BASE}/login", json=body, headers={"X-App-Version": "1.3.0-test.4"}).status_code == 200


def test_version_gate_does_not_affect_the_web_app(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_user(db_session)
    monkeypatch.setattr(settings, "mobile_min_app_version", "9.9.9")

    login = client.post("/api/auth/login", json={"email": "phone@example.com", "password": "correct-password"})

    assert login.status_code == 200


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1.4.0", (1, 4, 0)), ("v1.4.0", (1, 4, 0)), ("1.4", (1, 4, 0)), ("1.4.0-test.3", (1, 4, 0)), ("abc", None), ("", None)],
)
def test_parse_version(raw: str, expected: tuple[int, int, int] | None) -> None:
    assert parse_version(raw) == expected
