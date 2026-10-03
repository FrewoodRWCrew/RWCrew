# These tests check the phone-app install page's data endpoint (module-10):
# it needs a login, and it returns the phone section's (/m) address and a QR
# code of it, built from the environment's APP_PUBLIC_URL — or nothing when
# that isn't configured.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User

INSTALL_INFO = "/api/modules/module-10/install-info"


def _login_regular_user(client: TestClient, db_session: Session) -> None:
    db_session.add(
        User(email="member@example.com", hashed_password=hash_password("password123"), display_name="Member")
    )
    db_session.commit()
    client.post("/api/auth/login", json={"email": "member@example.com", "password": "password123"})


def test_install_info_requires_login(client: TestClient) -> None:
    assert client.get(INSTALL_INFO).status_code == 401


def test_install_info_is_empty_without_a_public_url(client: TestClient, db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_public_url", "")
    _login_regular_user(client, db_session)

    body = client.get(INSTALL_INFO).json()

    assert body == {"install_url": None, "qr_code_data_uri": None}


def test_install_info_points_at_the_phone_section(client: TestClient, db_session: Session, monkeypatch) -> None:
    # A trailing slash on the setting must not give a double slash.
    monkeypatch.setattr(settings, "app_public_url", "https://test.rwcrew.eu/")
    _login_regular_user(client, db_session)

    body = client.get(INSTALL_INFO).json()

    assert body["install_url"] == "https://test.rwcrew.eu/m"
    assert body["qr_code_data_uri"].startswith("data:image/svg+xml")
