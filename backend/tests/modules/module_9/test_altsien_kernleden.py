# These tests check the "Altsien Kernleden" screen: gated by normal
# module access + the "masterdata.altsien-kernleden" permission,
# independently of "masterdata.season"/others, with a super-admin
# bypass and full CRUD — mirrors test_festivals.py's shape (a
# multi-field entity with no FK and no uniqueness constraint).

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.models.altsien_kernlid import AltsienKernlid
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
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


def _grant_altsien_kernleden_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = MasterDataRole(name=f"Altsien Kernleden Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == "masterdata.altsien-kernleden"))
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


def _create_altsien_kernlid(
    db_session: Session,
    *,
    first_name: str = "Jan",
    name: str = "Janssens",
    telephone_number: str = "+32 470 12 34 56",
    email: str = "jan.janssens@example.com",
) -> AltsienKernlid:
    row = AltsienKernlid(first_name=first_name, name=name, telephone_number=telephone_number, email=email)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_user_without_module_access_cannot_list_altsien_kernleden(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_masterdata_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/altsien-kernleden")

    assert response.status_code == 403


def test_user_with_access_but_no_permission_cannot_list_altsien_kernleden(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/altsien-kernleden")

    assert response.status_code == 403


def test_altsien_kernleden_permission_does_not_grant_access_to_season_screen(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_altsien_kernleden_permission(db_session, user, can_view=True, can_create=True)
    _login(client, "viewer@example.com")

    assert client.get("/api/modules/module-9/altsien-kernleden").status_code == 200
    assert client.get("/api/modules/module-9/seasons").status_code == 403


def test_super_admin_can_create_a_contact_without_an_explicit_role(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/altsien-kernleden",
        json={
            "first_name": "Jan",
            "name": "Janssens",
            "telephone_number": "+32 470 12 34 56",
            "email": "jan.janssens@example.com",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["first_name"] == "Jan"
    assert body["name"] == "Janssens"
    assert body["telephone_number"] == "+32 470 12 34 56"
    assert body["email"] == "jan.janssens@example.com"


def test_view_only_permission_cannot_create_a_contact(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_altsien_kernleden_permission(db_session, user, can_view=True)
    _login(client, "viewer@example.com")

    response = client.post(
        "/api/modules/module-9/altsien-kernleden",
        json={
            "first_name": "Jan",
            "name": "Janssens",
            "telephone_number": "+32 470 12 34 56",
            "email": "jan.janssens@example.com",
        },
    )

    assert response.status_code == 403


def test_view_only_permission_cannot_update_or_delete(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_altsien_kernleden_permission(db_session, user, can_view=True)
    contact = _create_altsien_kernlid(db_session)
    _login(client, "viewer@example.com")

    update_response = client.put(
        f"/api/modules/module-9/altsien-kernleden/{contact.id}",
        json={
            "first_name": "Jan",
            "name": "Janssens",
            "telephone_number": "+32 470 12 34 56",
            "email": "jan.janssens@example.com",
        },
    )
    delete_response = client.delete(f"/api/modules/module-9/altsien-kernleden/{contact.id}")

    assert update_response.status_code == 403
    assert delete_response.status_code == 403


def test_creating_a_contact_with_an_invalid_email_returns_422(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.post(
        "/api/modules/module-9/altsien-kernleden",
        json={
            "first_name": "Jan",
            "name": "Janssens",
            "telephone_number": "+32 470 12 34 56",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422


def test_list_altsien_kernleden_ordered_by_name_then_first_name(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _create_altsien_kernlid(db_session, first_name="Zoe", name="Aerts", email="zoe@example.com")
    _create_altsien_kernlid(db_session, first_name="Jan", name="Bosmans", email="jan@example.com")
    _login(client, "admin@example.com")

    response = client.get("/api/modules/module-9/altsien-kernleden")

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Aerts", "Bosmans"]


def test_super_admin_can_update_a_contact(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    contact = _create_altsien_kernlid(db_session)
    _login(client, "admin@example.com")

    response = client.put(
        f"/api/modules/module-9/altsien-kernleden/{contact.id}",
        json={
            "first_name": "Janneke",
            "name": "Janssens-Peeters",
            "telephone_number": "+32 470 99 88 77",
            "email": "janneke@example.com",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Janneke"
    assert body["name"] == "Janssens-Peeters"
    assert body["telephone_number"] == "+32 470 99 88 77"
    assert body["email"] == "janneke@example.com"


def test_updating_a_missing_contact_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.put(
        "/api/modules/module-9/altsien-kernleden/999",
        json={
            "first_name": "Jan",
            "name": "Janssens",
            "telephone_number": "+32 470 12 34 56",
            "email": "jan.janssens@example.com",
        },
    )

    assert response.status_code == 404


def test_super_admin_can_delete_a_contact(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    contact = _create_altsien_kernlid(db_session)
    _login(client, "admin@example.com")

    response = client.delete(f"/api/modules/module-9/altsien-kernleden/{contact.id}")

    assert response.status_code == 204
    assert client.get("/api/modules/module-9/altsien-kernleden").json() == []


def test_deleting_a_missing_contact_returns_404(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")

    response = client.delete("/api/modules/module-9/altsien-kernleden/999")

    assert response.status_code == 404
