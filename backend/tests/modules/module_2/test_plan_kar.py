# Tests for the "Plan a kar" screen (see module_2/router.py's /plan-kar
# endpoints): per team, one delivery location per active festival of a
# season, saved as an upsert on (season, festival, team) into
# KarTracker_kar_afleverlocaties.

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.season import Season
from app.db.models.team import Team
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)


def _login_admin(client: TestClient, db_session: Session) -> None:
    """Set up the module and log in as a super admin with module access."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")


def _create_season(db_session: Session, *, name: str = "2026") -> Season:
    season = Season(name=name)
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


def _create_festival(
    db_session: Session, *, season_id: int, name: str = "Summer Bash", start_date: str = "2026-07-01", active: bool = True
) -> Festival:
    festival = Festival(
        name=name,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(start_date),
        season_id=season_id,
        active=active,
    )
    db_session.add(festival)
    db_session.commit()
    db_session.refresh(festival)
    return festival


def _create_team(db_session: Session, *, name: str = "Scouts Wezemaal", active: bool = True) -> Team:
    team = Team(name=name, active=active)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_location(db_session: Session, *, name: str = "Poort 1", active: bool = True) -> KarTrackerAfleverlocatie:
    zone = KarTrackerZone(name=f"Zone {name}")
    distributiepunt = KarTrackerDistributiepunt(name=f"DP {name}")
    db_session.add_all([zone, distributiepunt])
    db_session.commit()
    location = KarTrackerAfleverlocatie(
        name=name, zone_id=zone.id, distributiepunt_id=distributiepunt.id, active=active
    )
    db_session.add(location)
    db_session.commit()
    db_session.refresh(location)
    return location


def _record_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(KarTrackerKarAfleverlocatie)) or 0


def test_user_without_plankar_permission_cannot_view_it(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    # Permission on another screen must not open this one.
    role = create_role_with_permissions(db_session, name="Map Viewer", screen_key="kartracker.karmap", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    assert client.get("/api/modules/module-2/plan-kar/teams").status_code == 403
    assert client.get("/api/modules/module-2/plan-kar/afleverlocaties").status_code == 403
    assert client.get("/api/modules/module-2/plan-kar", params={"season_id": 1, "team_id": 1}).status_code == 403
    payload = {"season_id": 1, "team_id": 1, "rows": []}
    assert client.put("/api/modules/module-2/plan-kar", json=payload).status_code == 403


def test_dropdown_lists_only_include_active_entries(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    _create_team(db_session, name="Active Team")
    _create_team(db_session, name="Inactive Team", active=False)
    _create_location(db_session, name="Active Gate")
    _create_location(db_session, name="Inactive Gate", active=False)

    teams = client.get("/api/modules/module-2/plan-kar/teams").json()
    locations = client.get("/api/modules/module-2/plan-kar/afleverlocaties").json()

    assert [team["name"] for team in teams] == ["Active Team"]
    assert [location["name"] for location in locations] == ["Active Gate"]


def test_afleverlocatie_dropdown_includes_the_description(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    gate = _create_location(db_session, name="Poort 1")
    gate.description = "Main entrance, north side"
    db_session.commit()
    _create_location(db_session, name="Poort 2")

    locations = client.get("/api/modules/module-2/plan-kar/afleverlocaties").json()

    assert [(item["name"], item["description"]) for item in locations] == [
        ("Poort 1", "Main entrance, north side"),
        ("Poort 2", None),
    ]


def test_matrix_lists_only_active_festivals_of_the_season_without_locations(
    client: TestClient, db_session: Session
) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session, name="2026")
    other_season = _create_season(db_session, name="2027")
    team = _create_team(db_session)
    _create_festival(db_session, season_id=season.id, name="Beta Fest", start_date="2026-08-01")
    _create_festival(db_session, season_id=season.id, name="Alpha Fest", start_date="2026-07-01")
    _create_festival(db_session, season_id=season.id, name="Dormant Fest", active=False)
    _create_festival(db_session, season_id=other_season.id, name="Next Year Fest")

    response = client.get("/api/modules/module-2/plan-kar", params={"season_id": season.id, "team_id": team.id})

    assert response.status_code == 200
    rows = response.json()["rows"]
    # Ordered by start date, nothing saved yet.
    assert [row["festival_name"] for row in rows] == ["Alpha Fest", "Beta Fest"]
    assert all(row["afleverlocatie_id"] is None for row in rows)


def test_matrix_unknown_season_or_team_is_404(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    team = _create_team(db_session)

    assert client.get("/api/modules/module-2/plan-kar", params={"season_id": 999, "team_id": team.id}).status_code == 404
    assert client.get("/api/modules/module-2/plan-kar", params={"season_id": season.id, "team_id": 999}).status_code == 404


def test_save_inserts_then_second_save_updates_without_duplicating(
    client: TestClient, db_session: Session
) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    team = _create_team(db_session)
    festival_a = _create_festival(db_session, season_id=season.id, name="Alpha Fest", start_date="2026-07-01")
    festival_b = _create_festival(db_session, season_id=season.id, name="Beta Fest", start_date="2026-08-01")
    gate_1 = _create_location(db_session, name="Poort 1")
    gate_2 = _create_location(db_session, name="Poort 2")

    first = client.put(
        "/api/modules/module-2/plan-kar",
        json={
            "season_id": season.id,
            "team_id": team.id,
            "rows": [
                {"festival_id": festival_a.id, "afleverlocatie_id": gate_1.id},
                {"festival_id": festival_b.id, "afleverlocatie_id": gate_1.id},
            ],
        },
    )
    assert first.status_code == 200
    assert _record_count(db_session) == 2

    # Same combinations again, one with a different location: must update.
    second = client.put(
        "/api/modules/module-2/plan-kar",
        json={
            "season_id": season.id,
            "team_id": team.id,
            "rows": [
                {"festival_id": festival_a.id, "afleverlocatie_id": gate_1.id},
                {"festival_id": festival_b.id, "afleverlocatie_id": gate_2.id},
            ],
        },
    )
    assert second.status_code == 200
    assert _record_count(db_session) == 2

    # Reopening the screen pre-fills the saved values.
    reopened = client.get("/api/modules/module-2/plan-kar", params={"season_id": season.id, "team_id": team.id})
    saved = {row["festival_id"]: row["afleverlocatie_id"] for row in reopened.json()["rows"]}
    assert saved == {festival_a.id: gate_1.id, festival_b.id: gate_2.id}


def test_assignments_are_kept_per_team(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    team_one = _create_team(db_session, name="Team One")
    team_two = _create_team(db_session, name="Team Two")
    festival = _create_festival(db_session, season_id=season.id)
    gate = _create_location(db_session)

    client.put(
        "/api/modules/module-2/plan-kar",
        json={
            "season_id": season.id,
            "team_id": team_one.id,
            "rows": [{"festival_id": festival.id, "afleverlocatie_id": gate.id}],
        },
    )

    other = client.get("/api/modules/module-2/plan-kar", params={"season_id": season.id, "team_id": team_two.id})
    assert other.json()["rows"][0]["afleverlocatie_id"] is None


def test_clearing_a_row_removes_its_record(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    team = _create_team(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    gate = _create_location(db_session)
    url = "/api/modules/module-2/plan-kar"
    client.put(
        url,
        json={"season_id": season.id, "team_id": team.id, "rows": [{"festival_id": festival.id, "afleverlocatie_id": gate.id}]},
    )
    assert _record_count(db_session) == 1

    cleared = client.put(
        url,
        json={"season_id": season.id, "team_id": team.id, "rows": [{"festival_id": festival.id, "afleverlocatie_id": None}]},
    )

    assert cleared.status_code == 200
    assert _record_count(db_session) == 0


def test_save_rejects_invalid_references(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session, name="2026")
    other_season = _create_season(db_session, name="2027")
    team = _create_team(db_session)
    inactive_team = _create_team(db_session, name="Inactive Team", active=False)
    festival = _create_festival(db_session, season_id=season.id)
    foreign_festival = _create_festival(db_session, season_id=other_season.id, name="Other")
    inactive_festival = _create_festival(db_session, season_id=season.id, name="Dormant", active=False)
    gate = _create_location(db_session)
    inactive_gate = _create_location(db_session, name="Closed Gate", active=False)
    url = "/api/modules/module-2/plan-kar"

    def save(team_id: int, festival_id: int, location_id: int, season_id: int = season.id) -> int:
        payload = {
            "season_id": season_id,
            "team_id": team_id,
            "rows": [{"festival_id": festival_id, "afleverlocatie_id": location_id}],
        }
        return client.put(url, json=payload).status_code

    assert save(team.id, foreign_festival.id, gate.id) == 400  # festival of another season
    assert save(team.id, inactive_festival.id, gate.id) == 400  # inactive festival
    assert save(team.id, festival.id, inactive_gate.id) == 400  # inactive location
    assert save(team.id, festival.id, 9999) == 400  # unknown location
    assert save(inactive_team.id, festival.id, gate.id) == 400  # inactive team
    assert save(team.id, festival.id, gate.id, season_id=9999) == 404  # unknown season
    assert _record_count(db_session) == 0


def test_afleverlocatie_in_use_by_a_plan_cannot_be_deleted(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    team = _create_team(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    gate = _create_location(db_session)
    client.put(
        "/api/modules/module-2/plan-kar",
        json={"season_id": season.id, "team_id": team.id, "rows": [{"festival_id": festival.id, "afleverlocatie_id": gate.id}]},
    )

    response = client.delete(f"/api/modules/module-2/afleverlocaties/{gate.id}")

    assert response.status_code == 400


def test_afleverlocatie_active_flag_round_trips(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    gate = _create_location(db_session)
    payload = {
        "name": gate.name,
        "zone_id": gate.zone_id,
        "distributiepunt_id": gate.distributiepunt_id,
        "active": False,
    }

    updated = client.put(f"/api/modules/module-2/afleverlocaties/{gate.id}", json=payload)

    assert updated.status_code == 200
    assert updated.json()["active"] is False
