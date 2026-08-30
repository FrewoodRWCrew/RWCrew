# These tests check Tagscan's custom-roles-with-per-screen-permissions
# system: screens sync automatically, roles are fully custom (not a fixed
# enum), permissions are checked per screen per action, and a Tagscan
# admin can create/grant users scoped to Tagscan only — never any other
# module.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.tagscan_role import TagscanRole
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_1.screens import SCREEN_DEFINITIONS, sync_screens


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


def _create_tagscan_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-1"))
    if module is not None:
        return module
    module = Module(key="module-1", name="Tagscan", sort_order=1)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _create_role_with_permissions(
    db_session: Session,
    *,
    name: str,
    screen_key: str,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> TagscanRole:
    role = TagscanRole(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == screen_key))
    db_session.add(
        TagscanRolePermission(
            role_id=role.id,
            screen_id=screen.id,
            can_view=can_view,
            can_create=can_create,
            can_edit=can_edit,
            can_delete=can_delete,
        )
    )
    db_session.commit()
    return role


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


# --- screen registry sync -------------------------------------------------


def test_sync_screens_creates_every_defined_screen(db_session: Session) -> None:
    sync_screens(db_session)

    screens = db_session.scalars(select(TagscanScreen)).all()
    screen_keys = {screen.key for screen in screens}

    assert screen_keys == {definition.key for definition in SCREEN_DEFINITIONS}


def test_sync_screens_is_safe_to_run_more_than_once(db_session: Session) -> None:
    sync_screens(db_session)
    sync_screens(db_session)

    screens = db_session.scalars(select(TagscanScreen)).all()
    # Running it twice must not create duplicate rows.
    assert len(screens) == len(SCREEN_DEFINITIONS)


def test_sync_screens_updates_the_label_of_an_existing_screen(db_session: Session) -> None:
    sync_screens(db_session)

    screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == "tagscan.dashboard"))
    screen.label = "Some Old Label"
    db_session.commit()

    sync_screens(db_session)

    db_session.refresh(screen)
    assert screen.label == "Dashboard"


# --- basic access + permission enforcement --------------------------------


def test_user_without_module_access_cannot_view_dashboard(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_tagscan_module(db_session)
    _create_user(db_session, email="member@example.com")
    _login(client, "member@example.com")

    response = client.get("/api/modules/module-1/files/tree")

    assert response.status_code == 403


def test_user_with_access_but_no_role_cannot_view_roles_screen(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "member@example.com")

    response = client.get("/api/modules/module-1/roles")

    assert response.status_code == 403


def test_role_with_view_but_not_edit_cannot_rename_a_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)

    viewer_role = _create_role_with_permissions(db_session, name="Viewer", screen_key="tagscan.roles", can_view=True)
    db_session.add(TagscanUserRole(user_id=user.id, role_id=viewer_role.id))
    db_session.commit()

    _login(client, "member@example.com")

    # Viewing the roles list should work...
    list_response = client.get("/api/modules/module-1/roles")
    assert list_response.status_code == 200

    # ...but renaming (an "edit" action) should not.
    rename_response = client.put(f"/api/modules/module-1/roles/{viewer_role.id}", json={"name": "New Name"})
    assert rename_response.status_code == 403


def test_super_admin_bypasses_tagscan_permissions_entirely(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    # No Tagscan role assigned at all, yet every action succeeds.
    response = client.post("/api/modules/module-1/roles", json={"name": "Admin"})

    assert response.status_code == 201


# --- role CRUD -------------------------------------------------------------


def test_creating_a_role_with_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _create_role_with_permissions(db_session, name="Admin", screen_key="tagscan.roles")
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-1/roles", json={"name": "Admin"})

    assert response.status_code == 409


def test_deleting_a_role_still_assigned_to_a_user_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="tagscan.roles")

    other_user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, other_user, module)
    db_session.add(TagscanUserRole(user_id=other_user.id, role_id=role.id))
    db_session.commit()

    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-1/roles/{role.id}")

    assert response.status_code == 400


