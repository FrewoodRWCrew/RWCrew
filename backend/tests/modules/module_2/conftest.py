# Shared setup helpers for KarTracker's tests (test_roles.py,
# test_kar_management.py). Plain functions rather than fixtures, since each
# call site needs different arguments (e.g. which screen a role gets
# permissions on) — pytest auto-discovers this file, but these still need
# to be imported explicitly where used, same as any other module.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.kartracker_role import KarTrackerRole
from app.db.models.kartracker_role_permission import KarTrackerRolePermission
from app.db.models.kartracker_screen import KarTrackerScreen
from app.db.models.module import Module
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess


def create_user(db_session: Session, *, email: str, is_super_admin: bool = False) -> User:
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


def create_kartracker_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-2"))
    if module is not None:
        return module
    module = Module(key="module-2", name="KarTracker", sort_order=2)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def create_role_with_permissions(
    db_session: Session,
    *,
    name: str,
    screen_key: str,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> KarTrackerRole:
    role = KarTrackerRole(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(select(KarTrackerScreen).where(KarTrackerScreen.key == screen_key))
    db_session.add(
        KarTrackerRolePermission(
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


def login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})
