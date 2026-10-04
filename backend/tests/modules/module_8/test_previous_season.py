# Tests for the Ploeg Wizard's "copy from last season": finding the season
# before, matching festivals by (fuzzy) name, flagging each line, copying
# delivery locations / team leads / special requests, and the usual scope,
# season-lock and validation rules.

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_special_request import AltsienSelectSpecialRequest
from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.season import Season
from app.db.models.team_festival import TeamFestival
from app.db.models.team_responsible import TeamResponsible
from app.modules.module_8.previous_season import normalize_festival_name, previous_season_of
from tests.modules.module_8.conftest import AltsienWorld

BASE = "/api/modules/module-8"


@pytest.fixture()
def last_season(db_session: Session, world: AltsienWorld) -> Season:
    """A closed 2025 season with its own festivals, where own_team chose
    a location for "Rock Werchter 2025" and "Pukkelpop" (the latter has
    no counterpart in 2026).
    """
    season = Season(name="2025", periode_open=False)
    db_session.add(season)
    db_session.flush()
    rock = Festival(name="Rock Werchter 2025", start_date=date(2025, 7, 3), end_date=date(2025, 7, 6), season_id=season.id)
    tw = Festival(name="TW Classic", start_date=date(2025, 6, 21), end_date=date(2025, 6, 21), season_id=season.id)
    pukkelpop = Festival(name="Pukkelpop", start_date=date(2025, 8, 14), end_date=date(2025, 8, 17), season_id=season.id)
    db_session.add_all([rock, tw, pukkelpop])
    db_session.flush()
    for festival in (rock, tw, pukkelpop):
        db_session.add(TeamFestival(season_id=season.id, team_id=world.own_team.id, festival_id=festival.id))
        db_session.add(
            KarTrackerKarAfleverlocatie(
                season_id=season.id, festival_id=festival.id, team_id=world.own_team.id, afleverlocatie_id=world.location.id
            )
        )
    db_session.commit()
    return season


def _lines(client: TestClient, world: AltsienWorld, step_key: str) -> dict:
    response = client.get(f"{BASE}/wizard/{world.own_team.id}/steps/{step_key}/previous-season?season_id={world.season.id}")
    assert response.status_code == 200
    return response.json()


def _copy(client: TestClient, world: AltsienWorld, step_key: str, keys: list[str], team_id: int | None = None):
    team_id = team_id if team_id is not None else world.own_team.id
    return client.post(
        f"{BASE}/wizard/{team_id}/steps/{step_key}/copy-previous",
        json={"season_id": world.season.id, "line_keys": keys},
    )


def _select_festivals(client: TestClient, world: AltsienWorld, festival_ids: list[int]) -> None:
    client.put(
        f"{BASE}/wizard/{world.own_team.id}/festivals",
        json={"season_id": world.season.id, "festival_ids": festival_ids},
    )


# --- helpers ------------------------------------------------------------------


def test_previous_season_is_the_one_before_by_name(db_session: Session, world: AltsienWorld) -> None:
    assert previous_season_of(db_session, world.season) is None

    db_session.add_all([Season(name="2024"), Season(name="2025"), Season(name="2027")])
    db_session.commit()

    assert previous_season_of(db_session, world.season).name == "2025"


def test_festival_names_match_without_case_years_and_punctuation() -> None:
    assert normalize_festival_name("Rock Werchter 2025") == normalize_festival_name("rock  werchter 2026")
    assert normalize_festival_name("TW-Classic (2024)") == normalize_festival_name("TW Classic")
    assert normalize_festival_name("Pukkelpop") != normalize_festival_name("Rock Werchter")


# --- which steps --------------------------------------------------------------


def test_steps_say_whether_they_offer_a_copy(as_kernlid: TestClient, world: AltsienWorld) -> None:
    steps = as_kernlid.get(f"{BASE}/wizard/{world.own_team.id}?season_id={world.season.id}").json()["steps"]

    copyable = {step["key"] for step in steps if step["copy_from_previous"]}
    assert copyable == {"afleverlocaties", "ploegverantwoordelijken", "special_requests"}


def test_step_without_copy_returns_404(as_kernlid: TestClient, world: AltsienWorld) -> None:
    url = f"{BASE}/wizard/{world.own_team.id}/steps/festivals/previous-season?season_id={world.season.id}"
    assert as_kernlid.get(url).status_code == 404
    assert _copy(as_kernlid, world, "festivals", []).status_code == 404


def test_no_previous_season_gives_no_lines(as_kernlid: TestClient, world: AltsienWorld) -> None:
    body = _lines(as_kernlid, world, "ploegverantwoordelijken")

    assert body == {"previous_season_id": None, "previous_season_name": None, "lines": []}


# --- delivery locations -----------------------------------------------------


def test_location_lines_are_matched_and_flagged(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season
) -> None:
    # Only Rock Werchter is selected this season; TW Classic isn't.
    _select_festivals(as_kernlid, world, [world.festival_a.id])

    body = _lines(as_kernlid, world, "afleverlocaties")

    assert body["previous_season_name"] == "2025"
    by_label = {line["label"]: line for line in body["lines"]}
    assert by_label["Rock Werchter 2025"]["target"] == "Rock Werchter"
    assert by_label["Rock Werchter 2025"]["detail"] == "Backstage Noord"
    assert by_label["Rock Werchter 2025"]["unavailable_reason"] is None
    assert by_label["Rock Werchter 2025"]["already_present"] is False
    assert by_label["TW Classic"]["unavailable_reason"] == "festival_not_selected"
    assert by_label["Pukkelpop"]["unavailable_reason"] == "not_in_season"


