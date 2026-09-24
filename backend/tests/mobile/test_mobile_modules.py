# Tests for the phone's landing-page endpoint (/api/mobile/v1/modules):
# which tiles a user gets. A tile needs (1) phone support, (2) an active
# module and (3) an access grant from the super admin.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from tests.mobile.helpers import bearer, create_user, get_or_create_module, grant_access

URL = "/api/mobile/v1/modules"


def test_user_with_module_3_access_gets_exactly_one_tile(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "a@example.com")
    grant_access(db_session, user, "module-3")

    response = client.get(URL, headers=bearer(client, "a@example.com"))

    assert response.status_code == 200
    assert [module["key"] for module in response.json()] == ["module-3"]


def test_modules_the_phone_does_not_support_are_hidden(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "a@example.com")
    grant_access(db_session, user, "module-1")
    grant_access(db_session, user, "module-3")

    response = client.get(URL, headers=bearer(client, "a@example.com"))

    # module-1 (TagScan) is accessible on the web but not on the phone.
    assert [module["key"] for module in response.json()] == ["module-3"]


def test_user_without_any_access_gets_no_tiles(client: TestClient, db_session: Session) -> None:
    create_user(db_session, "a@example.com")

    assert client.get(URL, headers=bearer(client, "a@example.com")).json() == []


def test_super_admin_without_a_grant_gets_no_tiles(client: TestClient, db_session: Session) -> None:
    create_user(db_session, "boss@example.com", is_super_admin=True)
    get_or_create_module(db_session, "module-3")

    assert client.get(URL, headers=bearer(client, "boss@example.com")).json() == []


def test_a_switched_off_module_is_hidden(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "a@example.com")
    module = get_or_create_module(db_session, "module-3")
    grant_access(db_session, user, "module-3")
    module.is_active = False
    db_session.commit()

    assert client.get(URL, headers=bearer(client, "a@example.com")).json() == []


def test_requires_login(client: TestClient) -> None:
    assert client.get(URL).status_code == 401


def test_version_gate_applies(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    user = create_user(db_session, "a@example.com")
    grant_access(db_session, user, "module-3")
    headers = bearer(client, "a@example.com")
    monkeypatch.setattr(settings, "mobile_min_app_version", "2.0.0")

    assert client.get(URL, headers=headers).status_code == 426
    assert client.get(URL, headers={**headers, "X-App-Version": "2.0.0"}).status_code == 200
