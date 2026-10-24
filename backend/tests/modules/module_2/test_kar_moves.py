# Tests for the "Verplaatsingen tussen festivals" screen (module_2/kar_moves_service.py):
# for festival A -> B, the karren whose team's planned location changes,
# grouped per pick-up location in tour order, and its PDF.

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)
from tests.modules.module_2.test_initial_delivery import (
    _add,
    _kar,
    _location,
    _login_admin,
    _plan,
    _png,
    _season_with_festivals,
)

URL = "/api/modules/module-2/kar-moves"
PRINT_URL = "/api/modules/module-2/kar-moves/print"


def _params(season, first: Festival, second: Festival) -> dict:
    return {"season_id": season.id, "from_festival_id": first.id, "to_festival_id": second.id}


def test_only_karren_whose_location_changes_are_listed_per_pick_up_location(
    client: TestClient, db_session: Session
) -> None:
    _login_admin(client, db_session)
    season, first, second = _season_with_festivals(db_session)
    poort = _location(db_session, "Poort", 2, "DP")
    backstage = _location(db_session, "Backstage", 1, "DP")
    los = _location(db_session, "Los", None, "DP")
    later = _location(db_session, "Later", 3, "DP")

    scouts, chiro, ksa, kljb, vvksm = (Team(name=name) for name in ("Scouts", "Chiro", "KSA", "KLJB", "VVKSM"))
    _add(db_session, scouts, chiro, ksa, kljb, vvksm)
    # Scouts (no picks = every festival) move Poort -> Later.
    _plan(db_session, season, first, scouts, poort)
    _plan(db_session, season, second, scouts, later)
    # Chiro picked both festivals and moves Los -> Backstage.
    _add(
        db_session,
        TeamFestival(season_id=season.id, team_id=chiro.id, festival_id=first.id),
        TeamFestival(season_id=season.id, team_id=chiro.id, festival_id=second.id),
    )
    _plan(db_session, season, first, chiro, los)
    _plan(db_session, season, second, chiro, backstage)
    # KSA stays at the same location -> not listed.
    _plan(db_session, season, first, ksa, poort)
    _plan(db_session, season, second, ksa, poort)
    # KLJB only picked the second festival -> its old plan at the first doesn't count.
    _add(db_session, TeamFestival(season_id=season.id, team_id=kljb.id, festival_id=second.id))
    _plan(db_session, season, first, kljb, poort)
    _plan(db_session, season, second, kljb, backstage)
    # VVKSM has nothing planned at the second festival -> not listed.
    _plan(db_session, season, first, vvksm, poort)
    _add(db_session, KarTrackerLeverdatum(festival_id=second.id, delivery_date=date(2026, 7, 30)))

    _kar(db_session, "K2", scouts)
    _kar(db_session, "K1", scouts)
    _kar(db_session, "K3", chiro)
    _kar(db_session, "K4", ksa)
    _kar(db_session, "K5", kljb)
    _kar(db_session, "K6", vvksm)

    response = client.get(URL, params=_params(season, first, second))

    assert response.status_code == 200
    body = response.json()
    # Pick-up locations in tour order (no position last), karren by number, with their destination.
    assert [
        (group["name"], [(kar["kar_nummer"], kar["to_location"]["name"]) for kar in group["karren"]])
        for group in body["locations"]
    ] == [
        ("Poort", [("K1", "Later"), ("K2", "Later")]),
        ("Los", [("K3", "Backstage")]),
    ]
    assert body["total"] == 3
    assert body["to_delivery_date"] == "2026-07-30"
    assert [festival["name"] for festival in body["festivals"]] == ["Eerste", "Tweede"]

    # The other way round the same teams move back.
    back = client.get(URL, params=_params(season, second, first)).json()
    assert [group["name"] for group in back["locations"]] == ["Backstage", "Later"]