def test_inactive_location_cannot_be_copied(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season, db_session: Session
) -> None:
    _select_festivals(as_kernlid, world, [world.festival_a.id])
    db_session.get(KarTrackerAfleverlocatie, world.location.id).active = False
    db_session.commit()

    by_label = {line["label"]: line for line in _lines(as_kernlid, world, "afleverlocaties")["lines"]}

    assert by_label["Rock Werchter 2025"]["unavailable_reason"] == "location_inactive"


def test_copying_locations_writes_plan_a_kar(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season, db_session: Session
) -> None:
    _select_festivals(as_kernlid, world, [world.festival_a.id, world.festival_b.id])
    keys = [line["key"] for line in _lines(as_kernlid, world, "afleverlocaties")["lines"]]

    # Every line is sent; the one without a 2026 festival is skipped.
    response = _copy(as_kernlid, world, "afleverlocaties", keys)

    assert response.status_code == 200
    chosen = {row["festival_id"]: row["afleverlocatie_id"] for row in response.json()["festivals"] if row["selected"]}
    assert chosen == {world.festival_a.id: world.location.id, world.festival_b.id: world.location.id}
    # Copying doesn't mark the step as done.
    assert response.json()["progress"] == []
    # And the lines now show as already present.
    lines = _lines(as_kernlid, world, "afleverlocaties")["lines"]
    assert all(line["already_present"] for line in lines if line["unavailable_reason"] is None)


# --- team leads ----------------------------------------------------------------


def test_copying_team_leads_adds_them_and_skips_duplicates(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season, db_session: Session
) -> None:
    for name, email in (("Jan Peeters", "jan@example.com"), ("An Claes", "an@example.com")):
        db_session.add(
            TeamResponsible(season_id=last_season.id, team_id=world.own_team.id, name=name, email=email, phone="0470")
        )
    # Jan is already listed this season (different case).
    db_session.add(
        TeamResponsible(season_id=world.season.id, team_id=world.own_team.id, name="jan peeters", email="JAN@example.com", phone="0470")
    )
    db_session.commit()

    lines = _lines(as_kernlid, world, "ploegverantwoordelijken")["lines"]
    assert {line["label"]: line["already_present"] for line in lines} == {"An Claes": False, "Jan Peeters": True}

    response = _copy(as_kernlid, world, "ploegverantwoordelijken", [line["key"] for line in lines])

    assert response.status_code == 200
    assert sorted(row["name"] for row in response.json()["responsibles"]) == ["An Claes", "jan peeters"]
    # Last season's rows are untouched.
    assert len(db_session.scalars(select(TeamResponsible).where(TeamResponsible.season_id == last_season.id)).all()) == 2


def test_same_team_lead_twice_last_season_is_copied_once(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season, db_session: Session
) -> None:
    for name in ("Jan Peeters", "jan peeters "):
        db_session.add(
            TeamResponsible(season_id=last_season.id, team_id=world.own_team.id, name=name, email="jan@example.com", phone="0470")
        )
    db_session.commit()
    keys = [line["key"] for line in _lines(as_kernlid, world, "ploegverantwoordelijken")["lines"]]

    response = _copy(as_kernlid, world, "ploegverantwoordelijken", keys)

    assert len(response.json()["responsibles"]) == 1


# --- special requests --------------------------------------------------------------


def test_copying_requests_creates_new_ones_in_the_first_status(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season, db_session: Session
) -> None:
    old = AltsienSelectSpecialRequest(
        season_id=last_season.id,
        team_id=world.own_team.id,
        text="Extra frigo aub",
        status_id=world.status_completed.id,
        organisation_note="Geregeld",
    )
    db_session.add(old)
    db_session.commit()

    lines = _lines(as_kernlid, world, "special_requests")["lines"]
    assert [(line["label"], line["detail"]) for line in lines] == [("Extra frigo aub", "Completed")]

    response = _copy(as_kernlid, world, "special_requests", [lines[0]["key"]])

    assert response.status_code == 200
    [copied] = response.json()["requests"]
    assert copied["text"] == "Extra frigo aub"
    assert copied["status_name"] == "New"
    assert copied["organisation_note"] is None
    assert copied["created_by_name"] == "kernlid@example.com"

    # Copying again changes nothing: the text is already present.
    again = _copy(as_kernlid, world, "special_requests", [lines[0]["key"]])
    assert len(again.json()["requests"]) == 1


def test_same_request_text_twice_last_season_is_copied_once(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season, db_session: Session
) -> None:
    for text in ("Extra frigo aub", "Extra frigo aub "):
        db_session.add(
            AltsienSelectSpecialRequest(
                season_id=last_season.id, team_id=world.own_team.id, text=text, status_id=world.status_new.id
            )
        )
    db_session.commit()
    keys = [line["key"] for line in _lines(as_kernlid, world, "special_requests")["lines"]]

    response = _copy(as_kernlid, world, "special_requests", keys)

    assert len(response.json()["requests"]) == 1


# --- rules --------------------------------------------------------------------


def test_unknown_line_key_is_refused(as_kernlid: TestClient, world: AltsienWorld, last_season: Season) -> None:
    assert _copy(as_kernlid, world, "ploegverantwoordelijken", ["999999"]).status_code == 400


def test_cannot_copy_for_another_team(as_kernlid: TestClient, world: AltsienWorld, last_season: Season) -> None:
    assert _copy(as_kernlid, world, "ploegverantwoordelijken", [], team_id=world.other_team.id).status_code == 404


def test_cannot_copy_into_a_closed_season(
    as_kernlid: TestClient, world: AltsienWorld, last_season: Season, db_session: Session
) -> None:
    db_session.get(Season, world.season.id).periode_open = False
    db_session.commit()

    assert _copy(as_kernlid, world, "ploegverantwoordelijken", []).status_code == 403
