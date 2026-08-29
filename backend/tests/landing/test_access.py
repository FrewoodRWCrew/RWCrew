# These tests check the access-rights system end-to-end:
#   - Only the super admin can grant/revoke which modules a user can open.
#   - A user without access to a module is refused when they try to use it.
#   - A module's own admin (not the super admin) can manage roles within
#     that one module, but nowhere else.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.module_role import ModuleRole, ModuleRoleName
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess


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


def _create_module(db_session: Session, *, key: str = "module-1", sort_order: int = 1) -> Module:
    module = Module(key=key, name=key, sort_order=sort_order)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_non_super_admin_cannot_list_users(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/admin/users")

    assert response.status_code == 403


def test_super_admin_can_grant_module_access(client: TestClient, db_session: Session) -> None:
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    target_user = _create_user(db_session, email="member@example.com")
    _create_module(db_session, key="module-1")
    _login(client, "admin@example.com")

    response = client.put(f"/api/admin/users/{target_user.id}/access", json={"module_keys": ["module-1"]})

    assert response.status_code == 200
    assert response.json()["accessible_module_keys"] == ["module-1"]


def test_super_admin_can_revoke_previously_granted_access(client: TestClient, db_session: Session) -> None:
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    target_user = _create_user(db_session, email="member@example.com")
    _create_module(db_session, key="module-1")
    _login(client, "admin@example.com")

    # First grant access...
    client.put(f"/api/admin/users/{target_user.id}/access", json={"module_keys": ["module-1"]})
    # ...then revoke it again by sending an empty list.
    response = client.put(f"/api/admin/users/{target_user.id}/access", json={"module_keys": []})

    assert response.status_code == 200
    assert response.json()["accessible_module_keys"] == []


def test_super_admin_does_not_automatically_have_module_access(client: TestClient, db_session: Session) -> None:
    # Being super admin only grants the power to manage access for
    # everyone — it does not, by itself, open every module's tile.
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _create_module(db_session, key="module-1")
    _login(client, "admin@example.com")

    response = client.get("/api/modules/module-1/status")

    assert response.status_code == 403


def test_user_without_access_cannot_open_a_module(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="member@example.com")
    _create_module(db_session, key="module-1")
    _login(client, "member@example.com")

    response = client.get("/api/modules/module-1/status")

    assert response.status_code == 403


def test_user_with_granted_access_can_open_the_module(client: TestClient, db_session: Session) -> None:
    user = _create_user(db_session, email="member@example.com")
    module = _create_module(db_session, key="module-1")
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()
    _login(client, "member@example.com")

    response = client.get("/api/modules/module-1/status")

    assert response.status_code == 200
    assert response.json()["module_key"] == "module-1"


def test_module_admin_can_assign_roles_in_their_own_module(client: TestClient, db_session: Session) -> None:
    module_admin = _create_user(db_session, email="module-admin@example.com")
    team_member = _create_user(db_session, email="member@example.com")
    module = _create_module(db_session, key="module-1")

    # Both need access to the module first; the admin role is separate
    # from (and requires) that access grant.
    db_session.add(UserModuleAccess(user_id=module_admin.id, module_id=module.id))
    db_session.add(UserModuleAccess(user_id=team_member.id, module_id=module.id))
    db_session.add(ModuleRole(user_id=module_admin.id, module_id=module.id, role=ModuleRoleName.ADMIN))
    db_session.commit()

    _login(client, "module-admin@example.com")

    response = client.put(f"/api/modules/module-1/roles/{team_member.id}", json={"role": "editor"})

    assert response.status_code == 200
    assert response.json()["role"] == "editor"


def test_module_reader_cannot_assign_roles(client: TestClient, db_session: Session) -> None:
    reader = _create_user(db_session, email="reader@example.com")
    team_member = _create_user(db_session, email="member@example.com")
    module = _create_module(db_session, key="module-1")

    db_session.add(UserModuleAccess(user_id=reader.id, module_id=module.id))
    db_session.add(UserModuleAccess(user_id=team_member.id, module_id=module.id))
    db_session.add(ModuleRole(user_id=reader.id, module_id=module.id, role=ModuleRoleName.READER))
    db_session.commit()

    _login(client, "reader@example.com")

    response = client.put(f"/api/modules/module-1/roles/{team_member.id}", json={"role": "editor"})

    assert response.status_code == 403


def test_being_admin_of_one_module_does_not_grant_admin_of_another(client: TestClient, db_session: Session) -> None:
    module_admin = _create_user(db_session, email="module-admin@example.com")
    team_member = _create_user(db_session, email="member@example.com")
    module_one = _create_module(db_session, key="module-1", sort_order=1)
    module_two = _create_module(db_session, key="module-2", sort_order=2)

    db_session.add(UserModuleAccess(user_id=module_admin.id, module_id=module_one.id))
    db_session.add(ModuleRole(user_id=module_admin.id, module_id=module_one.id, role=ModuleRoleName.ADMIN))
    db_session.add(UserModuleAccess(user_id=team_member.id, module_id=module_two.id))
    db_session.commit()

    _login(client, "module-admin@example.com")

    response = client.put(f"/api/modules/module-2/roles/{team_member.id}", json={"role": "editor"})

    assert response.status_code == 403


def test_super_admin_can_manage_roles_in_any_module(client: TestClient, db_session: Session) -> None:
    super_admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    team_member = _create_user(db_session, email="member@example.com")
    module = _create_module(db_session, key="module-1")

    db_session.add(UserModuleAccess(user_id=team_member.id, module_id=module.id))
    db_session.commit()

    _login(client, "admin@example.com")

    response = client.put(f"/api/modules/module-1/roles/{team_member.id}", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_super_admin_can_delete_a_user(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    target_user = _create_user(db_session, email="member@example.com")
    _login(client, "admin@example.com")

    response = client.delete(f"/api/admin/users/{target_user.id}")
    assert response.status_code == 204

    # The deleted user should no longer show up in the admin list.
    list_response = client.get("/api/admin/users")
    assert all(user["id"] != target_user.id for user in list_response.json())


def test_deleting_a_user_also_removes_their_module_access(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="admin@example.com", is_super_admin=True)
    target_user = _create_user(db_session, email="member@example.com")
    module = _create_module(db_session, key="module-1")
    db_session.add(UserModuleAccess(user_id=target_user.id, module_id=module.id))
    db_session.commit()
    _login(client, "admin@example.com")

    response = client.delete(f"/api/admin/users/{target_user.id}")
    assert response.status_code == 204

    remaining_access = db_session.scalars(select(UserModuleAccess).where(UserModuleAccess.user_id == target_user.id)).all()
    assert remaining_access == []


def test_super_admin_cannot_delete_their_own_account(client: TestClient, db_session: Session) -> None:
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _login(client, "admin@example.com")

    response = client.delete(f"/api/admin/users/{admin.id}")

    assert response.status_code == 400


def test_non_super_admin_cannot_delete_users(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, email="regular@example.com")
    target_user = _create_user(db_session, email="member@example.com")
    _login(client, "regular@example.com")

    response = client.delete(f"/api/admin/users/{target_user.id}")

    assert response.status_code == 403
