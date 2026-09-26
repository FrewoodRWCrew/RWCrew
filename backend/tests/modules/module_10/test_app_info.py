# These tests check the "Mobile App" download page's data endpoint
# (module-10): it needs a login, and it returns the install links and
# changelog from the environment's settings, hiding empty ones.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User


def _login_regular_user(client: TestClient, db_session: Session) -> None:
    db_session.add(
        User(email="member@example.com", hashed_password=hash_password("password123"), display_name="Member")
    )
    db_session.commit()
    client.post("/api/auth/login", json={"email": "member@example.com", "password": "password123"})


def test_app_info_requires_login(client: TestClient) -> None:
    assert client.get("/api/modules/module-10/app-info").status_code == 401


def test_app_info_hides_unset_links(client: TestClient, db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "mobile_ios_testflight_url", "")
    monkeypatch.setattr(settings, "mobile_android_download_url", "")
    monkeypatch.setattr(settings, "mobile_latest_version", "")
    monkeypatch.setattr(settings, "mobile_changelog", "")
    _login_regular_user(client, db_session)

    body = client.get("/api/modules/module-10/app-info").json()

    assert body == {
        "ios_testflight_url": None,
        "android_download_url": None,
        "latest_version": None,
        "changelog": [],
    }


def test_app_info_returns_configured_values(client: TestClient, db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "mobile_ios_testflight_url", "https://testflight.apple.com/join/abc")
    monkeypatch.setattr(settings, "mobile_latest_version", "1.0.0")
    monkeypatch.setattr(settings, "mobile_changelog", "First release\n\n  KPI overview  \n")
    _login_regular_user(client, db_session)

    body = client.get("/api/modules/module-10/app-info").json()

    assert body["ios_testflight_url"] == "https://testflight.apple.com/join/abc"
    assert body["latest_version"] == "1.0.0"
    assert body["changelog"] == ["First release", "KPI overview"]
