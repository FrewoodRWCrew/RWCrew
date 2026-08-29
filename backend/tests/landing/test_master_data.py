# These tests check the "Season" master-data endpoints: only the super
# admin can manage them, names must stay unique, and create/update/delete
# all behave correctly.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.season import Season
from app.db.models.user import User


def _create_user(db_session: Session, *, email: str, is_super_admin: bool = False) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        display_name=email,
        is_super_admin=is_super_admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_season(db_session: Session, *, name: str = "2026") -> Season:
    season = Season(name=name)
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_non_super_admin_cannot_list_seasons(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/admin/master-data/seasons")

    assert response.status_code == 403


def test_super_admin_can_list_seasons(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _create_season(db_session, name="2027")
    _create_season(db_session, name="2026")
    _login(client, "admin@example.com")

    response = client.get("/api/admin/master-data/seasons")

    assert response.status_code == 200
    # Ordered by name, so "2026" comes before "2027".
    assert [season["name"] for season in response.json()] == ["2026", "2027"]


def test_super_admin_can_create_a_season(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _login(client, "admin@example.com")

    response = client.post("/api/admin/master-data/seasons", json={"name": "2026"})

    assert response.status_code == 201
    assert response.json()["name"] == "2026"


def test_non_super_admin_cannot_create_a_season(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.post("/api/admin/master-data/seasons", json={"name": "2026"})

    assert response.status_code == 403


def test_creating_a_season_with_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _create_season(db_session, name="2026")
    _login(client, "admin@example.com")

    response = client.post("/api/admin/master-data/seasons", json={"name": "2026"})

    assert response.status_code == 409


def test_super_admin_can_rename_a_season(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    season = _create_season(db_session, name="2026")
    _login(client, "admin@example.com")

    response = client.put(f"/api/admin/master-data/seasons/{season.id}", json={"name": "2026-2027"})

    assert response.status_code == 200
    assert response.json()["name"] == "2026-2027"


def test_renaming_a_season_to_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _create_season(db_session, name="2026")
    season_to_rename = _create_season(db_session, name="2027")
    _login(client, "admin@example.com")

    response = client.put(f"/api/admin/master-data/seasons/{season_to_rename.id}", json={"name": "2026"})

    assert response.status_code == 409


def test_renaming_a_missing_season_returns_404(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _login(client, "admin@example.com")

    response = client.put("/api/admin/master-data/seasons/999", json={"name": "2026"})

    assert response.status_code == 404


def test_super_admin_can_delete_a_season(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    season = _create_season(db_session, name="2026")
    _login(client, "admin@example.com")

    response = client.delete(f"/api/admin/master-data/seasons/{season.id}")

    assert response.status_code == 204
    assert client.get("/api/admin/master-data/seasons").json() == []


def test_deleting_a_missing_season_returns_404(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _login(client, "admin@example.com")

    response = client.delete("/api/admin/master-data/seasons/999")

    assert response.status_code == 404


def test_non_super_admin_cannot_delete_a_season(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="regular@example.com")
    season = _create_season(db_session, name="2026")
    _login(client, "regular@example.com")

    response = client.delete(f"/api/admin/master-data/seasons/{season.id}")

    assert response.status_code == 403
