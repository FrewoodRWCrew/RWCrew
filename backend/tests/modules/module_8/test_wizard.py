# Tests for Altsien Select's Ploeg Wizard: which teams a user may open,
# saving festivals and delivery locations (shared with KarTracker's "Plan a
# kar"), completing steps, and the season lock.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from tests.modules.module_8.conftest import AltsienWorld, login

BASE = "/api/modules/module-8"


def _save_festivals(client: TestClient, world: AltsienWorld, festival_ids: list[int]):
    return client.put(
        f"{BASE}/wizard/{world.own_team.id}/festivals",
        json={"season_id": world.season.id, "festival_ids": festival_ids},
    )


def _save_location(client: TestClient, world: AltsienWorld, festival_id: int, location_id: int | None):
    return client.put(
        f"{BASE}/wizard/{world.own_team.id}/afleverlocaties",
        json={"season_id": world.season.id, "rows": [{"festival_id": festival_id, "afleverlocatie_id": location_id}]},
    )


def _complete(client: TestClient, world: AltsienWorld, step_key: str):
    return client.post(f"{BASE}/wizard/{world.own_team.id}/steps/{step_key}/complete?season_id={world.season.id}")


# --- team scope -------------------------------------------------------------


def test_kernlid_only_sees_their_own_teams(as_kernlid: TestClient, world: AltsienWorld) -> None:
    response = as_kernlid.get(f"{BASE}/teams?season_id={world.season.id}")

    assert response.status_code == 200
    assert [team["team_name"] for team in response.json()] == ["Chiro Werchter"]


def test_kernlid_cannot_open_another_team(as_kernlid: TestClient, world: AltsienWorld) -> None:
    response = as_kernlid.get(f"{BASE}/wizard/{world.other_team.id}?season_id={world.season.id}")

    assert response.status_code == 404


def test_organisation_sees_every_team(client: TestClient, world: AltsienWorld, make_user) -> None:
    make_user("org@example.com", world.organisation_role)
    login(client, "org@example.com")

    response = client.get(f"{BASE}/teams?season_id={world.season.id}")

    assert [team["team_name"] for team in response.json()] == ["Chiro Werchter", "KSA Haacht"]


# --- festivals + delivery locations ---------------------------------------


def test_saving_festivals_marks_them_selected(as_kernlid: TestClient, world: AltsienWorld) -> None:
    response = _save_festivals(as_kernlid, world, [world.festival_a.id])

    assert response.status_code == 200
    selected = {row["festival_name"]: row["selected"] for row in response.json()["festivals"]}
    assert selected == {"Rock Werchter": True, "TW Classic": False}


def test_location_is_written_to_plan_a_kar(as_kernlid: TestClient, world: AltsienWorld, db_session: Session) -> None:
    _save_festivals(as_kernlid, world, [world.festival_a.id])

    response = _save_location(as_kernlid, world, world.festival_a.id, world.location.id)

    assert response.status_code == 200
    plan = db_session.scalars(select(KarTrackerKarAfleverlocatie)).all()
    assert [(row.festival_id, row.team_id, row.afleverlocatie_id) for row in plan] == [
        (world.festival_a.id, world.own_team.id, world.location.id)
    ]


def test_location_for_an_unselected_festival_is_rejected(as_kernlid: TestClient, world: AltsienWorld) -> None:
    _save_festivals(as_kernlid, world, [world.festival_a.id])

    response = _save_location(as_kernlid, world, world.festival_b.id, world.location.id)

    assert response.status_code == 400


def test_deselecting_a_festival_removes_its_plan_a_kar_row(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    _save_festivals(as_kernlid, world, [world.festival_a.id])
    _save_location(as_kernlid, world, world.festival_a.id, world.location.id)

    _save_festivals(as_kernlid, world, [world.festival_b.id])

    assert db_session.scalars(select(KarTrackerKarAfleverlocatie)).all() == []


# --- completing steps -------------------------------------------------------


def test_festivals_step_needs_at_least_one_festival(as_kernlid: TestClient, world: AltsienWorld) -> None:
    assert _complete(as_kernlid, world, "festivals").status_code == 400

    _save_festivals(as_kernlid, world, [world.festival_a.id])

    assert _complete(as_kernlid, world, "festivals").status_code == 200


def test_location_step_needs_a_location_for_every_festival(as_kernlid: TestClient, world: AltsienWorld) -> None:
    _save_festivals(as_kernlid, world, [world.festival_a.id, world.festival_b.id])
    _save_location(as_kernlid, world, world.festival_a.id, world.location.id)

    assert _complete(as_kernlid, world, "afleverlocaties").status_code == 400

    _save_location(as_kernlid, world, world.festival_b.id, world.location.id)

    assert _complete(as_kernlid, world, "afleverlocaties").status_code == 200


def test_changing_festivals_reopens_the_location_step(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    _save_festivals(as_kernlid, world, [world.festival_a.id])
    _save_location(as_kernlid, world, world.festival_a.id, world.location.id)
    _complete(as_kernlid, world, "afleverlocaties")

    _save_festivals(as_kernlid, world, [world.festival_a.id, world.festival_b.id])

    keys = db_session.scalars(select(AltsienSelectStepProgress.step_key)).all()
    assert "afleverlocaties" not in keys


def test_placeholder_step_can_be_marked_done_and_reopened(as_kernlid: TestClient, world: AltsienWorld) -> None:
    done = _complete(as_kernlid, world, "products")
    assert done.status_code == 200
    assert [item["step_key"] for item in done.json()["progress"]] == ["products"]

    reopened = as_kernlid.delete(
        f"{BASE}/wizard/{world.own_team.id}/steps/products/complete?season_id={world.season.id}"
    )
    assert reopened.json()["progress"] == []


def test_unknown_step_returns_404(as_kernlid: TestClient, world: AltsienWorld) -> None:
    assert _complete(as_kernlid, world, "does-not-exist").status_code == 404


# --- season lock ------------------------------------------------------------


def test_closed_season_is_read_only_for_a_kernlid(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    world.season.periode_open = False
    db_session.commit()

    state = as_kernlid.get(f"{BASE}/wizard/{world.own_team.id}?season_id={world.season.id}")
    assert state.status_code == 200
    assert state.json()["can_edit"] is False
    assert _save_festivals(as_kernlid, world, [world.festival_a.id]).status_code == 403


def test_organisation_can_still_edit_a_closed_season(
    client: TestClient, world: AltsienWorld, make_user, db_session: Session
) -> None:
    world.season.periode_open = False
    db_session.commit()
    make_user("org@example.com", world.organisation_role)
    login(client, "org@example.com")

    assert _save_festivals(client, world, [world.festival_a.id]).status_code == 200
