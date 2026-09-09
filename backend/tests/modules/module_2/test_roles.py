# These tests check KarTracker's custom-roles-with-per-screen-permissions
# system: screens sync automatically, roles are fully custom (not a fixed
# enum), permissions are checked per screen per action, and a KarTracker
# admin can create/grant users scoped to KarTracker only — never any other
# module. This is the module's first development phase, so only the
# "kartracker.roles"/"kartracker.users" screens exist yet.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_role_permission import KarTrackerRolePermission
from app.db.models.kartracker_screen import KarTrackerScreen
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_2.screens import SCREEN_DEFINITIONS, sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)


# --- screen registry sync -------------------------------------------------


def test_sync_screens_creates_every_defined_screen(db_session: Session) -> None:
    sync_screens(db_session)

    screens = db_session.scalars(select(KarTrackerScreen)).all()
    screen_keys = {screen.key for screen in screens}

    assert screen_keys == {definition.key for definition in SCREEN_DEFINITIONS}


def test_sync_screens_is_safe_to_run_more_than_once(db_session: Session) -> None:
    sync_screens(db_session)
    sync_screens(db_session)

    screens = db_session.scalars(select(KarTrackerScreen)).all()
    # Running it twice must not create duplicate rows.
    assert len(screens) == len(SCREEN_DEFINITIONS)


def test_sync_screens_updates_the_label_of_an_existing_screen(db_session: Session) -> None:
    sync_screens(db_session)

    screen = db_session.scalar(select(KarTrackerScreen).where(KarTrackerScreen.key == "kartracker.roles"))
    screen.label = "Some Old Label"
    db_session.commit()

    sync_screens(db_session)

    db_session.refresh(screen)
    assert screen.label == "Roles"


# --- basic access + permission enforcement --------------------------------


def test_user_without_module_access_cannot_view_roles(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    create_kartracker_module(db_session)
    create_user(db_session, email="member@example.com")
    login(client, "member@example.com")

    response = client.get("/api/modules/module-2/roles")

    assert response.status_code == 403


def test_user_with_access_but_no_role_cannot_view_roles_screen(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    login(client, "member@example.com")

    response = client.get("/api/modules/module-2/roles")

    assert response.status_code == 403


def test_role_with_view_but_not_edit_cannot_rename_a_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)

    viewer_role = create_role_with_permissions(
        db_session, name="Viewer", screen_key="kartracker.roles", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=viewer_role.id))
    db_session.commit()

    login(client, "member@example.com")

    # Viewing the roles list should work...
    list_response = client.get("/api/modules/module-2/roles")
    assert list_response.status_code == 200

    # ...but renaming (an "edit" action) should not.
    rename_response = client.put(f"/api/modules/module-2/roles/{viewer_role.id}", json={"name": "New Name"})
    assert rename_response.status_code == 403


def test_super_admin_bypasses_kartracker_permissions_entirely(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")

    # No KarTracker role assigned at all, yet every action succeeds.
    response = client.post("/api/modules/module-2/roles", json={"name": "Admin"})

    assert response.status_code == 201


# --- role CRUD -------------------------------------------------------------


def test_creating_a_role_with_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    create_role_with_permissions(db_session, name="Admin", screen_key="kartracker.roles")
    login(client, "admin@example.com")

    response = client.post("/api/modules/module-2/roles", json={"name": "Admin"})

    assert response.status_code == 409


def test_deleting_a_role_still_assigned_to_a_user_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    role = create_role_with_permissions(db_session, name="Admin", screen_key="kartracker.roles")

    other_user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, other_user, module)
    db_session.add(KarTrackerUserRole(user_id=other_user.id, role_id=role.id))
    db_session.commit()

    login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-2/roles/{role.id}")

    assert response.status_code == 400


def test_set_role_permissions_replaces_the_whole_matrix(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    role = create_role_with_permissions(db_session, name="Admin", screen_key="kartracker.roles")
    users_screen = db_session.scalar(select(KarTrackerScreen).where(KarTrackerScreen.key == "kartracker.users"))
    roles_screen = db_session.scalar(select(KarTrackerScreen).where(KarTrackerScreen.key == "kartracker.roles"))

    login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-2/roles/{role.id}/permissions",
        json={
            "permissions": [
                {"screen_id": users_screen.id, "can_view": True, "can_create": False, "can_edit": False, "can_delete": False},
                {"screen_id": roles_screen.id, "can_view": True, "can_create": True, "can_edit": True, "can_delete": True},
            ]
        },
    )

    assert response.status_code == 200
    permissions_by_key = {p["screen_key"]: p for p in response.json()["permissions"]}
    assert permissions_by_key["kartracker.users"]["can_view"] is True
    assert permissions_by_key["kartracker.users"]["can_edit"] is False
    assert permissions_by_key["kartracker.roles"]["can_edit"] is True


