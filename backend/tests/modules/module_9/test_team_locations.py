# These tests check the "Team Location" screen (nested under "Teams"):
# gated by normal module access + the "masterdata.team-location"
# permission, independently of "masterdata.roles"/"masterdata.users",
# with a super-admin bypass — mirrors test_season.py's shape.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.team_location import TeamLocation
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


def _grant_team_location_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = MasterDataRole(name=f"Team Location Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == "masterdata.team-location"))
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


def _create_team_location(db_session: Session, *, location: str = "Antwerp") -> TeamLocation:
    team_location = TeamLocation(location=location)
    db_session.add(team_location)
    db_session.commit()
    db_session.refresh(team_location)
    return team_location


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_user_without_module_access_cannot_list_team_locations(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_masterdata_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/team-locations")

    assert response.status_code == 403


def test_user_with_access_but_no_team_location_permission_cannot_list_team_locations(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/team-locations")

    assert response.status_code == 403


def test_user_with_team_location_view_permission_can_list_team_locations(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_team_location_permission(db_session, user, can_view=True)
    _create_team_location(db_session, location="Ghent")
    _create_team_location(db_session, location="Antwerp")
    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-9/team-locations")

    assert response.status_code == 200
    assert [row["location"] for row in response.json()] == ["Antwerp", "Ghent"]


def test_super_admin_can_manage_team_locations_without_an_explicit_role(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/team-locations", json={"location": "Antwerp"})

    assert response.status_code == 201
    assert response.json()["location"] == "Antwerp"


def test_team_location_permission_does_not_grant_access_to_roles_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_team_location_permission(db_session, user, can_view=True, can_create=True)
    _login(client, "viewer@example.com")

    assert client.get("/api/modules/module-9/team-locations").status_code == 200
    assert client.get("/api/modules/module-9/roles").status_code == 403


def test_view_only_team_location_permission_cannot_create_a_team_location(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_team_location_permission(db_session, user, can_view=True)
    _login(client, "viewer@example.com")

    response = client.post("/api/modules/module-9/team-locations", json={"location": "Antwerp"})

    assert response.status_code == 403


def test_creating_a_team_location_with_a_duplicate_name_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _create_team_location(db_session, location="Antwerp")
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/team-locations", json={"location": "Antwerp"})

    assert response.status_code == 409


def test_super_admin_can_rename_a_team_location(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    team_location = _create_team_location(db_session, location="Antwerp")
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-9/team-locations/{team_location.id}", json={"location": "Antwerp Warehouse"}
    )

    assert response.status_code == 200
    assert response.json()["location"] == "Antwerp Warehouse"


def test_renaming_a_missing_team_location_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.put("/api/modules/module-9/team-locations/999", json={"location": "Antwerp"})

    assert response.status_code == 404


def test_super_admin_can_delete_a_team_location(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    team_location = _create_team_location(db_session, location="Antwerp")
    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-9/team-locations/{team_location.id}")

    assert response.status_code == 204
    assert client.get("/api/modules/module-9/team-locations").json() == []


def test_deleting_a_missing_team_location_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.delete("/api/modules/module-9/team-locations/999")

    assert response.status_code == 404