def test_without_a_pair_only_the_festivals_are_returned(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, _first, _second = _season_with_festivals(db_session)

    body = client.get(URL, params={"season_id": season.id}).json()

    assert [festival["name"] for festival in body["festivals"]] == ["Eerste", "Tweede"]
    assert body["locations"] == [] and body["total"] == 0


def test_rejects_the_same_or_an_unknown_festival_and_needs_the_screen_right(
    client: TestClient, db_session: Session
) -> None:
    _login_admin(client, db_session)
    season, first, _second = _season_with_festivals(db_session)
    assert client.get(URL, params=_params(season, first, first)).status_code == 400
    assert (
        client.get(URL, params={"season_id": season.id, "from_festival_id": first.id, "to_festival_id": 999}).status_code
        == 404
    )
    assert client.get(URL, params={"season_id": 999}).status_code == 404

    client.cookies.clear()
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="user@example.com")
    grant_module_access(db_session, user, module)
    # A right on the initial delivery screen doesn't open this one.
    role = create_role_with_permissions(
        db_session, name="Planner", screen_key="kartracker.initieleleverplanning", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "user@example.com")
    assert client.get(URL, params={"season_id": season.id}).status_code == 403


def _moves_with_coordinates(db_session: Session) -> tuple[dict, list[int]]:
    """Two teams moving between three locations (one without a position) with
    coordinates inside a ground plan; returns the print payload base and the kar ids.
    """
    season, first, second = _season_with_festivals(db_session)
    poort = _location(db_session, "Poort", 1, "DP")
    backstage = _location(db_session, "Backstage", 2, "DP")
    los = _location(db_session, "Los", None, "DP")
    for location, (lat, lng) in ((poort, (50.951, 4.651)), (backstage, (50.953, 4.655)), (los, (50.952, 4.653))):
        location.latitude, location.longitude = lat, lng
    dp = db_session.scalar(select(KarTrackerDistributiepunt))
    dp.latitude, dp.longitude = 50.950, 4.650
    db_session.add(
        KarTrackerGroundplan(
            name="Terrein",
            image_data=_png(),
            image_content_type="image/png",
            sw_latitude=50.948,
            sw_longitude=4.645,
            ne_latitude=50.956,
            ne_longitude=4.660,
        )
    )
    db_session.commit()

    scouts, chiro = Team(name="Scouts"), Team(name="Chiro")
    _add(db_session, scouts, chiro)
    _plan(db_session, season, first, scouts, poort)
    _plan(db_session, season, second, scouts, backstage)
    _plan(db_session, season, first, chiro, backstage)
    _plan(db_session, season, second, chiro, los)
    _kar(db_session, "K1", scouts)
    _kar(db_session, "K2", scouts)
    _kar(db_session, "K3", chiro)
    kar_ids = [kar.id for kar in db_session.scalars(select(KarTrackerKar).order_by(KarTrackerKar.kar_nummer))]
    return _params(season, first, second), kar_ids


def test_print_returns_a_landscape_pdf_with_and_without_the_map(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    base, kar_ids = _moves_with_coordinates(db_session)

    for include_map in (False, True):
        response = client.post(PRINT_URL, json={**base, "kar_ids": kar_ids, "include_map": include_map, "locale": "en"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        # Landscape A4 = 297 x 210 mm = 841.89 x 595.28 pt.
        assert b"/MediaBox [0 0 841.89 595.28]" in response.content
        assert response.content.count(b"/Type /Page\n") == (2 if include_map else 1)

    # Without a ground plan the map page is still drawn.
    db_session.query(KarTrackerGroundplan).delete()
    db_session.commit()
    assert client.post(PRINT_URL, json={**base, "kar_ids": kar_ids[:1], "include_map": True}).status_code == 200


def test_print_needs_known_karren_and_two_different_festivals(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    base, _kar_ids = _moves_with_coordinates(db_session)
    assert client.post(PRINT_URL, json={**base, "kar_ids": [9999]}).status_code == 404
    same = {**base, "to_festival_id": base["from_festival_id"], "kar_ids": [1]}
    assert client.post(PRINT_URL, json=same).status_code == 400
    assert client.post(PRINT_URL, json={**base, "kar_ids": []}).status_code == 422