def test_set_role_permissions_removes_permissions_for_an_omitted_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    # Give the role full permissions on "users" up front...
    role = create_role_with_permissions(
        db_session, name="Admin", screen_key="kartracker.users", can_view=True, can_edit=True
    )
    users_screen = db_session.scalar(select(KarTrackerScreen).where(KarTrackerScreen.key == "kartracker.users"))
    roles_screen = db_session.scalar(select(KarTrackerScreen).where(KarTrackerScreen.key == "kartracker.roles"))

    login(client, "admin@example.com")

    # ...then send a matrix that only mentions "roles" — "users" is omitted
    # entirely, which should clear its permissions rather than leave them.
    response = client.put(
        f"/api/modules/module-2/roles/{role.id}/permissions",
        json={
            "permissions": [
                {"screen_id": roles_screen.id, "can_view": True, "can_create": False, "can_edit": False, "can_delete": False},
            ]
        },
    )

    assert response.status_code == 200
    permissions_by_key = {p["screen_key"]: p for p in response.json()["permissions"]}
    assert permissions_by_key["kartracker.users"]["can_view"] is False
    assert permissions_by_key["kartracker.users"]["can_edit"] is False

    # Prove this is an actual delete, not merely a response that happens to
    # default missing permissions to False — the "users" row must be gone.
    remaining = db_session.scalar(
        select(KarTrackerRolePermission).where(
            KarTrackerRolePermission.role_id == role.id, KarTrackerRolePermission.screen_id == users_screen.id
        )
    )
    assert remaining is None


def test_set_role_permissions_with_unknown_screen_id_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    role = create_role_with_permissions(db_session, name="Admin", screen_key="kartracker.roles")

    login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-2/roles/{role.id}/permissions",
        json={
            "permissions": [
                {"screen_id": 999999, "can_view": True, "can_create": False, "can_edit": False, "can_delete": False},
            ]
        },
    )

    assert response.status_code == 404


# --- "Roles" and "Users" are gated independently -----------------------------


def test_permission_on_roles_screen_does_not_grant_access_to_users_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Role Manager", screen_key="kartracker.roles", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    login(client, "member@example.com")

    # Can view the Roles screen...
    roles_response = client.get("/api/modules/module-2/roles")
    assert roles_response.status_code == 200

    # ...but has no permission on the separate Users screen.
    users_response = client.get("/api/modules/module-2/users")
    assert users_response.status_code == 403


def test_permission_on_users_screen_does_not_grant_access_to_roles_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="User Manager", screen_key="kartracker.users", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    login(client, "member@example.com")

    # Can view the Users screen...
    users_response = client.get("/api/modules/module-2/users")
    assert users_response.status_code == 200

    # ...but has no permission on the separate Roles screen.
    roles_response = client.get("/api/modules/module-2/roles")
    assert roles_response.status_code == 403


# --- user creation/assignment, and module scoping ---------------------------


def test_cannot_assign_a_role_to_a_user_without_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    role = create_role_with_permissions(db_session, name="Admin", screen_key="kartracker.roles")

    user_without_access = create_user(db_session, email="nobody@example.com")
    login(client, "admin@example.com")

    response = client.put(f"/api/modules/module-2/users/{user_without_access.id}/role", json={"role_id": role.id})

    assert response.status_code == 400


def test_create_or_grant_user_creates_a_brand_new_account_scoped_to_kartracker_only(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    role = create_role_with_permissions(db_session, name="Admin", screen_key="kartracker.roles")
    login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-2/users",
        json={
            "email": "newperson@example.com",
            "display_name": "New Person",
            "password": "TestPass123!",
            "role_id": role.id,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role_name"] == "Admin"

    new_user = db_session.scalar(select(User).where(User.email == "newperson@example.com"))
    assert new_user is not None

    # The whole point of this endpoint: access is granted for KarTracker
    # (module-2) only, never anything else.
    grants = db_session.scalars(select(UserModuleAccess).where(UserModuleAccess.user_id == new_user.id)).all()
    assert [grant.module_id for grant in grants] == [module.id]


def test_create_or_grant_user_without_password_for_a_new_email_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")

    response = client.post("/api/modules/module-2/users", json={"email": "nopassword@example.com"})

    assert response.status_code == 400


def test_create_or_grant_user_with_an_existing_email_just_grants_access(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    existing_user = create_user(db_session, email="already-here@example.com")
    login(client, "admin@example.com")

    response = client.post("/api/modules/module-2/users", json={"email": "already-here@example.com"})

    assert response.status_code == 201
    assert response.json()["user_id"] == existing_user.id

    grants = db_session.scalars(select(UserModuleAccess).where(UserModuleAccess.user_id == existing_user.id)).all()
    assert len(grants) == 1


def test_me_permissions_reflects_only_what_the_role_allows(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Users Viewer", screen_key="kartracker.users", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    login(client, "member@example.com")

    response = client.get("/api/modules/module-2/me/permissions")

    assert response.status_code == 200
    assert response.json()["viewable_screen_keys"] == ["kartracker.users"]
