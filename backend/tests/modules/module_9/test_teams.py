# These tests check the "Teams" screen: gated by normal module access +
# the "masterdata.teams" permission, independently of
# "masterdata.roles"/"masterdata.users", with a super-admin bypass —
# mirrors test_season.py's/test_team_locations.py's shape, plus extra
# coverage for Teams' FK/many-to-many fields (location, delivery method,
# tasks, kernleden).

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.delivery_method import DeliveryMethod
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.team import Team
from app.db.models.team_kernlid import TeamKernlid
from app.db.models.team_location import TeamLocation
from app.db.models.team_task import TeamTask
from app.db.models.team_team_task import TeamTeamTask
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


def _grant_teams_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = MasterDataRole(name=f"Teams Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == "masterdata.teams"))
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


def _create_team(db_session: Session, *, name: str = "Bar Team") -> Team:
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_team_location(db_session: Session, *, location: str = "Inside") -> TeamLocation:
    team_location = TeamLocation(location=location)
    db_session.add(team_location)
    db_session.commit()
    db_session.refresh(team_location)
    return team_location


def _create_delivery_method(db_session: Session, *, delivery_method: str = "Truck") -> DeliveryMethod:
    method = DeliveryMethod(delivery_method=delivery_method)
    db_session.add(method)
    db_session.commit()
    db_session.refresh(method)
    return method


def _create_team_task(db_session: Session, *, team_tasks: str = "Inkom") -> TeamTask:
    task = TeamTask(team_tasks=team_tasks)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def _create_kernlid(db_session: Session, *, first_name: str = "Jane", name: str = "Doe", flagged: bool = True) -> User:
    """A user flagged "Altsien Kernlid" (what Teams' Kernleden picker now uses)."""
    kernlid = User(
        email=f"{first_name}.{name}@example.com".lower(),
        hashed_password=hash_password("password123"),
        display_name=f"{first_name} {name}",
        is_altsien_kernlid=flagged,
    )
    db_session.add(kernlid)
    db_session.commit()
    db_session.refresh(kernlid)
    return kernlid


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_user_without_module_access_cannot_list_teams(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_masterdata_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/teams")

    assert response.status_code == 403


def test_user_with_access_but_no_teams_permission_cannot_list_teams(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/teams")

    assert response.status_code == 403


def test_user_with_teams_view_permission_can_list_teams(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_teams_permission(db_session, user, can_view=True)
    _create_team(db_session, name="Bravo")
    _create_team(db_session, name="Alfa")
    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-9/teams")

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Alfa", "Bravo"]


def test_super_admin_can_manage_teams_without_an_explicit_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team"})

    assert response.status_code == 201
    assert response.json()["name"] == "Bar Team"
    assert response.json()["task_ids"] == []
    assert response.json()["kernlid_ids"] == []


def test_teams_permission_does_not_grant_access_to_roles_screen(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_teams_permission(db_session, user, can_view=True, can_create=True)
    _login(client, "viewer@example.com")

    assert client.get("/api/modules/module-9/teams").status_code == 200
    assert client.get("/api/modules/module-9/roles").status_code == 403


def test_view_only_teams_permission_cannot_create_a_team(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_teams_permission(db_session, user, can_view=True)
    _login(client, "viewer@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team"})

    assert response.status_code == 403


def test_creating_a_team_with_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _create_team(db_session, name="Bar Team")
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team"})

    assert response.status_code == 409


def test_super_admin_can_rename_a_team(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    team = _create_team(db_session, name="Bar Team")
    _login(client, "admin@example.com")

    response = client.put(f"/api/modules/module-9/teams/{team.id}", json={"name": "Renamed Team"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Team"


def test_team_is_active_by_default_and_active_can_be_set_on_create_and_update(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    # Omitting "active" on create means the team is active.
    default_response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team"})
    assert default_response.status_code == 201
    assert default_response.json()["active"] is True

    # An explicit false is stored...
    inactive_response = client.post("/api/modules/module-9/teams", json={"name": "Old Team", "active": False})
    assert inactive_response.status_code == 201
    assert inactive_response.json()["active"] is False
    team_id = inactive_response.json()["id"]

    # ...shows up in the list, and can be flipped back on update.
    listed = {row["name"]: row["active"] for row in client.get("/api/modules/module-9/teams").json()}
    assert listed == {"Bar Team": True, "Old Team": False}

    update_response = client.put(f"/api/modules/module-9/teams/{team_id}", json={"name": "Old Team", "active": True})
    assert update_response.status_code == 200
    assert update_response.json()["active"] is True


def test_renaming_a_missing_team_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.put("/api/modules/module-9/teams/999", json={"name": "Bar Team"})

    assert response.status_code == 404


def test_super_admin_can_delete_a_team(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    team = _create_team(db_session, name="Bar Team")
    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-9/teams/{team.id}")

    assert response.status_code == 204
    assert client.get("/api/modules/module-9/teams").json() == []


def test_deleting_a_missing_team_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.delete("/api/modules/module-9/teams/999")

    assert response.status_code == 404


def test_creating_a_team_with_valid_location_delivery_method_tasks_and_kernleden(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    location = _create_team_location(db_session)
    delivery_method = _create_delivery_method(db_session)
    task_a = _create_team_task(db_session, team_tasks="Inkom")
    task_b = _create_team_task(db_session, team_tasks="Uitkom")
    kernlid_a = _create_kernlid(db_session, first_name="Jane", name="Doe")
    kernlid_b = _create_kernlid(db_session, first_name="John", name="Doe")
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/teams",
        json={
            "name": "Bar Team",
            "location_id": location.id,
            "delivery_method_id": delivery_method.id,
            "task_ids": [task_a.id, task_b.id],
            "kernlid_ids": [kernlid_a.id, kernlid_b.id],
            "description": "A team.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["location_id"] == location.id
    assert body["delivery_method_id"] == delivery_method.id
    assert sorted(body["task_ids"]) == sorted([task_a.id, task_b.id])
    assert sorted(body["kernlid_ids"]) == sorted([kernlid_a.id, kernlid_b.id])
    assert body["description"] == "A team."


def test_creating_a_team_with_an_unknown_location_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team", "location_id": 999})

    assert response.status_code == 404


def test_creating_a_team_with_an_unknown_delivery_method_id_returns_404(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team", "delivery_method_id": 999})

    assert response.status_code == 404


def test_creating_a_team_with_an_unknown_task_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team", "task_ids": [999]})

    assert response.status_code == 404


def test_creating_a_team_with_an_unknown_kernlid_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team", "kernlid_ids": [999]})

    assert response.status_code == 404


def test_updating_a_team_with_an_unknown_task_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    team = _create_team(db_session, name="Bar Team")
    _login(client, "admin@example.com")

    response = client.put(f"/api/modules/module-9/teams/{team.id}", json={"name": "Bar Team", "task_ids": [999]})

    assert response.status_code == 404


def test_updating_a_team_replaces_its_task_links_rather_than_appending(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    task_a = _create_team_task(db_session, team_tasks="Inkom")
    task_b = _create_team_task(db_session, team_tasks="Uitkom")
    task_c = _create_team_task(db_session, team_tasks="Opbouw")
    _login(client, "admin@example.com")

    create_response = client.post(
        "/api/modules/module-9/teams",
        json={"name": "Bar Team", "task_ids": [task_a.id, task_b.id]},
    )
    team_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/modules/module-9/teams/{team_id}",
        json={"name": "Bar Team", "task_ids": [task_c.id]},
    )

    assert update_response.status_code == 200
    assert update_response.json()["task_ids"] == [task_c.id]
    remaining_links = db_session.scalars(select(TeamTeamTask).where(TeamTeamTask.team_id == team_id)).all()
    assert [link.team_task_id for link in remaining_links] == [task_c.id]


def test_creating_a_team_with_a_user_who_is_not_flagged_altsien_kernlid_returns_404(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    unflagged = _create_kernlid(db_session, first_name="Not", name="Flagged", flagged=False)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-9/teams", json={"name": "Bar Team", "kernlid_ids": [unflagged.id]})

    assert response.status_code == 404


def test_updating_a_team_replaces_its_kernlid_links_rather_than_appending(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    kernlid_a = _create_kernlid(db_session, first_name="Jane", name="Doe")
    kernlid_b = _create_kernlid(db_session, first_name="John", name="Doe")
    kernlid_c = _create_kernlid(db_session, first_name="Jack", name="Doe")
    _login(client, "admin@example.com")

    create_response = client.post(
        "/api/modules/module-9/teams",
        json={"name": "Bar Team", "kernlid_ids": [kernlid_a.id, kernlid_b.id]},
    )
    team_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/modules/module-9/teams/{team_id}",
        json={"name": "Bar Team", "kernlid_ids": [kernlid_c.id]},
    )

    assert update_response.status_code == 200
    assert update_response.json()["kernlid_ids"] == [kernlid_c.id]
    remaining_links = db_session.scalars(select(TeamKernlid).where(TeamKernlid.team_id == team_id)).all()
    assert [link.altsien_kernlid_id for link in remaining_links] == [kernlid_c.id]


def test_deleting_a_team_cascades_its_join_table_rows(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    task = _create_team_task(db_session)
    kernlid = _create_kernlid(db_session)
    _login(client, "admin@example.com")

    create_response = client.post(
        "/api/modules/module-9/teams",
        json={"name": "Bar Team", "task_ids": [task.id], "kernlid_ids": [kernlid.id]},
    )
    team_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/modules/module-9/teams/{team_id}")

    assert delete_response.status_code == 204
    assert db_session.scalars(select(TeamTeamTask).where(TeamTeamTask.team_id == team_id)).all() == []
    assert db_session.scalars(select(TeamKernlid).where(TeamKernlid.team_id == team_id)).all() == []
