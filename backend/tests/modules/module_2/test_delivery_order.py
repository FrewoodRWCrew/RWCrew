# Tests for the "Leveringsvolgorde" screen (module_2/delivery_order_service.py):
# the active delivery locations get their position in the delivery tour
# (KarTracker_afleverlocaties.terrein_positie), saved as one whole tour.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.kartracker_zone import KarTrackerZone
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)

URL = "/api/modules/module-2/delivery-order"


def _login_admin(client: TestClient, db_session: Session) -> None:
    """Set up the module and log in as a super admin with module access."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")


def _login_with_role(client: TestClient, db_session: Session, **permissions: bool) -> None:
    """Log in as a plain user whose role has the given rights on the screen."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="user@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(
        db_session, name="Planner", screen_key="kartracker.leveringsvolgorde", **permissions
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "user@example.com")


def _create_locations(db_session: Session, *specs: tuple[str, int | None, bool]) -> dict[str, int]:
    """Locations (name, terrein_positie, active) sharing one zone and distributiepunt."""
    zone = KarTrackerZone(name="Zone A")
    distributiepunt = KarTrackerDistributiepunt(name="DP 1")
    db_session.add_all([zone, distributiepunt])
    db_session.commit()
    locations = [
        KarTrackerAfleverlocatie(
            name=name,
            zone_id=zone.id,
            distributiepunt_id=distributiepunt.id,
            terrein_positie=positie,
            active=active,
        )
        for name, positie, active in specs
    ]
    db_session.add_all(locations)
    db_session.commit()
    return {location.name: location.id for location in locations}


def _positions(db_session: Session) -> dict[str, int | None]:
    db_session.expire_all()
    return {
        location.name: location.terrein_positie for location in db_session.query(KarTrackerAfleverlocatie).all()
    }


def test_list_puts_the_tour_first_and_hides_inactive(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    _create_locations(
        db_session,
        ("Zuid", None, True),
        ("Backstage", 2, True),
        ("Alpha", None, True),
        ("Poort 1", 1, True),
        ("Oud", 3, False),
    )

    response = client.get(URL)

    assert response.status_code == 200
    rows = response.json()
    assert [row["name"] for row in rows] == ["Poort 1", "Backstage", "Alpha", "Zuid"]
    assert rows[0] == {
        "id": rows[0]["id"],
        "name": "Poort 1",
        "description": None,
        "zone_name": "Zone A",
        "distributiepunt_name": "DP 1",
        "terrein_positie": 1,
        "latitude": None,
        "longitude": None,
    }


def test_save_renumbers_the_tour_and_clears_the_rest(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    ids = _create_locations(
        db_session,
        ("A", 5, True),
        ("B", 9, True),
        ("C", None, True),
        ("Oud", 4, False),
    )

    # C goes first, A second; B is taken out of the tour.
    response = client.put(URL, json={"afleverlocatie_ids": [ids["C"], ids["A"]]})

    assert response.status_code == 200
    assert [(row["name"], row["terrein_positie"]) for row in response.json()] == [("C", 1), ("A", 2), ("B", None)]
    # The inactive location keeps its old value.
    assert _positions(db_session) == {"A": 2, "B": None, "C": 1, "Oud": 4}


def test_save_rejects_duplicate_unknown_or_inactive_ids(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    ids = _create_locations(db_session, ("A", 1, True), ("Oud", None, False))

    for bad_ids in ([ids["A"], ids["A"]], [ids["A"], 99999], [ids["Oud"]]):
        response = client.put(URL, json={"afleverlocatie_ids": bad_ids})
        assert response.status_code == 400

    # Nothing changed.
    assert _positions(db_session) == {"A": 1, "Oud": None}


def test_view_right_can_read_but_not_save(client: TestClient, db_session: Session) -> None:
    _login_with_role(client, db_session, can_view=True)
    ids = _create_locations(db_session, ("A", None, True))

    assert client.get(URL).status_code == 200
    assert client.put(URL, json={"afleverlocatie_ids": [ids["A"]]}).status_code == 403


def test_without_rights_the_screen_is_forbidden(client: TestClient, db_session: Session) -> None:
    _login_with_role(client, db_session)

    assert client.get(URL).status_code == 403


def test_edit_right_can_save(client: TestClient, db_session: Session) -> None:
    _login_with_role(client, db_session, can_view=True, can_edit=True)
    ids = _create_locations(db_session, ("A", None, True))

    assert client.put(URL, json={"afleverlocatie_ids": [ids["A"]]}).status_code == 200
    assert _positions(db_session) == {"A": 1}


def test_view_right_can_load_the_ground_plans_for_the_map(client: TestClient, db_session: Session) -> None:
    _login_with_role(client, db_session, can_view=True)

    assert client.get("/api/modules/module-2/groundplans").status_code == 200
