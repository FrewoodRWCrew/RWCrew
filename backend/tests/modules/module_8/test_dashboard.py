# Tests for Altsien Select's KPI screen figures.

from fastapi.testclient import TestClient

from app.modules.module_8.steps import STEP_DEFINITIONS
from tests.modules.module_8.conftest import AltsienWorld, login

BASE = "/api/modules/module-8"


def test_dashboard_counts_only_the_users_teams(as_kernlid: TestClient, world: AltsienWorld) -> None:
    team_id = world.own_team.id
    as_kernlid.post(f"{BASE}/wizard/{team_id}/steps/products/complete?season_id={world.season.id}")
    as_kernlid.post(f"{BASE}/wizard/{team_id}/requests?season_id={world.season.id}", json={"text": "Iets extra"})

    body = as_kernlid.get(f"{BASE}/dashboard?season_id={world.season.id}").json()

    assert body["total_teams"] == 1
    assert body["in_progress_teams"] == 1
    assert body["completed_teams"] == 0
    assert body["open_requests"] == 1
    products = next(item for item in body["step_breakdown"] if item["step_key"] == "products")
    assert products["completed_count"] == 1
    assert {item["status_name"]: item["count"] for item in body["status_breakdown"]} == {
        "New": 1,
        "In Progress": 0,
        "Completed": 0,
    }


def test_dashboard_marks_a_team_complete_when_every_step_is_done(
    client: TestClient, world: AltsienWorld, make_user
) -> None:
    make_user("org@example.com", world.organisation_role)
    login(client, "org@example.com")
    team_id = world.own_team.id
    client.put(
        f"{BASE}/wizard/{team_id}/festivals", json={"season_id": world.season.id, "festival_ids": [world.festival_a.id]}
    )
    client.put(
        f"{BASE}/wizard/{team_id}/afleverlocaties",
        json={
            "season_id": world.season.id,
            "rows": [{"festival_id": world.festival_a.id, "afleverlocatie_id": world.location.id}],
        },
    )
    for step in STEP_DEFINITIONS:
        assert client.post(f"{BASE}/wizard/{team_id}/steps/{step.key}/complete?season_id={world.season.id}").status_code == 200

    body = client.get(f"{BASE}/dashboard?season_id={world.season.id}").json()

    assert body["total_teams"] == 2
    assert body["completed_teams"] == 1
    assert body["not_started_teams"] == 1


def test_dashboard_without_a_season_is_empty(as_kernlid: TestClient) -> None:
    body = as_kernlid.get(f"{BASE}/dashboard").json()

    assert body["season_id"] is None
    assert body["completed_teams"] == 0
