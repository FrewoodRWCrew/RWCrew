# These tests check MasterData's landing dashboard ("Masterdata
# Overview"): aggregate KPI stats gated by plain module access (no
# specific screen permission), mirroring
# backend/tests/modules/module_1/test_dashboard.py.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.season import Season
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


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def _create_season(db_session: Session, *, name: str) -> Season:
    season = Season(name=name)
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


def test_dashboard_requires_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    _create_masterdata_module(db_session)
    _create_user(db_session, email="regular@example.com")
    _login(client, "regular@example.com")

    response = client.get("/api/modules/module-9/dashboard")

    assert response.status_code == 403


def test_dashboard_counts_seasons(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _create_season(db_session, name="Summer 2026")
    _create_season(db_session, name="Winter 2026")
    _login(client, "viewer@example.com")

    response = client.get("/api/modules/module-9/dashboard")

    assert response.status_code == 200
    # The product stats moved to StockMaster (tests/modules/module_4/test_product_stats.py).
    assert response.json() == {"total_seasons": 2}
