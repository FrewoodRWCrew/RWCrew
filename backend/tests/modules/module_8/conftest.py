# Shared setup for Altsien Select's (module-8) tests: a small, realistic
# world with one season, two festivals, two teams, a delivery location, the
# seeded request statuses, a "Kernlid" role (wizard + ploegfiche) and an
# "Organisatie" role (all teams + request follow-up), plus helpers to create
# users holding either role.

from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.altsien_select_request_status import AltsienSelectRequestStatus
from app.db.models.altsien_select_role import AltsienSelectRole
from app.db.models.altsien_select_role_permission import AltsienSelectRolePermission
from app.db.models.altsien_select_screen import AltsienSelectScreen
from app.db.models.altsien_select_user_role import AltsienSelectUserRole
from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_kernlid import TeamKernlid
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_8.screens import sync_screens


@dataclass
class AltsienWorld:
    """Everything the module-8 tests share."""

    module: Module
    season: Season
    festival_a: Festival
    festival_b: Festival
    own_team: Team
    other_team: Team
    location: KarTrackerAfleverlocatie
    kernlid_role: AltsienSelectRole
    organisation_role: AltsienSelectRole
    status_new: AltsienSelectRequestStatus
    status_in_progress: AltsienSelectRequestStatus
    status_completed: AltsienSelectRequestStatus


def _role(db: Session, name: str, grants: dict[str, tuple[bool, bool, bool, bool]]) -> AltsienSelectRole:
    """A role with (view, create, edit, delete) per screen key."""
    role = AltsienSelectRole(name=name)
    db.add(role)
    db.flush()
    screens = {screen.key: screen for screen in db.scalars(select(AltsienSelectScreen)).all()}
    for key, (can_view, can_create, can_edit, can_delete) in grants.items():
        db.add(
            AltsienSelectRolePermission(
                role_id=role.id,
                screen_id=screens[key].id,
                can_view=can_view,
                can_create=can_create,
                can_edit=can_edit,
                can_delete=can_delete,
            )
        )
    return role


@pytest.fixture()
def world(db_session: Session) -> AltsienWorld:
    """Build the shared test data."""
    sync_screens(db_session)
    module = Module(key="module-8", name="Altsien Select", sort_order=8)
    season = Season(name="2026", periode_open=True)
    db_session.add_all([module, season])
    db_session.flush()

    festival_a = Festival(name="Rock Werchter", start_date=date(2026, 7, 2), end_date=date(2026, 7, 5), season_id=season.id)
    festival_b = Festival(name="TW Classic", start_date=date(2026, 6, 20), end_date=date(2026, 6, 20), season_id=season.id)
    own_team = Team(name="Chiro Werchter")
    other_team = Team(name="KSA Haacht")
    zone = KarTrackerZone(name="Zone 1")
    punt = KarTrackerDistributiepunt(name="DP 1")
    db_session.add_all([festival_a, festival_b, own_team, other_team, zone, punt])
    db_session.flush()

    location = KarTrackerAfleverlocatie(name="Backstage Noord", description="Achter main stage", zone_id=zone.id, distributiepunt_id=punt.id)
    statuses = [
        AltsienSelectRequestStatus(name="New", is_open=True, color="blue", sort_order=1),
        AltsienSelectRequestStatus(name="In Progress", is_open=True, color="amber", sort_order=2),
        AltsienSelectRequestStatus(name="Completed", is_open=False, color="green", sort_order=3),
    ]
    db_session.add(location)
    db_session.add_all(statuses)

    kernlid_role = _role(
        db_session,
        "Kernlid",
        {"altsienselect.wizard": (True, True, True, True), "altsienselect.ploegfiche": (True, False, False, False)},
    )
    organisation_role = _role(
        db_session,
        "Organisatie",
        {
            "altsienselect.wizard": (True, True, True, True),
            "altsienselect.ploegfiche": (True, False, False, False),
            "altsienselect.allteams": (True, False, True, False),
            "altsienselect.requests": (True, False, True, False),
        },
    )
    db_session.commit()
    return AltsienWorld(
        module, season, festival_a, festival_b, own_team, other_team, location,
        kernlid_role, organisation_role, *statuses,
    )


@pytest.fixture()
def make_user(db_session: Session, world: AltsienWorld):
    """Create a user with module-8 access and the given role, linked as
    Kernlid to the given teams.
    """

    def _make(email: str, role: AltsienSelectRole | None, teams: list[Team] = ()) -> User:
        user = User(email=email, hashed_password=hash_password("password123"), display_name=email, is_altsien_kernlid=True)
        db_session.add(user)
        db_session.flush()
        db_session.add(UserModuleAccess(user_id=user.id, module_id=world.module.id))
        if role is not None:
            db_session.add(AltsienSelectUserRole(user_id=user.id, role_id=role.id))
        for team in teams:
            db_session.add(TeamKernlid(team_id=team.id, altsien_kernlid_id=user.id))
        db_session.commit()
        return user

    return _make


def login(client: TestClient, email: str) -> None:
    """Log in with the test password."""
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


@pytest.fixture()
def as_kernlid(client: TestClient, world: AltsienWorld, make_user) -> TestClient:
    """A client logged in as a Kernlid of own_team only."""
    make_user("kernlid@example.com", world.kernlid_role, [world.own_team])
    login(client, "kernlid@example.com")
    return client
