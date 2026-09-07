# These tests check Intervention Requests' landing dashboard ("KPI
# overview"): aggregate KPI stats gated by plain module access (no
# specific screen permission), mirroring
# backend/tests/modules/module_9/test_dashboard.py.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_status import InterventionStatus
from app.db.models.module import Module
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_3.screens import sync_screens


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


def _create_intervention_requests_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-3"))
    if module is not None:
        return module
    module = Module(key="module-3", name="Intervention Requests", sort_order=3)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def _create_status(db_session: Session, *, name: str, is_open: bool = True, color: str = "gray") -> InterventionStatus:
    status = InterventionStatus(name=name, is_open=is_open, color=color)
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


def _create_team(db_session: Session, *, name: str) -> Team:
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_request(
    db_session: Session,
    *,
    request_number: str,
    status_id: int,
    team_id: int | None = None,
    team_name: str | None = None,
) -> InterventionRequest:
    request = InterventionRequest(
        request_number=request_number,
        team_id=team_id,
        team_name=team_name,
        question="Please help",
        status_id=status_id,
    )
    db_session.add(request)
    db_session.commit()
    db_session.refresh(request)
    return request


def test_dashboard_requires_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_intervention_requests_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-3/dashboard")

    assert response.status_code == 403


def test_dashboard_with_no_data_returns_all_zero_stats(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_intervention_requests_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-3/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 0
    assert body["open_requests"] == 0
    assert body["closed_requests"] == 0
    assert body["status_breakdown"] == []
    assert body["team_breakdown"] == []


def test_dashboard_computes_open_closed_and_status_breakdown(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_intervention_requests_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    open_status = _create_status(db_session, name="Nieuw", is_open=True, color="green")
    closed_status = _create_status(db_session, name="Afgesloten", is_open=False, color="gray")

    _create_request(db_session, request_number="IA26_0001", status_id=open_status.id, team_name="Team A")
    _create_request(db_session, request_number="IA26_0002", status_id=open_status.id, team_name="Team A")
    _create_request(db_session, request_number="IA26_0003", status_id=closed_status.id, team_name="Team B")

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-3/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 3
    assert body["open_requests"] == 2
    assert body["closed_requests"] == 1
    # Ordered by status name ("Afgesloten" before "Nieuw"); every status
    # appears even though neither has zero requests here.
    assert body["status_breakdown"] == [
        {"status_name": "Afgesloten", "color": "gray", "count": 1},
        {"status_name": "Nieuw", "color": "green", "count": 2},
    ]


def test_dashboard_team_breakdown_merges_real_teams_and_free_text_names(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_intervention_requests_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)

    status = _create_status(db_session, name="Nieuw")
    team = _create_team(db_session, name="Zebra Team")

    # Two requests for a real MasterData team, one for a free-typed name
    # not yet in MasterData, one for a different free-typed name.
    _create_request(db_session, request_number="IA26_0001", status_id=status.id, team_id=team.id)
    _create_request(db_session, request_number="IA26_0002", status_id=status.id, team_id=team.id)
    _create_request(db_session, request_number="IA26_0003", status_id=status.id, team_name="Alpha Association")
    _create_request(db_session, request_number="IA26_0004", status_id=status.id, team_name="Alpha Association")

    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-3/dashboard")

    assert response.status_code == 200
    team_breakdown = response.json()["team_breakdown"]
    # Sorted case-insensitively by name, real-team and free-text names
    # merged into the same list.
    assert team_breakdown == [
        {"team_name": "Alpha Association", "count": 2},
        {"team_name": "Zebra Team", "count": 2},
    ]
