# Tests for the phone's KarScan (/api/mobile/v1/module-2): scan a kar's QR
# code (its kar number), log the kar's new status + GPS location. The key
# rules: rights are exactly the web role's rights on "kartracker.actions",
# a logged movement is identical to one logged on the web, and deleting a
# movement doesn't exist on the phone.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_action import KarTrackerKarAction
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.product import Product
from app.db.models.season import Season
from app.db.models.team import Team
from app.modules.module_2.screens import sync_screens
from tests.mobile.helpers import bearer, create_user, get_or_create_module, grant_access
from tests.modules.module_2.conftest import create_role_with_permissions

BASE = "/api/mobile/v1/module-2"


def _user_with_rights(db: Session, email: str, screen_key: str = "kartracker.actions", **rights: bool) -> None:
    """A user with module-2 access and a role with the given rights on one
    KarTracker screen ("Manuele kar beweging" unless told otherwise).
    """
    sync_screens(db)
    user = create_user(db, email)
    grant_access(db, user, "module-2")
    role = create_role_with_permissions(db, name=f"role-for-{email}", screen_key=screen_key, **rights)
    db.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db.commit()


def _create_status(db: Session, name: str) -> KarTrackerKarStatus:
    kar_status = KarTrackerKarStatus(name=name)
    db.add(kar_status)
    db.commit()
    db.refresh(kar_status)
    return kar_status


