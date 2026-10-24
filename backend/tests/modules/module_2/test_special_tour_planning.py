# Tests for the "Speciale levertoeren-planning" screen
# (module_2/special_tour_planning_service.py): for a festival + tours, the
# karren of the tours' teams at their planned location for that festival,
# grouped per distributiepunt / location in tour order, and its PDF.

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_speciale_levertoer import KarTrackerSpecialeLevertoer
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival
from app.db.models.team_speciale_levertoer import TeamSpecialeLevertoer
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

URL = "/api/modules/module-2/special-tour-planning"
PRINT_URL = f"{URL}/print"


def _tour(db_session: Session, name: str, *teams: Team, active: bool = True) -> KarTrackerSpecialeLevertoer:
    """A tour passing by the given teams."""
    tour = KarTrackerSpecialeLevertoer(name=name, active=active)
    _add(db_session, tour)
    _add(db_session, *(TeamSpecialeLevertoer(team_id=team.id, levertoer_id=tour.id) for team in teams))
    return tour


def test_without_festival_or_tours_only_the_filters_come_back(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, first, second = _season_with_festivals(db_session)
    _tour(db_session, "Wastoer")
    _tour(db_session, "Oud", active=False)
    _tour(db_session, "Ijsblokken")

    body = client.get(URL, params={"season_id": season.id, "festival_id": first.id}).json()

    assert [festival["name"] for festival in body["festivals"]] == ["Eerste", "Tweede"]
    # Only active tours are offered, by name.
    assert [tour["name"] for tour in body["tours"]] == ["Ijsblokken", "Wastoer"]
    assert body["locations"] == []
    assert body["total"] == 0


def test_karren_of_the_tours_teams_at_their_location_for_the_festival(
    client: TestClient, db_session: Session
) -> None:
    _login_admin(client, db_session)
    season, first, second = _season_with_festivals(db_session)
    poort = _location(db_session, "Poort", 2, "DP Noord")
    # Not in the delivery tour (no position) -> the last stop.
    backstage = _location(db_session, "Backstage", None, "DP Zuid")
    later = _location(db_session, "Later", 3, "DP Noord")

    scouts, chiro, ksa, klj, other = (Team(name=name) for name in ("Scouts", "Chiro", "KSA", "KLJ", "Other"))
    _add(db_session, scouts, chiro, ksa, klj, other)
    wastoer = _tour(db_session, "Wastoer", scouts, chiro, klj)
    ijs = _tour(db_session, "Ijsblokken", scouts, ksa)
    _tour(db_session, "Niet gekozen", other)

    # Scouts picked nothing -> plays every festival.
    _plan(db_session, season, second, scouts, poort)
    _plan(db_session, season, first, scouts, later)
    _plan(db_session, season, second, chiro, backstage)
    _plan(db_session, season, second, ksa, later)
    _plan(db_session, season, second, other, poort)
    # KLJ only takes part in the first festival -> left out at the second.
    _add(db_session, TeamFestival(season_id=season.id, team_id=klj.id, festival_id=first.id))
    _plan(db_session, season, second, klj, poort)
    _add(db_session, KarTrackerLeverdatum(festival_id=second.id, delivery_date=date(2026, 7, 30)))

    _kar(db_session, "K2", scouts)
    _kar(db_session, "K1", scouts)
    _kar(db_session, "K3", chiro)
    _kar(db_session, "K4", ksa)
    _kar(db_session, "K5", klj)
    _kar(db_session, "K6", other)

    response = client.get(
        URL, params={"season_id": season.id, "festival_id": second.id, "tour_ids": [wastoer.id, ijs.id]}
    )

    assert response.status_code == 200
    body = response.json()
    # The stops in tour order (no position last), numbered 1..n, no distributiepunten.
    assert [(loc["stop"], loc["name"], [kar["kar_nummer"] for kar in loc["karren"]]) for loc in body["locations"]] == [
        (1, "Poort", ["K1", "K2"]),
        (2, "Later", ["K4"]),
        (3, "Backstage", ["K3"]),
    ]
    assert "distributiepunten" not in body
    poort_karren = body["locations"][0]["karren"]
    # A kar on both selected tours is listed once, with both names.
    assert poort_karren[0]["tour_names"] == ["Ijsblokken", "Wastoer"]
    assert poort_karren[0]["festival_name"] == "Tweede"
    assert poort_karren[0]["delivery_date"] == "2026-07-30"
    assert body["delivery_date"] == "2026-07-30"
    assert body["total"] == 4

    # Only one tour selected -> only its teams.
    body = client.get(URL, params={"season_id": season.id, "festival_id": second.id, "tour_ids": [ijs.id]}).json()
    assert [kar["kar_nummer"] for loc in body["locations"] for kar in loc["karren"]] == [
        "K1", "K2", "K4"
    ]


def test_unknown_festival_tour_season_and_screen_right(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, first, _second = _season_with_festivals(db_session)
    tour = _tour(db_session, "Wastoer")

    assert client.get(URL, params={"season_id": season.id, "festival_id": 9999, "tour_ids": [tour.id]}).status_code == 404
    assert client.get(URL, params={"season_id": season.id, "festival_id": first.id, "tour_ids": [9999]}).status_code == 404
    assert client.get(URL, params={"season_id": 9999}).status_code == 404

    client.cookies.clear()
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="user@example.com")
    grant_module_access(db_session, user, module)
    # A right on another screen doesn't open this one.
    role = create_role_with_permissions(
        db_session, name="Planner", screen_key="kartracker.specialelevertoeren", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "user@example.com")
    assert client.get(URL, params={"season_id": season.id}).status_code == 403


def test_print_returns_a_landscape_pdf_with_and_without_the_map(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, first, _second = _season_with_festivals(db_session)
    poort = _location(db_session, "Poort", 1, "DP Noord")
    backstage = _location(db_session, "Backstage", 2, "DP Noord")
    for location, (lat, lng) in ((poort, (50.951, 4.651)), (backstage, (50.953, 4.655))):
        location.latitude, location.longitude = lat, lng
    dp = db_session.scalar(select(KarTrackerDistributiepunt).where(KarTrackerDistributiepunt.name == "DP Noord"))
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
    tour = _tour(db_session, "Wastoer", scouts, chiro)
    _plan(db_session, season, first, scouts, poort)
    _plan(db_session, season, first, chiro, backstage)
    _kar(db_session, "K1", scouts)
    _kar(db_session, "K2", chiro)
    kar_ids = [kar.id for kar in db_session.scalars(select(KarTrackerKar).order_by(KarTrackerKar.kar_nummer))]

    for include_map in (False, True):
        response = client.post(
            PRINT_URL,
            json={
                "season_id": season.id,
                "festival_id": first.id,
                "tour_ids": [tour.id],
                "kar_ids": kar_ids,
                "include_map": include_map,
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"/MediaBox [0 0 841.89 595.28]" in response.content
        assert response.content.count(b"/Type /Page\n") == (2 if include_map else 1)

    # Karren that aren't in the planning -> nothing to print.
    response = client.post(
        PRINT_URL, json={"season_id": season.id, "festival_id": first.id, "tour_ids": [tour.id], "kar_ids": [9999]}
    )
    assert response.status_code == 404
