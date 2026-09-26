# Shared test setup for the phone-API tests: creating users, modules and
# module-3 roles directly in the database, and logging in the way the phone
# does (Bearer token from /api/mobile/v1/auth/login).

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_requests_role import InterventionRequestsRole
from app.db.models.intervention_requests_role_permission import InterventionRequestsRolePermission
from app.db.models.intervention_requests_screen import InterventionRequestsScreen
from app.db.models.intervention_requests_user_role import InterventionRequestsUserRole
from app.db.models.intervention_status import InterventionStatus
from app.db.models.module import Module
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_3.screens import sync_screens

PASSWORD = "password123"


def create_user(db: Session, email: str, *, is_super_admin: bool = False) -> User:
    user = User(
        email=email, hashed_password=hash_password(PASSWORD), display_name=email, is_super_admin=is_super_admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_module(db: Session, key: str, *, is_active: bool = True) -> Module:
    module = db.scalar(select(Module).where(Module.key == key))
    if module is None:
        number = int(key.split("-")[1])
        module = Module(key=key, name=f"Module {number}", sort_order=number, is_active=is_active)
        db.add(module)
        db.commit()
        db.refresh(module)
    return module


def grant_access(db: Session, user: User, module_key: str) -> None:
    module = get_or_create_module(db, module_key)
    db.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db.commit()


def give_requests_role(
    db: Session, user: User, *, can_view: bool = False, can_create: bool = False, can_edit: bool = False
) -> None:
    """Give a user a module-3 role with exactly these rights on the requests screen."""
    sync_screens(db)
    role = InterventionRequestsRole(name=f"role-for-{user.email}")
    db.add(role)
    db.commit()
    db.refresh(role)
    screen = db.scalar(
        select(InterventionRequestsScreen).where(InterventionRequestsScreen.key == "interventionrequests.requests")
    )
    db.add(
        InterventionRequestsRolePermission(
            role_id=role.id,
            screen_id=screen.id,
            can_view=can_view,
            can_create=can_create,
            can_edit=can_edit,
            can_delete=False,
        )
    )
    db.add(InterventionRequestsUserRole(user_id=user.id, role_id=role.id))
    db.commit()


def bearer(client: TestClient, email: str) -> dict[str, str]:
    """Log in as the phone does and return the Authorization header."""
    response = client.post("/api/mobile/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_status(db: Session, name: str = "Nieuw", *, is_open: bool = True, color: str = "blue") -> InterventionStatus:
    status = InterventionStatus(name=name, is_open=is_open, color=color)
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


def create_team(db: Session, name: str = "Team A") -> Team:
    team = Team(name=name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def create_request(db: Session, status_id: int, *, number: str = "IA26_0001", team_name: str = "Vereniging X") -> InterventionRequest:
    request = InterventionRequest(request_number=number, team_name=team_name, question="Hulp nodig", status_id=status_id)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request
