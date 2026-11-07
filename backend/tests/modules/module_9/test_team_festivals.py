# Tests for MasterData's "Festivals per ploeg" grid (masterdata.team-festivals):
# the grid of one year, saving ticked/unticked cells through the shared
# team_festival_service (removing a link deletes the Plan a kar location and
# re-opens Altsien Select's "afleverlocaties" step), the closed-year lock,
# the rights, and the "copy from previous year" proposal.

from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_9.screens import sync_screens

URL = "/api/modules/module-9/team-festivals"


@dataclass
class GridWorld:
    """The shared test data: two years, festivals, three teams, a location."""

    season: Season
    rock: Festival
    tw: Festival
    old_festival: Festival
    team_a: Team
    team_b: Team
    inactive_team: Team
    location: KarTrackerAfleverlocatie


@pytest.fixture()
def world(db_session: Session) -> GridWorld:
    """2026 (open) with Rock Werchter, TW Classic and an inactive festival;
    team A works at Rock Werchter and has a delivery location there.
    """
    sync_screens(db_session)
    season = Season(name="2026", periode_open=True)
    db_session.add(season)
    db_session.flush()
    rock = Festival(name="Rock Werchter 2026", start_date=date(2026, 7, 2), end_date=date(2026, 7, 5), season_id=season.id)
    tw = Festival(name="TW Classic", start_date=date(2026, 6, 20), end_date=date(2026, 6, 20), season_id=season.id)
    old_festival = Festival(
        name="Oud festival", start_date=date(2026, 5, 1), end_date=date(2026, 5, 1), season_id=season.id, active=False
    )
    team_a = Team(name="Chiro Werchter")
    team_b = Team(name="KSA Haacht")
    inactive_team = Team(name="Zzz oude ploeg", active=False)
    zone = KarTrackerZone(name="Zone 1")
    punt = KarTrackerDistributiepunt(name="DP 1")
    db_session.add_all([rock, tw, old_festival, team_a, team_b, inactive_team, zone, punt])
    db_session.flush()
    location = KarTrackerAfleverlocatie(name="Backstage", zone_id=zone.id, distributiepunt_id=punt.id)
    db_session.add(location)
    db_session.flush()
    db_session.add(TeamFestival(season_id=season.id, team_id=team_a.id, festival_id=rock.id))
    db_session.add(
        KarTrackerKarAfleverlocatie(
            season_id=season.id, festival_id=rock.id, team_id=team_a.id, afleverlocatie_id=location.id
        )
    )
    # Team A already confirmed both wizard steps.
    for step_key in ("festivals", "afleverlocaties"):
        db_session.add(AltsienSelectStepProgress(season_id=season.id, team_id=team_a.id, step_key=step_key))
    db_session.commit()
    return GridWorld(season, rock, tw, old_festival, team_a, team_b, inactive_team, location)


def _login_with(client: TestClient, db_session: Session, *, view: bool = True, edit: bool = True) -> None:
    """Log in a user with MasterData access and these rights on the grid."""
    module = db_session.scalar(select(Module).where(Module.key == "module-9"))
    if module is None:
        module = Module(key="module-9", name="MasterData", sort_order=9)
        db_session.add(module)
        db_session.flush()
    user = User(email="md@example.com", hashed_password=hash_password("password123"), display_name="MD")
    role = MasterDataRole(name="Grid role")
    db_session.add_all([user, role])
    db_session.flush()
    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == "masterdata.team-festivals"))
    db_session.add(MasterDataRolePermission(role_id=role.id, screen_id=screen.id, can_view=view, can_edit=edit))
    db_session.add(MasterDataUserRole(user_id=user.id, role_id=role.id))
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()
    client.post("/api/auth/login", json={"email": "md@example.com", "password": "password123"})


def _save(client: TestClient, world: GridWorld, changes: list[tuple[int, int, bool]]):
    return client.put(
        f"{URL}/grid",
        json={
            "season_id": world.season.id,
            "changes": [{"team_id": t, "festival_id": f, "selected": s} for t, f, s in changes],
        },
    )


def _steps(db_session: Session, world: GridWorld, team: Team) -> set[str]:
    db_session.expire_all()
    return set(
        db_session.scalars(
            select(AltsienSelectStepProgress.step_key).where(
                AltsienSelectStepProgress.season_id == world.season.id, AltsienSelectStepProgress.team_id == team.id
            )
        ).all()
    )


# --- reading ---------------------------------------------------------------------


def test_grid_lists_festivals_teams_and_links(client: TestClient, db_session: Session, world: GridWorld) -> None:
    _login_with(client, db_session)

    body = client.get(f"{URL}/grid?season_id={world.season.id}").json()

    # By start date; the inactive festival without links is left out.
    assert [festival["name"] for festival in body["festivals"]] == ["TW Classic", "Rock Werchter 2026"]
    # Active teams by name; the inactive team without links is left out.
    assert [team["name"] for team in body["teams"]] == ["Chiro Werchter", "KSA Haacht"]
    assert body["links"] == [[world.team_a.id, world.rock.id]]
    assert body["planned"] == [[world.team_a.id, world.rock.id]]
    assert body["editable"] is True
    assert body["can_edit"] is True


def test_options_default_to_the_last_open_year(client: TestClient, db_session: Session, world: GridWorld) -> None:
    db_session.add(Season(name="2027", periode_open=False))
    db_session.commit()
    _login_with(client, db_session)

    body = client.get(f"{URL}/options").json()

    assert [season["name"] for season in body["seasons"]] == ["2026", "2027"]
    assert body["default_season_id"] == world.season.id


