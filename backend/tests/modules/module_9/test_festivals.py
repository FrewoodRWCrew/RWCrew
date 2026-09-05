# These tests check the "Festivals" MasterData screen: gated by normal
# module access + the "masterdata.festival" permission, independently of
# "masterdata.season"/others, with a super-admin bypass, full CRUD, and
# season_id FK validation — mirrors test_scanners.py's shape.

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.models.festival import Festival
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_9.screens import sync_screens


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


def _create_masterdata_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-9"))
    if module is not None:
        return module
    module = Module(key="module-9", name="MasterData", sort_order=9)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _grant_screen_permission(
    db_session: Session,
    user: User,
    screen_key: str,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = MasterDataRole(name=f"{screen_key} Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == screen_key))
    db_session.add(
        MasterDataRolePermission(
            role_id=role.id,
            screen_id=screen.id,
            can_view=can_view,
            can_create=can_create,
            can_edit=can_edit,
            can_delete=can_delete,
        )
    )
    db_session.add(MasterDataUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _grant_festival_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    _grant_screen_permission(
        db_session,
        user,
        "masterdata.festival",
        can_view=can_view,
        can_create=can_create,
        can_edit=can_edit,
        can_delete=can_delete,
    )


def _create_season(db_session: Session, *, name: str = "2026") -> Season:
    season = Season(name=name)
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


def _create_festival(
    db_session: Session,
    *,
    name: str = "Summer Bash",
    start_date: str = "2026-07-01",
    end_date: str = "2026-07-03",
    season_id: int,
) -> Festival:
    row = Festival(
        name=name,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        season_id=season_id,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_user_without_module_access_cannot_list_festivals(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_masterdata_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/festivals")

    assert response.status_code == 403


def test_user_with_access_but_no_festival_permission_cannot_list_festivals(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/festivals")

    assert response.status_code == 403


def test_festival_permission_does_not_grant_access_to_season_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_festival_permission(db_session, user, can_view=True, can_create=True)
    _login(client, "viewer@example.com")

    assert client.get("/api/modules/module-9/festivals").status_code == 200
    assert client.get("/api/modules/module-9/seasons").status_code == 403


def test_super_admin_can_create_a_festival_without_an_explicit_role(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    season = _create_season(db_session)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/festivals",
        json={
            "name": "Summer Bash",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "season_id": season.id,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Summer Bash"
    assert body["start_date"] == "2026-07-01"
    assert body["end_date"] == "2026-07-03"
    assert body["season_id"] == season.id


def test_view_only_festival_permission_cannot_create_a_festival(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_festival_permission(db_session, user, can_view=True)
    season = _create_season(db_session)
    _login(client, "viewer@example.com")

    response = client.post(
        "/api/modules/module-9/festivals",
        json={
            "name": "Summer Bash",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "season_id": season.id,
        },
    )

    assert response.status_code == 403


def test_view_only_festival_permission_cannot_update_or_delete(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_festival_permission(db_session, user, can_view=True)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    _login(client, "viewer@example.com")

    update_response = client.put(
        f"/api/modules/module-9/festivals/{festival.id}",
        json={
            "name": "Renamed",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "season_id": season.id,
        },
    )
    delete_response = client.delete(f"/api/modules/module-9/festivals/{festival.id}")

    assert update_response.status_code == 403
    assert delete_response.status_code == 403


def test_creating_a_festival_with_a_missing_season_id_returns_422(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/festivals",
        json={"name": "Summer Bash", "start_date": "2026-07-01", "end_date": "2026-07-03"},
    )

    assert response.status_code == 422


def test_creating_a_festival_with_an_unknown_season_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/festivals",
        json={"name": "Summer Bash", "start_date": "2026-07-01", "end_date": "2026-07-03", "season_id": 999},
    )

    assert response.status_code == 404


def test_list_festivals_ordered_by_name(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    season = _create_season(db_session)
    _create_festival(db_session, name="ZZZ Fest", season_id=season.id)
    _create_festival(db_session, name="AAA Fest", season_id=season.id)
    _login(client, "admin@example.com")

    response = client.get("/api/modules/module-9/festivals")

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["AAA Fest", "ZZZ Fest"]


def test_super_admin_can_update_a_festival(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-9/festivals/{festival.id}",
        json={
            "name": "Summer Bash Renamed",
            "start_date": "2026-08-01",
            "end_date": "2026-08-03",
            "season_id": season.id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Summer Bash Renamed"
    assert body["start_date"] == "2026-08-01"
    assert body["end_date"] == "2026-08-03"


def test_updating_a_missing_festival_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    season = _create_season(db_session)
    _login(client, "admin@example.com")

    response = client.put(
        "/api/modules/module-9/festivals/999",
        json={
            "name": "Nope",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "season_id": season.id,
        },
    )

    assert response.status_code == 404


def test_updating_a_festival_with_an_unknown_season_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-9/festivals/{festival.id}",
        json={
            "name": "Summer Bash",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "season_id": 999,
        },
    )

    assert response.status_code == 404


def test_super_admin_can_delete_a_festival(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-9/festivals/{festival.id}")

    assert response.status_code == 204
    assert client.get("/api/modules/module-9/festivals").json() == []


def test_deleting_a_missing_festival_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.delete("/api/modules/module-9/festivals/999")

    assert response.status_code == 404
