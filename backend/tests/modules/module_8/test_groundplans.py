# Tests for Altsien Select's read-only ground plan endpoints, which feed the
# map in Ploeg Wizard step 2 (afleverlocaties) — and for the coordinates the
# step's delivery-location options carry so they can be pinned on it.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from tests.modules.module_8.conftest import AltsienWorld, login

BASE = "/api/modules/module-8"


def _add_groundplan(db_session: Session, name: str = "Terrein") -> KarTrackerGroundplan:
    plan = KarTrackerGroundplan(
        name=name,
        image_data=b"png-bytes",
        image_content_type="image/png",
        sw_latitude=50.0,
        sw_longitude=4.0,
        ne_latitude=51.0,
        ne_longitude=5.0,
    )
    db_session.add(plan)
    db_session.commit()
    return plan


def test_wizard_user_can_list_and_fetch_ground_plans(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    plan = _add_groundplan(db_session)

    listed = as_kernlid.get(f"{BASE}/groundplans")
    image = as_kernlid.get(f"{BASE}/groundplans/{plan.id}/image")

    assert listed.status_code == 200
    assert [(item["name"], item["ne_latitude"]) for item in listed.json()] == [("Terrein", 51.0)]
    assert image.status_code == 200
    assert image.content == b"png-bytes"
    assert image.headers["content-type"] == "image/png"


def test_unknown_ground_plan_image_is_404(as_kernlid: TestClient, world: AltsienWorld) -> None:
    assert as_kernlid.get(f"{BASE}/groundplans/999/image").status_code == 404


def test_user_without_wizard_or_ploegfiche_view_cannot_read_ground_plans(
    client: TestClient, world: AltsienWorld, make_user, db_session: Session
) -> None:
    plan = _add_groundplan(db_session)
    make_user("norole@example.com", None)
    login(client, "norole@example.com")

    assert client.get(f"{BASE}/groundplans").status_code == 403
    assert client.get(f"{BASE}/groundplans/{plan.id}/image").status_code == 403


def test_afleverlocatie_options_carry_coordinates(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    world.location.latitude = 50.97
    world.location.longitude = 4.69
    db_session.commit()

    state = as_kernlid.get(f"{BASE}/wizard/{world.own_team.id}?season_id={world.season.id}").json()

    assert [(item["name"], item["latitude"], item["longitude"]) for item in state["afleverlocaties"]] == [
        ("Backstage Noord", 50.97, 4.69)
    ]