def test_set_role_permissions_replaces_the_whole_matrix(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="tagscan.roles")
    dashboard_screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == "tagscan.dashboard"))
    roles_screen = db_session.scalar(select(TagscanScreen).where(TagscanScreen.key == "tagscan.roles"))

    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-1/roles/{role.id}/permissions",
        json={
            "permissions": [
                {"screen_id": dashboard_screen.id, "can_view": True, "can_create": False, "can_edit": False, "can_delete": False},
                {"screen_id": roles_screen.id, "can_view": True, "can_create": True, "can_edit": True, "can_delete": True},
            ]
        },
    )

    assert response.status_code == 200
    permissions_by_key = {p["screen_key"]: p for p in response.json()["permissions"]}
    assert permissions_by_key["tagscan.dashboard"]["can_view"] is True
    assert permissions_by_key["tagscan.dashboard"]["can_edit"] is False
    assert permissions_by_key["tagscan.roles"]["can_edit"] is True


# --- "Roles" and "Users" are gated independently -----------------------------


def test_permission_on_roles_screen_does_not_grant_access_to_users_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(db_session, name="Role Manager", screen_key="tagscan.roles", can_view=True)
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    _login(client, "member@example.com")

    # Can view the Roles screen...
    roles_response = client.get("/api/modules/module-1/roles")
    assert roles_response.status_code == 200

    # ...but has no permission on the separate Users screen.
    users_response = client.get("/api/modules/module-1/users")
    assert users_response.status_code == 403


def test_permission_on_users_screen_does_not_grant_access_to_roles_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(db_session, name="User Manager", screen_key="tagscan.users", can_view=True)
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    _login(client, "member@example.com")

    # Can view the Users screen...
    users_response = client.get("/api/modules/module-1/users")
    assert users_response.status_code == 200

    # ...but has no permission on the separate Roles screen.
    roles_response = client.get("/api/modules/module-1/roles")
    assert roles_response.status_code == 403


# --- user creation/assignment, and module scoping ---------------------------


def test_cannot_assign_a_role_to_a_user_without_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="tagscan.roles")

    user_without_access = _create_user(db_session, email="nobody@example.com")
    _login(client, "admin@example.com")

    response = client.put(f"/api/modules/module-1/users/{user_without_access.id}/role", json={"role_id": role.id})

    assert response.status_code == 400


def test_create_or_grant_user_creates_a_brand_new_account_scoped_to_tagscan_only(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="tagscan.roles")
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-1/users",
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

    # The whole point of this endpoint: access is granted for Tagscan
    # (module-1) only, never anything else.
    grants = db_session.scalars(select(UserModuleAccess).where(UserModuleAccess.user_id == new_user.id)).all()
    assert [grant.module_id for grant in grants] == [module.id]


def test_create_or_grant_user_without_password_for_a_new_email_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-1/users", json={"email": "nopassword@example.com"})

    assert response.status_code == 400


def test_create_or_grant_user_with_an_existing_email_just_grants_access(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    existing_user = _create_user(db_session, email="already-here@example.com")
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-1/users", json={"email": "already-here@example.com"})

    assert response.status_code == 201
    assert response.json()["user_id"] == existing_user.id

    grants = db_session.scalars(select(UserModuleAccess).where(UserModuleAccess.user_id == existing_user.id)).all()
    assert len(grants) == 1


def test_me_permissions_reflects_only_what_the_role_allows(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_tagscan_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(db_session, name="Dashboard Viewer", screen_key="tagscan.dashboard", can_view=True)
    db_session.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    _login(client, "member@example.com")

    response = client.get("/api/modules/module-1/me/permissions")

    assert response.status_code == 200
    assert response.json()["viewable_screen_keys"] == ["tagscan.dashboard"]
