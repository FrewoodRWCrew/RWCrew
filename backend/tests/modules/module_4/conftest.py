# Shared setup for StockMaster's (module-4) tests: a small warehouse world
# with an open and a closed season, a warehouse, three products (a normal
# one, a consumable with a minimum stock, and a blocked one), two kars of
# one team, a festival, the seeded reasons, and a "Magazijn" role with
# every right, plus helpers to create users and make bookings.

from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.festival import Festival
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.season import Season
from app.db.models.stockmaster_reason import StockMasterReason
from app.db.models.stockmaster_role import StockMasterRole
from app.db.models.stockmaster_role_permission import StockMasterRolePermission
from app.db.models.stockmaster_screen import StockMasterScreen
from app.db.models.stockmaster_user_role import StockMasterUserRole
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.db.models.warehouse import Warehouse
from app.modules.module_4.screens import SCREEN_DEFINITIONS, sync_screens

BASE = "/api/modules/module-4"


@dataclass
class StockWorld:
    """Everything the module-4 tests share."""

    module: Module
    season: Season
    closed_season: Season
    warehouse: Warehouse
    lader: Product
    tape: Product
    blocked: Product
    team: Team
    festival: Festival
    k101: KarTrackerKar
    k043: KarTrackerKar
    reason_used: StockMasterReason
    reason_count: StockMasterReason
    full_role: StockMasterRole


def make_role(db: Session, name: str, grants: dict[str, tuple[bool, bool, bool, bool]]) -> StockMasterRole:
    """A role with (view, create, edit, delete) per screen key."""
    role = StockMasterRole(name=name)
    db.add(role)
    db.flush()
    screens = {screen.key: screen for screen in db.scalars(select(StockMasterScreen)).all()}
    for key, (can_view, can_create, can_edit, can_delete) in grants.items():
        db.add(
            StockMasterRolePermission(
                role_id=role.id,
                screen_id=screens[key].id,
                can_view=can_view,
                can_create=can_create,
                can_edit=can_edit,
                can_delete=can_delete,
            )
        )
    db.commit()
    return role


@pytest.fixture()
def world(db_session: Session) -> StockWorld:
    """Build the shared test data."""
    sync_screens(db_session)
    module = Module(key="module-4", name="StockMaster", sort_order=4)
    season = Season(name="2026", periode_open=True)
    closed_season = Season(name="2025", periode_open=False)
    warehouse = Warehouse(name="Hal A")
    team = Team(name="Chiro Werchter")
    status = KarTrackerKarStatus(name="Beschikbaar")
    db_session.add_all([module, season, closed_season, warehouse, team, status])
    db_session.flush()

    lader = Product(name="Walkie-lader", warehouse_id=warehouse.id, warehouse_location="B-12")
    tape = Product(name="Tape", warehouse_id=warehouse.id, warehouse_location="A-01", is_consumable=True, min_stock=10)
    blocked = Product(name="Oude kabel", warehouse_id=warehouse.id, warehouse_location="C-03", is_blocked=True)
    db_session.add_all([lader, tape, blocked])
    db_session.flush()

    k101 = KarTrackerKar(kar_nummer="K101", status_id=status.id, team_id=team.id, transport_type_id=lader.id)
    k043 = KarTrackerKar(kar_nummer="K043", status_id=status.id, team_id=team.id, transport_type_id=lader.id)
    festival = Festival(name="Rock Werchter", start_date=date(2026, 7, 2), end_date=date(2026, 7, 5), season_id=season.id)
    reason_used = StockMasterReason(name="Verbruikt", applies_to="book_out", sort_order=1)
    reason_count = StockMasterReason(name="Telverschil", applies_to="count", sort_order=2)
    db_session.add_all([k101, k043, festival, reason_used, reason_count])
    db_session.flush()
    db_session.add(TeamFestival(season_id=season.id, team_id=team.id, festival_id=festival.id))
    db_session.commit()

    everything = (True, True, True, True)
    full_role = make_role(
        db_session,
        "Magazijn",
        {definition.key: everything for definition in SCREEN_DEFINITIONS if definition.key != "stockmaster.closedseason"},
    )
    return StockWorld(
        module, season, closed_season, warehouse, lader, tape, blocked, team, festival, k101, k043,
        reason_used, reason_count, full_role,
    )


@pytest.fixture()
def make_user(db_session: Session, world: StockWorld):
    """Create a user with module-4 access and the given role."""

    def _make(email: str, role: StockMasterRole | None, *, access: bool = True, super_admin: bool = False) -> User:
        user = User(
            email=email, hashed_password=hash_password("password123"), display_name=email.split("@")[0].title(),
            is_super_admin=super_admin,
        )
        db_session.add(user)
        db_session.flush()
        if access:
            db_session.add(UserModuleAccess(user_id=user.id, module_id=world.module.id))
        if role is not None:
            db_session.add(StockMasterUserRole(user_id=user.id, role_id=role.id))
        db_session.commit()
        return user

    return _make


def login(client: TestClient, email: str) -> None:
    """Log in with the test password."""
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200


@pytest.fixture()
def as_warehouse(client: TestClient, world: StockWorld, make_user) -> TestClient:
    """A client logged in as "Magazijnier" with every StockMaster right."""
    make_user("magazijnier@example.com", world.full_role)
    login(client, "magazijnier@example.com")
    return client


def book(client: TestClient, world: StockWorld, action: str, lines: list[tuple[int, int] | tuple[int, int, str]] = (), **fields):
    """POST one booking in the open season; returns the response."""
    payload = {
        "action": action,
        "season_id": fields.pop("season_id", world.season.id),
        "lines": [
            {"product_id": line[0], "quantity": line[1], **({"destination": line[2]} if len(line) > 2 else {})}
            for line in lines
        ],
        **fields,
    }
    return client.post(f"{BASE}/bookings", json=payload)


def stock_of(client: TestClient, product_id: int) -> dict:
    """One product's line on the stock overview."""
    rows = client.get(f"{BASE}/stock").json()
    return next(row for row in rows if row["product_id"] == product_id)
