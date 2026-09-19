# Tests for the "Delivery Dates" screen (see module_2/router.py's /leverdata
# endpoints): per active festival of a season, one delivery date and one
# pick-up date, saved as an upsert on the festival into
# Festivals_leverdatum (at most one row per festival).

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.season import Season
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)

URL = "/api/modules/module-2/leverdata"


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


def _record_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(KarTrackerLeverdatum)) or 0


def test_user_without_leverdata_permission_cannot_use_it(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    # Permission on another screen must not open this one.
    role = create_role_with_permissions(db_session, name="Map Viewer", screen_key="kartracker.karmap", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    assert client.get(URL, params={"season_id": 1}).status_code == 403
    assert client.put(URL, json={"season_id": 1, "rows": []}).status_code == 403


def test_view_only_user_can_read_but_not_save(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Viewer", screen_key="kartracker.leverdata", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    season = _create_season(db_session)
    login(client, "member@example.com")

    assert client.get(URL, params={"season_id": season.id}).status_code == 200
    assert client.put(URL, json={"season_id": season.id, "rows": []}).status_code == 403


def test_lists_only_active_festivals_of_the_season_without_dates(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session, name="2026")
    other_season = _create_season(db_session, name="2027")
    _create_festival(db_session, season_id=season.id, name="Beta Fest", start_date="2026-08-01")
    _create_festival(db_session, season_id=season.id, name="Alpha Fest", start_date="2026-07-01")
    _create_festival(db_session, season_id=season.id, name="Dormant Fest", active=False)
    _create_festival(db_session, season_id=other_season.id, name="Next Year Fest")

    response = client.get(URL, params={"season_id": season.id})

    assert response.status_code == 200
    rows = response.json()["rows"]
    # Ordered by start date, nothing saved yet.
    assert [row["festival_name"] for row in rows] == ["Alpha Fest", "Beta Fest"]
    assert all(row["delivery_date"] is None and row["pickup_date"] is None for row in rows)


def test_unknown_season_is_404(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)

    assert client.get(URL, params={"season_id": 999}).status_code == 404
    assert client.put(URL, json={"season_id": 999, "rows": []}).status_code == 404


def test_save_inserts_then_second_save_updates_without_duplicating(
    client: TestClient, db_session: Session
) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)

    first = client.put(
        URL,
        json={
            "season_id": season.id,
            "rows": [{"festival_id": festival.id, "delivery_date": "2026-06-28", "pickup_date": "2026-07-05"}],
        },
    )
    assert first.status_code == 200
    assert first.json()["rows"][0]["delivery_date"] == "2026-06-28"
    assert first.json()["rows"][0]["pickup_date"] == "2026-07-05"
    assert _record_count(db_session) == 1

    # Saving again changes the same row — still one line for the festival.
    second = client.put(
        URL,
        json={
            "season_id": season.id,
            "rows": [{"festival_id": festival.id, "delivery_date": "2026-06-29", "pickup_date": "2026-07-06"}],
        },
    )
    assert second.status_code == 200
    assert second.json()["rows"][0]["delivery_date"] == "2026-06-29"
    assert _record_count(db_session) == 1


def test_save_allows_only_one_of_the_two_dates(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)

    response = client.put(
        URL,
        json={"season_id": season.id, "rows": [{"festival_id": festival.id, "delivery_date": "2026-06-28"}]},
    )

    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert row["delivery_date"] == "2026-06-28"
    assert row["pickup_date"] is None


def test_clearing_both_dates_removes_the_record(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    client.put(
        URL,
        json={
            "season_id": season.id,
            "rows": [{"festival_id": festival.id, "delivery_date": "2026-06-28", "pickup_date": "2026-07-05"}],
        },
    )
    assert _record_count(db_session) == 1

    response = client.put(URL, json={"season_id": season.id, "rows": [{"festival_id": festival.id}]})

    assert response.status_code == 200
    assert response.json()["rows"][0]["delivery_date"] is None
    assert _record_count(db_session) == 0


def test_pickup_before_delivery_is_rejected(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)

    response = client.put(
        URL,
        json={
            "season_id": season.id,
            "rows": [{"festival_id": festival.id, "delivery_date": "2026-07-05", "pickup_date": "2026-06-28"}],
        },
    )

    assert response.status_code == 400
    assert _record_count(db_session) == 0


def test_invalid_festivals_are_rejected(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session, name="2026")
    other_season = _create_season(db_session, name="2027")
    active = _create_festival(db_session, season_id=season.id, name="Active Fest")
    inactive = _create_festival(db_session, season_id=season.id, name="Dormant Fest", active=False)
    elsewhere = _create_festival(db_session, season_id=other_season.id, name="Next Year Fest")
    dates = {"delivery_date": "2026-06-28"}

    # Inactive, from another season, or unknown: all rejected.
    for bad_id in (inactive.id, elsewhere.id, 999):
        response = client.put(URL, json={"season_id": season.id, "rows": [{"festival_id": bad_id, **dates}]})
        assert response.status_code == 400

    # The same festival twice in one save is rejected too.
    duplicated = [{"festival_id": active.id, **dates}, {"festival_id": active.id, **dates}]
    assert client.put(URL, json={"season_id": season.id, "rows": duplicated}).status_code == 400
    assert _record_count(db_session) == 0


def test_deleting_a_festival_removes_its_dates(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season = _create_season(db_session)
    festival = _create_festival(db_session, season_id=season.id)
    client.put(
        URL,
        json={"season_id": season.id, "rows": [{"festival_id": festival.id, "delivery_date": "2026-06-28"}]},
    )
    assert _record_count(db_session) == 1

    db_session.delete(festival)
    db_session.commit()

    assert _record_count(db_session) == 0
