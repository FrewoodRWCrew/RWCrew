# These tests check KarTracker's landing dashboard ("KPI Overview"):
# aggregate KPI stats gated by plain module access (no specific screen
# permission), mirroring backend/tests/modules/module_3/test_dashboard.py.
# The movement windows are tested directly on build_dashboard_stats with a
# pinned "now", so they don't depend on the clock.

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_action import KarTrackerKarAction
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.product import Product
from app.db.models.season import Season
from app.db.models.team import Team
from app.modules.module_2.kartracker_dashboard import build_dashboard_stats
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import create_kartracker_module, create_user, grant_module_access, login

DASHBOARD_URL = "/api/modules/module-2/dashboard"


def _login_member(client: TestClient, db_session: Session) -> None:
    """A plain user with module access but no KarTracker role at all."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    login(client, "member@example.com")


def _create_status(db_session: Session, name: str) -> KarTrackerKarStatus:
    kar_status = KarTrackerKarStatus(name=name)
    db_session.add(kar_status)
    db_session.commit()
    return kar_status


def _create_team(db_session: Session, name: str, *, active: bool = True) -> Team:
    team = Team(name=name, active=active)
    db_session.add(team)
    db_session.commit()
    return team


def _create_kar(db_session: Session, kar_nummer: str, *, status_id: int, team_id: int | None = None) -> KarTrackerKar:
    product = db_session.scalar(select(Product)) or Product(name="Box")
    db_session.add(product)
    db_session.commit()
    kar = KarTrackerKar(kar_nummer=kar_nummer, status_id=status_id, transport_type_id=product.id, team_id=team_id)
    db_session.add(kar)
    db_session.commit()
    return kar


def _log_movement(db_session: Session, kar: KarTrackerKar, recorded_at: datetime) -> None:
    db_session.add(
        KarTrackerKarAction(
            kar_id=kar.id, status_id=kar.status_id, latitude=51.0, longitude=4.0, recorded_at=recorded_at
        )
    )
    db_session.commit()


def _create_season(db_session: Session, name: str) -> Season:
    season = Season(name=name)
    db_session.add(season)
    db_session.commit()
    return season


def _create_festival(
    db_session: Session, name: str, *, season_id: int, start: str, active: bool = True
) -> Festival:
    festival = Festival(
        name=name,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(start),
        season_id=season_id,
        active=active,
    )
    db_session.add(festival)
    db_session.commit()
    return festival


def _create_location(db_session: Session) -> KarTrackerAfleverlocatie:
    zone = KarTrackerZone(name="Zone A")
    distributiepunt = KarTrackerDistributiepunt(name="DP A")
    db_session.add_all([zone, distributiepunt])
    db_session.commit()
    location = KarTrackerAfleverlocatie(name="Poort 1", zone_id=zone.id, distributiepunt_id=distributiepunt.id)
    db_session.add(location)
    db_session.commit()
    return location


def _plan(db_session: Session, *, season: Season, festival: Festival, team: Team, location_id: int) -> None:
    db_session.add(
        KarTrackerKarAfleverlocatie(
            season_id=season.id, festival_id=festival.id, team_id=team.id, afleverlocatie_id=location_id
        )
    )
    db_session.commit()


def test_dashboard_requires_login(client: TestClient) -> None:
    assert client.get(DASHBOARD_URL).status_code == 401


def test_dashboard_requires_module_access(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    create_kartracker_module(db_session)
    create_user(db_session, email="outsider@example.com")
    login(client, "outsider@example.com")

    assert client.get(DASHBOARD_URL).status_code == 403


def test_dashboard_is_open_to_any_module_member_and_starts_empty(client: TestClient, db_session: Session) -> None:
    _login_member(client, db_session)

    response = client.get(DASHBOARD_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["total_karren"] == 0
    assert body["karren_with_team"] == 0
    assert body["karren_without_team"] == 0
    assert body["movements_last_7_days"] == 0
    assert body["status_breakdown"] == []
    assert body["team_breakdown"] == []
    assert len(body["movements_per_day"]) == 14
    assert all(item["count"] == 0 for item in body["movements_per_day"])
    # No season asked for: no Plan a kar figures.
    assert body["plan_kar_planned"] is None
    assert body["plan_kar_expected"] is None
    assert body["festival_plan_breakdown"] is None


def test_fleet_figures_count_teams_and_zero_fill_statuses(client: TestClient, db_session: Session) -> None:
    _login_member(client, db_session)
    in_stock = _create_status(db_session, "In magazijn")
    on_site = _create_status(db_session, "Op terrein")
    _create_status(db_session, "Defect")
    scouts = _create_team(db_session, "Scouts")
    chiro = _create_team(db_session, "Chiro")
    _create_team(db_session, "Empty Team")
    _create_kar(db_session, "K001", status_id=in_stock.id)
    _create_kar(db_session, "K002", status_id=on_site.id, team_id=scouts.id)
    _create_kar(db_session, "K003", status_id=on_site.id, team_id=scouts.id)
    _create_kar(db_session, "K004", status_id=on_site.id, team_id=chiro.id)

    body = client.get(DASHBOARD_URL).json()

    assert body["total_karren"] == 4
    assert body["karren_with_team"] == 3
    assert body["karren_without_team"] == 1
    assert body["status_breakdown"] == [
        {"status_name": "Defect", "count": 0},
        {"status_name": "In magazijn", "count": 1},
        {"status_name": "Op terrein", "count": 3},
    ]
    # Only teams that have a kar, ordered by name.
    assert body["team_breakdown"] == [
        {"team_name": "Chiro", "count": 1},
        {"team_name": "Scouts", "count": 2},
    ]


def test_movement_windows(db_session: Session) -> None:
    kar_status = _create_status(db_session, "Op terrein")
    kar = _create_kar(db_session, "K001", status_id=kar_status.id)
    now = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
    _log_movement(db_session, kar, now - timedelta(hours=1))  # today
    _log_movement(db_session, kar, now - timedelta(hours=2))  # today
    _log_movement(db_session, kar, now - timedelta(days=6))  # inside both windows
    _log_movement(db_session, kar, now - timedelta(days=8))  # chart only
    _log_movement(db_session, kar, now - timedelta(days=20))  # outside both

    stats = build_dashboard_stats(db_session, None, now=now)

    assert stats.movements_last_7_days == 3
    per_day = {item.day: item.count for item in stats.movements_per_day}
    assert len(stats.movements_per_day) == 14
    assert stats.movements_per_day[0].day == date(2026, 9, 14)
    assert stats.movements_per_day[-1].day == date(2026, 9, 27)
    assert per_day[date(2026, 9, 27)] == 2
    assert per_day[date(2026, 9, 21)] == 1
    assert per_day[date(2026, 9, 19)] == 1
    assert sum(per_day.values()) == 4


def test_plan_kar_coverage_for_a_season(client: TestClient, db_session: Session) -> None:
    _login_member(client, db_session)
    season = _create_season(db_session, "2026")
    other_season = _create_season(db_session, "2025")
    early = _create_festival(db_session, "Early Fest", season_id=season.id, start="2026-06-01")
    late = _create_festival(db_session, "Late Fest", season_id=season.id, start="2026-08-01")
    inactive_festival = _create_festival(
        db_session, "Cancelled Fest", season_id=season.id, start="2026-07-01", active=False
    )
    old_festival = _create_festival(db_session, "Old Fest", season_id=other_season.id, start="2025-07-01")
    scouts = _create_team(db_session, "Scouts")
    chiro = _create_team(db_session, "Chiro")
    retired = _create_team(db_session, "Retired", active=False)
    location = _create_location(db_session)
    _plan(db_session, season=season, festival=early, team=scouts, location_id=location.id)
    _plan(db_session, season=season, festival=early, team=chiro, location_id=location.id)
    _plan(db_session, season=season, festival=late, team=scouts, location_id=location.id)
    # None of these count: an inactive team, an inactive festival, another season.
    _plan(db_session, season=season, festival=late, team=retired, location_id=location.id)
    _plan(db_session, season=season, festival=inactive_festival, team=chiro, location_id=location.id)
    _plan(db_session, season=other_season, festival=old_festival, team=chiro, location_id=location.id)

    body = client.get(DASHBOARD_URL, params={"season_id": season.id}).json()

    assert body["season_id"] == season.id
    assert body["active_teams"] == 2
    assert body["plan_kar_planned"] == 3
    assert body["plan_kar_expected"] == 4
    assert body["festival_plan_breakdown"] == [
        {"festival_name": "Early Fest", "planned_teams": 2},
        {"festival_name": "Late Fest", "planned_teams": 1},
    ]


def test_unknown_season_is_404(client: TestClient, db_session: Session) -> None:
    _login_member(client, db_session)

    assert client.get(DASHBOARD_URL, params={"season_id": 999}).status_code == 404
