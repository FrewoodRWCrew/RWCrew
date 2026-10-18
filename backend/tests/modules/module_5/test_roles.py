# These tests check Atelier's custom-roles-with-per-screen-permissions
# system — the same system Atelier uses (see
# tests/modules/module_5/test_roles.py), applied to module-5.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.atelier_role import AtelierRole
from app.db.models.atelier_role_permission import AtelierRolePermission
from app.db.models.atelier_screen import AtelierScreen
from app.db.models.atelier_user_role import AtelierUserRole
from app.db.models.module import Module
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_5.screens import SCREEN_DEFINITIONS, sync_screens


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


def _create_atelier_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-5"))
    if module is not None:
        return module
    module = Module(key="module-5", name="Atelier", sort_order=5)
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
) -> AtelierRole:
    role = AtelierRole(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(AtelierScreen).where(AtelierScreen.key == screen_key))
    db_session.add(
        AtelierRolePermission(
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

    screens = db_session.scalars(select(AtelierScreen)).all()
    screen_keys = {screen.key for screen in screens}

    assert screen_keys == {definition.key for definition in SCREEN_DEFINITIONS}


def test_sync_screens_is_safe_to_run_more_than_once(db_session: Session) -> None:
    sync_screens(db_session)
    sync_screens(db_session)

    screens = db_session.scalars(select(AtelierScreen)).all()
    assert len(screens) == len(SCREEN_DEFINITIONS)


# --- basic access + permission enforcement --------------------------------


def test_user_without_module_access_cannot_view_roles(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_atelier_module(db_session)
    _create_user(db_session, email="member@example.com")
    _login(client, "member@example.com")

    response = client.get("/api/modules/module-5/roles")

    assert response.status_code == 403


def test_user_with_access_but_no_role_cannot_view_roles_screen(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "member@example.com")

    response = client.get("/api/modules/module-5/roles")

    assert response.status_code == 403


def test_role_with_view_but_not_edit_cannot_rename_a_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)

    viewer_role = _create_role_with_permissions(
        db_session, name="Viewer", screen_key="atelier.roles", can_view=True
    )
    db_session.add(AtelierUserRole(user_id=user.id, role_id=viewer_role.id))
    db_session.commit()

    _login(client, "member@example.com")

    list_response = client.get("/api/modules/module-5/roles")
    assert list_response.status_code == 200

    rename_response = client.put(f"/api/modules/module-5/roles/{viewer_role.id}", json={"name": "New Name"})
    assert rename_response.status_code == 403


def test_super_admin_bypasses_atelier_permissions_entirely(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-5/roles", json={"name": "Admin"})

    assert response.status_code == 201


# --- role CRUD -------------------------------------------------------------


def test_creating_a_role_with_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _create_role_with_permissions(db_session, name="Admin", screen_key="atelier.roles")
    _login(client, "admin@example.com")

    response = client.post("/api/modules/module-5/roles", json={"name": "Admin"})

    assert response.status_code == 409


def test_deleting_a_role_still_assigned_to_a_user_is_rejected(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="atelier.roles")

    other_user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, other_user, module)
    db_session.add(AtelierUserRole(user_id=other_user.id, role_id=role.id))
    db_session.commit()

    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-5/roles/{role.id}")

    assert response.status_code == 400


def test_set_role_permissions_replaces_the_whole_matrix(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="atelier.roles")
    requests_screen = db_session.scalar(
        select(AtelierScreen).where(AtelierScreen.key == "atelier.kpi")
    )
    roles_screen = db_session.scalar(
        select(AtelierScreen).where(AtelierScreen.key == "atelier.roles")
    )

    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-5/roles/{role.id}/permissions",
        json={
            "permissions": [
                {"screen_id": requests_screen.id, "can_view": True, "can_create": False, "can_edit": False, "can_delete": False},
                {"screen_id": roles_screen.id, "can_view": True, "can_create": True, "can_edit": True, "can_delete": True},
            ]
        },
    )

    assert response.status_code == 200
    permissions_by_key = {p["screen_key"]: p for p in response.json()["permissions"]}
    assert permissions_by_key["atelier.kpi"]["can_view"] is True
    assert permissions_by_key["atelier.kpi"]["can_edit"] is False
    assert permissions_by_key["atelier.roles"]["can_edit"] is True


# --- "Roles" and "Users" are gated independently -----------------------------


def test_permission_on_roles_screen_does_not_grant_access_to_users_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(
        db_session, name="Role Manager", screen_key="atelier.roles", can_view=True
    )
    db_session.add(AtelierUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    _login(client, "member@example.com")

    assert client.get("/api/modules/module-5/roles").status_code == 200
    assert client.get("/api/modules/module-5/users").status_code == 403


def test_permission_on_users_screen_does_not_grant_access_to_roles_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(
        db_session, name="User Manager", screen_key="atelier.users", can_view=True
    )
    db_session.add(AtelierUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    _login(client, "member@example.com")

    assert client.get("/api/modules/module-5/users").status_code == 200
    assert client.get("/api/modules/module-5/roles").status_code == 403


# --- user creation/assignment, and module scoping ---------------------------


def test_cannot_assign_a_role_to_a_user_without_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="atelier.roles")

    user_without_access = _create_user(db_session, email="nobody@example.com")
    _login(client, "admin@example.com")

    response = client.put(f"/api/modules/module-5/users/{user_without_access.id}/role", json={"role_id": role.id})

    assert response.status_code == 400


def test_create_or_grant_user_creates_a_brand_new_account_scoped_to_atelier_only(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    role = _create_role_with_permissions(db_session, name="Admin", screen_key="atelier.roles")
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-5/users",
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

    grants = db_session.scalars(select(UserModuleAccess).where(UserModuleAccess.user_id == new_user.id)).all()
    assert [grant.module_id for grant in grants] == [module.id]


def test_me_permissions_reflects_only_what_the_role_allows(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_atelier_module(db_session)
    user = _create_user(db_session, email="member@example.com")
    _grant_module_access(db_session, user, module)
    role = _create_role_with_permissions(
        db_session, name="Requests Viewer", screen_key="atelier.kpi", can_view=True
    )
    db_session.add(AtelierUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    _login(client, "member@example.com")

    response = client.get("/api/modules/module-5/me/permissions")

    assert response.status_code == 200
    assert response.json()["viewable_screen_keys"] == ["atelier.kpi"]


# --- the real screens use per-screen permissions too ----------------------
