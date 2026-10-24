# Tests for the "Initiële leverplanning" screen (module_2/initial_delivery_service.py):
# per distributiepunt and delivery location, in tour order, the karren
# delivered there at their team's first festival of the season.

import io
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from PIL import Image
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.kartracker_zone import KarTrackerZone
from app.db.models.product import Product
from app.db.models.season import Season
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

URL = "/api/modules/module-2/initial-delivery"


def _login_admin(client: TestClient, db_session: Session) -> None:
    """Set up the module and log in as a super admin with module access."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")


def _add(db_session: Session, *rows: object) -> None:
    db_session.add_all(rows)
    db_session.commit()


def _season_with_festivals(db_session: Session) -> tuple[Season, Festival, Festival]:
    """A season with two active festivals: "Eerste" (July) and "Tweede" (August)."""
    season = Season(name="2026")
    _add(db_session, season)
    first = Festival(
        name="Eerste", start_date=date(2026, 7, 1), end_date=date(2026, 7, 3), season_id=season.id
    )
    second = Festival(
        name="Tweede", start_date=date(2026, 8, 1), end_date=date(2026, 8, 3), season_id=season.id
    )
    _add(db_session, first, second)
    return season, first, second


def _location(db_session: Session, name: str, positie: int | None, distributiepunt: str) -> KarTrackerAfleverlocatie:
    """A delivery location in one zone, under the named distributiepunt."""
    zone = db_session.scalar(select(KarTrackerZone)) or KarTrackerZone(name="Zone A")
    dp = db_session.scalar(
        select(KarTrackerDistributiepunt).where(KarTrackerDistributiepunt.name == distributiepunt)
    ) or KarTrackerDistributiepunt(name=distributiepunt)
    _add(db_session, zone, dp)
    location = KarTrackerAfleverlocatie(
        name=name, zone_id=zone.id, distributiepunt_id=dp.id, terrein_positie=positie
    )
    _add(db_session, location)
    return location


def _kar(db_session: Session, kar_nummer: str, team: Team | None) -> None:
    status = db_session.scalar(select(KarTrackerKarStatus)) or KarTrackerKarStatus(name="In Magazijn")
    product = db_session.scalar(select(Product)) or Product(name="Box")
    _add(db_session, status, product)
    _add(
        db_session,
        KarTrackerKar(
            kar_nummer=kar_nummer,
            status_id=status.id,
            transport_type_id=product.id,
            team_id=team.id if team else None,
        ),
    )


def _plan(db_session: Session, season: Season, festival: Festival, team: Team, location: KarTrackerAfleverlocatie) -> None:
    _add(
        db_session,
        KarTrackerKarAfleverlocatie(
            season_id=season.id, festival_id=festival.id, team_id=team.id, afleverlocatie_id=location.id
        ),
    )


def test_karren_go_to_their_team_first_festival_location_in_tour_order(
    client: TestClient, db_session: Session
) -> None:
    _login_admin(client, db_session)
    season, first, second = _season_with_festivals(db_session)
    poort = _location(db_session, "Poort", 2, "DP Noord")
    backstage = _location(db_session, "Backstage", 1, "DP Zuid")
    los = _location(db_session, "Los", None, "DP Noord")
    later = _location(db_session, "Later", 3, "DP Noord")

    scouts = Team(name="Scouts")
    chiro = Team(name="Chiro")
    ksa = Team(name="KSA")
    _add(db_session, scouts, chiro, ksa)
    # Scouts picked nothing in Altsien Select -> the season's first festival.
    _plan(db_session, season, first, scouts, poort)
    _plan(db_session, season, second, scouts, later)
    # Chiro only takes part in the second festival -> that one is its first.
    _add(db_session, TeamFestival(season_id=season.id, team_id=chiro.id, festival_id=second.id))
    _plan(db_session, season, first, chiro, later)
    _plan(db_session, season, second, chiro, backstage)
    # KSA has a location without a tour position.
    _plan(db_session, season, first, ksa, los)
    _add(db_session, KarTrackerLeverdatum(festival_id=first.id, delivery_date=date(2026, 6, 28)))

    _kar(db_session, "K2", scouts)
    _kar(db_session, "K1", scouts)
    _kar(db_session, "K3", chiro)
    _kar(db_session, "K4", ksa)
    _kar(db_session, "K5", None)  # no team -> not delivered

    response = client.get(URL, params={"season_id": season.id})

    assert response.status_code == 200
    body = response.json()
    # Per distributiepunt (ordered by its first location in the tour), its
    # locations in tour order (no position last), each with its karren.
    assert [
        (dp["name"], dp["count"], [(loc["name"], [kar["kar_nummer"] for kar in loc["karren"]]) for loc in dp["locations"]])
        for dp in body["distributiepunten"]
    ] == [
        ("DP Zuid", 1, [("Backstage", ["K3"])]),
        ("DP Noord", 3, [("Poort", ["K1", "K2"]), ("Los", ["K4"])]),
    ]
    zuid, noord = body["distributiepunten"]
    assert zuid["locations"][0]["karren"][0]["festival_name"] == "Tweede"
    assert noord["locations"][0]["karren"][0]["delivery_date"] == "2026-06-28"
    assert body["total"] == 4


def test_team_without_plan_for_its_first_festival_is_left_out(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, _first, second = _season_with_festivals(db_session)
    location = _location(db_session, "Poort", 1, "DP")
    team = Team(name="Scouts")
    _add(db_session, team)
    # Only the second festival is planned; the team's first one isn't.
    _plan(db_session, season, second, team, location)
    _kar(db_session, "K1", team)

    body = client.get(URL, params={"season_id": season.id}).json()

    assert body == {"distributiepunten": [], "total": 0}


def test_needs_the_screen_right_and_a_known_season(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="user@example.com")
    grant_module_access(db_session, user, module)
    # A right on another screen doesn't open this one.
    role = create_role_with_permissions(
        db_session, name="Planner", screen_key="kartracker.leveringsvolgorde", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "user@example.com")
    assert client.get(URL, params={"season_id": 1}).status_code == 403

    client.cookies.clear()
    _login_admin(client, db_session)
    assert client.get(URL, params={"season_id": 999}).status_code == 404


PRINT_URL = "/api/modules/module-2/initial-delivery/print"


def _png(width: int = 40, height: int = 30) -> bytes:
    """A small ground-plan image, with transparency like many real plans."""
    output = io.BytesIO()
    Image.new("RGBA", (width, height), (200, 220, 255, 128)).save(output, format="PNG")
    return output.getvalue()


def _planning_with_coordinates(db_session: Session) -> tuple[Season, list[int]]:
    """Two positioned locations + one without a position, with coordinates
    inside a ground plan; returns the season and the kar ids (K1..K3).
    """
    season, first, _second = _season_with_festivals(db_session)
    poort = _location(db_session, "Poort", 1, "DP Noord")
    backstage = _location(db_session, "Backstage", 2, "DP Noord")
    los = _location(db_session, "Los", None, "DP Zuid")
    for location, (lat, lng) in ((poort, (50.951, 4.651)), (backstage, (50.953, 4.655)), (los, (50.952, 4.653))):
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

    teams = [Team(name=name) for name in ("Scouts", "Chiro", "KSA")]
    _add(db_session, *teams)
    for team, location in zip(teams, (poort, backstage, los)):
        _plan(db_session, season, first, team, location)
    for number, team in enumerate(teams, start=1):
        _kar(db_session, f"K{number}", team)
    kar_ids = [kar.id for kar in db_session.scalars(select(KarTrackerKar).order_by(KarTrackerKar.kar_nummer))]
    return season, kar_ids


def test_print_returns_a_landscape_pdf_with_and_without_the_map(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, kar_ids = _planning_with_coordinates(db_session)

    for include_map in (False, True):
        response = client.post(
            PRINT_URL, json={"season_id": season.id, "kar_ids": kar_ids, "include_map": include_map, "locale": "nl"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")
        # Landscape A4 = 297 x 210 mm = 841.89 x 595.28 pt.
        assert b"/MediaBox [0 0 841.89 595.28]" in response.content
        # One page of tables (+ the map page when asked for).
        assert response.content.count(b"/Type /Page\n") == (2 if include_map else 1)


def test_print_without_a_ground_plan_still_draws_the_map(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, kar_ids = _planning_with_coordinates(db_session)
    db_session.query(KarTrackerGroundplan).delete()
    db_session.commit()

    response = client.post(PRINT_URL, json={"season_id": season.id, "kar_ids": kar_ids[:1], "include_map": True})

    assert response.status_code == 200


def test_print_needs_known_karren_season_and_the_screen_right(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    season, _kar_ids = _planning_with_coordinates(db_session)
    assert client.post(PRINT_URL, json={"season_id": season.id, "kar_ids": [9999]}).status_code == 404
    assert client.post(PRINT_URL, json={"season_id": 9999, "kar_ids": [1]}).status_code == 404
    assert client.post(PRINT_URL, json={"season_id": season.id, "kar_ids": []}).status_code == 422

    client.cookies.clear()
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="user@example.com")
    grant_module_access(db_session, user, module)
    login(client, "user@example.com")
    assert client.post(PRINT_URL, json={"season_id": season.id, "kar_ids": [1]}).status_code == 403
