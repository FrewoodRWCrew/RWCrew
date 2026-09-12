# These tests check the login history feature: every login attempt
# (successful or not) is recorded in Landing_login_history, and the
# super-admin-only "Login History" endpoint lists, paginates, and
# date-filters those rows correctly.

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.login_history import LoginHistory
from app.db.models.user import User


def _create_user(db_session: Session, *, email: str, password: str = "password123", is_super_admin: bool = False) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=email,
        is_super_admin=is_super_admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client: TestClient, email: str, password: str = "password123") -> None:
    client.post("/api/auth/login", json={"email": email, "password": password})


def test_successful_login_is_recorded(client: TestClient, db_session: Session) -> None:
    user = _create_user(db_session, email="user@example.com")

    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
    assert response.status_code == 200

    rows = db_session.scalars(select(LoginHistory)).all()
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].user_id == user.id
    assert rows[0].email_attempted == "user@example.com"


def test_wrong_password_is_recorded_with_the_matched_user(client: TestClient, db_session: Session) -> None:
    user = _create_user(db_session, email="user@example.com")

    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert response.status_code == 401

    rows = db_session.scalars(select(LoginHistory)).all()
    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].user_id == user.id


def test_unknown_email_is_recorded_with_no_user(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "anything"})
    assert response.status_code == 401

    rows = db_session.scalars(select(LoginHistory)).all()
    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].user_id is None
    assert rows[0].email_attempted == "nobody@example.com"


def test_non_super_admin_cannot_list_login_history(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/admin/login-history")

    assert response.status_code == 403


def test_super_admin_sees_login_history_newest_first(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    other_user = _create_user(db_session, email="member@example.com")

    now = datetime.now(timezone.utc)
    db_session.add(LoginHistory(user_id=other_user.id, email_attempted="member@example.com", success=True, created_at=now - timedelta(minutes=5)))
    db_session.add(LoginHistory(user_id=other_user.id, email_attempted="member@example.com", success=False, created_at=now - timedelta(minutes=1)))
    db_session.commit()

    _login(client, "admin@example.com")
    response = client.get("/api/admin/login-history")

    assert response.status_code == 200
    body = response.json()
    # Two seeded rows plus this admin's own successful login, which
    # happened last (just now) so it sorts first.
    assert body["total"] == 3
    assert body["items"][0]["display_name"] == "admin@example.com"
    assert body["items"][1]["success"] is False
    assert body["items"][1]["display_name"] == "member@example.com"


def test_login_history_supports_pagination(client: TestClient, db_session: Session) -> None:
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)

    now = datetime.now(timezone.utc)
    for i in range(5):
        db_session.add(
            LoginHistory(user_id=admin.id, email_attempted="admin@example.com", success=True, created_at=now - timedelta(minutes=i))
        )
    db_session.commit()

    _login(client, "admin@example.com")
    response = client.get("/api/admin/login-history", params={"page": 2, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 6  # 5 seeded + this admin's own login just now
    assert len(body["items"]) == 2


def test_login_history_supports_date_range_filtering(client: TestClient, db_session: Session) -> None:
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)

    old_moment = datetime.now(timezone.utc) - timedelta(days=10)
    db_session.add(LoginHistory(user_id=admin.id, email_attempted="admin@example.com", success=True, created_at=old_moment))
    db_session.commit()

    _login(client, "admin@example.com")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = client.get("/api/admin/login-history", params={"date_from": cutoff})

    assert response.status_code == 200
    body = response.json()
    # Only this admin's own just-now login should be in range; the
    # 10-day-old seeded row should be filtered out.
    assert body["total"] == 1