# --- saving ------------------------------------------------------------------------


def test_ticking_adds_links_and_reopens_the_location_step(
    client: TestClient, db_session: Session, world: GridWorld
) -> None:
    _login_with(client, db_session)

    response = _save(client, world, [(world.team_a.id, world.tw.id, True), (world.team_b.id, world.rock.id, True)])

    assert response.status_code == 200
    assert sorted(map(tuple, response.json()["links"])) == sorted(
        [(world.team_a.id, world.rock.id), (world.team_a.id, world.tw.id), (world.team_b.id, world.rock.id)]
    )
    # Team A's delivery locations must be confirmed again; its festival step stays.
    assert _steps(db_session, world, world.team_a) == {"festivals"}


def test_unticking_deletes_the_delivery_location(client: TestClient, db_session: Session, world: GridWorld) -> None:
    _login_with(client, db_session)

    response = _save(client, world, [(world.team_a.id, world.rock.id, False)])

    assert response.status_code == 200
    assert response.json()["links"] == []
    assert db_session.scalars(select(KarTrackerKarAfleverlocatie)).all() == []
    # No festivals left: both wizard steps are open again.
    assert _steps(db_session, world, world.team_a) == set()


def test_inactive_festival_cannot_be_ticked(client: TestClient, db_session: Session, world: GridWorld) -> None:
    _login_with(client, db_session)

    assert _save(client, world, [(world.team_b.id, world.old_festival.id, True)]).status_code == 400
    # Nothing was written.
    assert len(db_session.scalars(select(TeamFestival)).all()) == 1


def test_festival_of_another_year_is_refused(client: TestClient, db_session: Session, world: GridWorld) -> None:
    other = Season(name="2025", periode_open=True)
    db_session.add(other)
    db_session.flush()
    foreign = Festival(name="Pukkelpop", start_date=date(2025, 8, 14), end_date=date(2025, 8, 17), season_id=other.id)
    db_session.add(foreign)
    db_session.commit()
    _login_with(client, db_session)

    assert _save(client, world, [(world.team_b.id, foreign.id, True)]).status_code == 400


def test_closed_year_is_read_only(client: TestClient, db_session: Session, world: GridWorld) -> None:
    db_session.get(Season, world.season.id).periode_open = False
    db_session.commit()
    _login_with(client, db_session)

    assert client.get(f"{URL}/grid?season_id={world.season.id}").json()["editable"] is False
    response = _save(client, world, [(world.team_b.id, world.rock.id, True)])
    assert response.status_code == 403
    assert response.json()["detail"] == "season_closed"


# --- rights ------------------------------------------------------------------------


def test_view_right_cannot_save(client: TestClient, db_session: Session, world: GridWorld) -> None:
    _login_with(client, db_session, edit=False)

    grid = client.get(f"{URL}/grid?season_id={world.season.id}")
    assert grid.status_code == 200
    assert grid.json()["can_edit"] is False
    assert _save(client, world, [(world.team_b.id, world.rock.id, True)]).status_code == 403


def test_no_right_cannot_view(client: TestClient, db_session: Session, world: GridWorld) -> None:
    _login_with(client, db_session, view=False, edit=False)

    assert client.get(f"{URL}/grid?season_id={world.season.id}").status_code == 403
    assert client.get(f"{URL}/options").status_code == 403


# --- copy from the previous year ------------------------------------------------------


def test_previous_year_is_mapped_by_festival_name(client: TestClient, db_session: Session, world: GridWorld) -> None:
    previous = Season(name="2025", periode_open=False)
    db_session.add(previous)
    db_session.flush()
    rock_2025 = Festival(name="Rock Werchter 2025", start_date=date(2025, 7, 3), end_date=date(2025, 7, 6), season_id=previous.id)
    boutique = Festival(name="Werchter Boutique", start_date=date(2025, 6, 28), end_date=date(2025, 6, 28), season_id=previous.id)
    db_session.add_all([rock_2025, boutique])
    db_session.flush()
    for team, festival in (
        (world.team_a, rock_2025),  # already linked in 2026
        (world.team_b, rock_2025),  # proposed
        (world.team_b, boutique),  # no 2026 festival
        (world.inactive_team, rock_2025),  # inactive team: skipped
    ):
        db_session.add(TeamFestival(season_id=previous.id, team_id=team.id, festival_id=festival.id))
    db_session.commit()
    _login_with(client, db_session)

    body = client.get(f"{URL}/previous?season_id={world.season.id}").json()

    assert body["previous_season_name"] == "2025"
    assert body["links"] == [[world.team_b.id, world.rock.id]]
    assert body["already_present"] == 1
    assert body["unmatched"] == [{"festival_name": "Werchter Boutique", "team_count": 1}]
    # Only a proposal: nothing was written.
    assert len(db_session.scalars(select(TeamFestival).where(TeamFestival.season_id == world.season.id)).all()) == 1


def test_no_previous_year_gives_an_empty_proposal(client: TestClient, db_session: Session, world: GridWorld) -> None:
    _login_with(client, db_session)

    body = client.get(f"{URL}/previous?season_id={world.season.id}").json()

    assert body == {
        "previous_season_id": None,
        "previous_season_name": None,
        "links": [],
        "already_present": 0,
        "unmatched": [],
    }