def _create_team(db: Session, name: str = "Scouts Wezemaal") -> Team:
    team = Team(name=name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def _create_kar(db: Session, kar_nummer: str, status_id: int, team_id: int | None = None) -> KarTrackerKar:
    product = db.scalar(select(Product))
    if product is None:
        product = Product(name="Box")
        db.add(product)
        db.commit()
    kar = KarTrackerKar(kar_nummer=kar_nummer, status_id=status_id, transport_type_id=product.id, team_id=team_id)
    db.add(kar)
    db.commit()
    db.refresh(kar)
    return kar


def _movement(kar_id: int, status_id: int) -> dict:
    return {"kar_id": kar_id, "status_id": status_id, "latitude": 50.97, "longitude": 4.68}


# --- Tile & permissions ----------------------------------------------------


def test_kartracker_tile_appears_on_the_phone(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)

    response = client.get("/api/mobile/v1/modules", headers=bearer(client, "a@example.com"))

    assert [module["key"] for module in response.json()] == ["module-2"]


def test_permissions_need_module_access(client: TestClient, db_session: Session) -> None:
    create_user(db_session, "a@example.com")
    get_or_create_module(db_session, "module-2")

    assert client.get(f"{BASE}/permissions", headers=bearer(client, "a@example.com")).status_code == 403


def test_permissions_reflect_the_web_role(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)

    response = client.get(f"{BASE}/permissions", headers=bearer(client, "a@example.com"))

    assert response.json() == {
        "can_view_actions": True,
        "can_create_actions": False,
        "can_view_karplanning": False,
        "can_view_karmap": False,
    }


# --- Scanning a kar ----------------------------------------------------------


def test_scan_finds_the_kar_with_its_team_and_status(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")
    team = _create_team(db_session)
    kar = _create_kar(db_session, "B001", magazijn.id, team.id)

    response = client.get(f"{BASE}/karren/by-nummer/B001", headers=bearer(client, "a@example.com"))

    assert response.status_code == 200
    body = response.json()
    assert body["kar"] == {
        "id": kar.id,
        "kar_nummer": "B001",
        "team_id": team.id,
        "team_name": "Scouts Wezemaal",
        "status_id": magazijn.id,
    }
    assert body["recent_actions"] == []


def test_scan_ignores_case_and_surrounding_spaces(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")
    _create_kar(db_session, "B001", magazijn.id)

    response = client.get(f"{BASE}/karren/by-nummer/%20b001%20", headers=bearer(client, "a@example.com"))

    assert response.status_code == 200
    assert response.json()["kar"]["kar_nummer"] == "B001"


def test_scanning_an_unknown_kar_returns_404(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)

    response = client.get(f"{BASE}/karren/by-nummer/X999", headers=bearer(client, "a@example.com"))

    assert response.status_code == 404


def test_scanning_needs_view_rights(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_create=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")
    _create_kar(db_session, "B001", magazijn.id)
    headers = bearer(client, "a@example.com")

    assert client.get(f"{BASE}/karren/by-nummer/B001", headers=headers).status_code == 403
    assert client.get(f"{BASE}/kar-statuses", headers=headers).status_code == 403


def test_scan_shows_the_last_five_movements_newest_first(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True, can_create=True)
    statuses = [_create_status(db_session, f"Status {index}") for index in range(7)]
    kar = _create_kar(db_session, "B001", statuses[0].id)
    headers = bearer(client, "a@example.com")
    for kar_status in statuses:
        assert client.post(f"{BASE}/kar-actions", json=_movement(kar.id, kar_status.id), headers=headers).status_code == 201

    recent = client.get(f"{BASE}/karren/by-nummer/B001", headers=headers).json()["recent_actions"]

    assert [action["status_name"] for action in recent] == ["Status 6", "Status 5", "Status 4", "Status 3", "Status 2"]


# --- Logging a movement ------------------------------------------------------


def test_kar_statuses_are_listed_by_name(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)
    _create_status(db_session, "Geleverd")
    _create_status(db_session, "Afgehaald")

    response = client.get(f"{BASE}/kar-statuses", headers=bearer(client, "a@example.com"))

    assert [kar_status["name"] for kar_status in response.json()] == ["Afgehaald", "Geleverd"]


def test_logging_a_movement_matches_the_web(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True, can_create=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")
    geleverd = _create_status(db_session, "Geleverd")
    team = _create_team(db_session)
    kar = _create_kar(db_session, "B001", magazijn.id, team.id)

    response = client.post(
        f"{BASE}/kar-actions", json=_movement(kar.id, geleverd.id), headers=bearer(client, "a@example.com")
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["kar_nummer"], body["status_name"], body["team_name"], body["user_name"]) == (
        "B001",
        "Geleverd",
        "Scouts Wezemaal",
        "a@example.com",
    )
    # The movement is logged, and the kar's own latest state follows it.
    db_session.expire_all()
    assert db_session.scalar(select(KarTrackerKarAction)).team_id == team.id
    updated_kar = db_session.get(KarTrackerKar, kar.id)
    assert (updated_kar.status_id, updated_kar.last_latitude, updated_kar.last_longitude) == (geleverd.id, 50.97, 4.68)


def test_logging_needs_create_rights(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")
    kar = _create_kar(db_session, "B001", magazijn.id)

    response = client.post(
        f"{BASE}/kar-actions", json=_movement(kar.id, magazijn.id), headers=bearer(client, "a@example.com")
    )

    assert response.status_code == 403


def test_logging_an_unknown_kar_returns_404(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", can_view=True, can_create=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")

    response = client.post(
        f"{BASE}/kar-actions", json=_movement(9999, magazijn.id), headers=bearer(client, "a@example.com")
    )

    assert response.status_code == 404


# --- Kar Planning --------------------------------------------------------------


def _create_season(db: Session, name: str, *, periode_open: bool) -> Season:
    season = Season(name=name, periode_open=periode_open)
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


def test_permissions_include_planning_and_map(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", screen_key="kartracker.karmap", can_view=True)

    body = client.get(f"{BASE}/permissions", headers=bearer(client, "a@example.com")).json()

    assert (body["can_view_actions"], body["can_view_karplanning"], body["can_view_karmap"]) == (False, False, True)


def test_seasons_lists_only_open_seasons_newest_first(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", screen_key="kartracker.karplanning", can_view=True)
    _create_season(db_session, "2025", periode_open=True)
    _create_season(db_session, "2026", periode_open=True)
    _create_season(db_session, "2024", periode_open=False)

    response = client.get(f"{BASE}/seasons", headers=bearer(client, "a@example.com"))

    assert [season["name"] for season in response.json()] == ["2026", "2025"]


def test_kar_planning_matches_the_web(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", screen_key="kartracker.karplanning", can_view=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")
    team = _create_team(db_session)
    _create_kar(db_session, "B001", magazijn.id, team.id)
    season = _create_season(db_session, "2026", periode_open=True)
    headers = bearer(client, "a@example.com")

    phone = client.get(f"{BASE}/kar-planning", params={"season_id": season.id}, headers=headers)
    web = client.get("/api/modules/module-2/kar-planning", params={"season_id": season.id}, headers=headers)

    assert phone.status_code == 200
    assert phone.json() == web.json()
    assert phone.json()["rows"][0]["kar_nummer"] == "B001"


def test_kar_planning_needs_its_own_view_right(client: TestClient, db_session: Session) -> None:
    # Rights on KarScan don't open Kar Planning or Kar Map.
    _user_with_rights(db_session, "a@example.com", can_view=True, can_create=True)
    headers = bearer(client, "a@example.com")

    assert client.get(f"{BASE}/kar-planning", headers=headers).status_code == 403
    assert client.get(f"{BASE}/seasons", headers=headers).status_code == 403
    assert client.get(f"{BASE}/kar-map", headers=headers).status_code == 403
    assert client.get(f"{BASE}/groundplans", headers=headers).status_code == 403


# --- Kar Map -------------------------------------------------------------------


def test_kar_map_matches_the_web(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", screen_key="kartracker.karmap", can_view=True)
    magazijn = _create_status(db_session, "Terug in Magazijn")
    kar = _create_kar(db_session, "B001", magazijn.id)
    kar.last_latitude, kar.last_longitude = 50.97, 4.68
    db_session.commit()
    headers = bearer(client, "a@example.com")

    phone = client.get(f"{BASE}/kar-map", headers=headers)
    web = client.get("/api/modules/module-2/kar-map", headers=headers)

    assert phone.status_code == 200
    assert phone.json() == web.json()
    assert phone.json()["karren"][0]["latitude"] == 50.97


def test_groundplans_and_their_image(client: TestClient, db_session: Session) -> None:
    _user_with_rights(db_session, "a@example.com", screen_key="kartracker.karmap", can_view=True)
    groundplan = KarTrackerGroundplan(
        name="Terrein",
        image_data=b"\x89PNG-bytes",
        image_content_type="image/png",
        sw_latitude=50.0,
        sw_longitude=4.0,
        ne_latitude=51.0,
        ne_longitude=5.0,
    )
    db_session.add(groundplan)
    db_session.commit()
    headers = bearer(client, "a@example.com")

    listed = client.get(f"{BASE}/groundplans", headers=headers).json()
    image = client.get(f"{BASE}/groundplans/{groundplan.id}/image", headers=headers)

    assert [item["name"] for item in listed] == ["Terrein"]
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content == b"\x89PNG-bytes"
    assert client.get(f"{BASE}/groundplans/9999/image", headers=headers).status_code == 404
