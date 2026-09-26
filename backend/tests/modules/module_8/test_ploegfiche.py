# Tests for Altsien Select's Ploegfiche (the one-screen overview of a
# team's choices) and its PDF.

from fastapi.testclient import TestClient

from tests.modules.module_8.conftest import AltsienWorld

BASE = "/api/modules/module-8"


def test_ploegfiche_shows_every_choice(as_kernlid: TestClient, world: AltsienWorld) -> None:
    team_id = world.own_team.id
    as_kernlid.put(
        f"{BASE}/wizard/{team_id}/festivals", json={"season_id": world.season.id, "festival_ids": [world.festival_a.id]}
    )
    as_kernlid.put(
        f"{BASE}/wizard/{team_id}/afleverlocaties",
        json={
            "season_id": world.season.id,
            "rows": [{"festival_id": world.festival_a.id, "afleverlocatie_id": world.location.id}],
        },
    )
    as_kernlid.post(f"{BASE}/wizard/{team_id}/requests?season_id={world.season.id}", json={"text": "Extra tafel"})

    response = as_kernlid.get(f"{BASE}/ploegfiche/{team_id}?season_id={world.season.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["team"]["kernleden"] == ["kernlid@example.com"]
    festival = next(row for row in body["festivals"] if row["selected"])
    assert festival["afleverlocatie_name"] == "Backstage Noord"
    assert [request["text"] for request in body["requests"]] == ["Extra tafel"]


def test_ploegfiche_respects_team_scope(as_kernlid: TestClient, world: AltsienWorld) -> None:
    response = as_kernlid.get(f"{BASE}/ploegfiche/{world.other_team.id}?season_id={world.season.id}")

    assert response.status_code == 404


def test_pdf_is_generated_for_an_empty_team(as_kernlid: TestClient, world: AltsienWorld) -> None:
    response = as_kernlid.get(f"{BASE}/ploegfiche/{world.own_team.id}/pdf?season_id={world.season.id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_pdf_handles_filled_in_data_and_non_latin_text(as_kernlid: TestClient, world: AltsienWorld) -> None:
    team_id = world.own_team.id
    as_kernlid.put(
        f"{BASE}/wizard/{team_id}/festivals",
        json={"season_id": world.season.id, "festival_ids": [world.festival_a.id, world.festival_b.id]},
    )
    as_kernlid.put(
        f"{BASE}/wizard/{team_id}/afleverlocaties",
        json={
            "season_id": world.season.id,
            "rows": [{"festival_id": world.festival_a.id, "afleverlocatie_id": world.location.id}],
        },
    )
    as_kernlid.post(
        f"{BASE}/wizard/{team_id}/requests?season_id={world.season.id}",
        json={"text": "Graag “extra” stroom – 32A € \U0001f600 " + "lange tekst " * 40},
    )
    as_kernlid.post(f"{BASE}/wizard/{team_id}/steps/festivals/complete?season_id={world.season.id}")

    response = as_kernlid.get(f"{BASE}/ploegfiche/{team_id}/pdf?season_id={world.season.id}&locale=en")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
