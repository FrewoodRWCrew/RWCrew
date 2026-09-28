# Tests for the Ploeg Wizard's "Ploegverantwoordelijken" step: adding,
# changing and removing a team's responsible people from the wizard (stored
# in MasterData's MasterData_team_responsible, shared with its own screen),
# the team scope, the season lock, and the step's completion rule.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.team_responsible import TeamResponsible
from tests.modules.module_8.conftest import AltsienWorld

BASE = "/api/modules/module-8"
STEP = "ploegverantwoordelijken"


def _person(**overrides: object) -> dict:
    person = {"name": "Jan Peeters", "email": "jan@example.com", "phone": "0470 12 34 56", "comments": None}
    person.update(overrides)
    return person


def _add(client: TestClient, world: AltsienWorld, team_id: int | None = None, **overrides: object):
    team_id = team_id if team_id is not None else world.own_team.id
    return client.post(
        f"{BASE}/wizard/{team_id}/responsibles?season_id={world.season.id}", json=_person(**overrides)
    )


def _complete(client: TestClient, world: AltsienWorld):
    return client.post(f"{BASE}/wizard/{world.own_team.id}/steps/{STEP}/complete?season_id={world.season.id}")


def _state(client: TestClient, world: AltsienWorld) -> dict:
    return client.get(f"{BASE}/wizard/{world.own_team.id}?season_id={world.season.id}").json()


def test_step_sits_between_afleverlocaties_and_products(as_kernlid: TestClient, world: AltsienWorld) -> None:
    keys = [step["key"] for step in _state(as_kernlid, world)["steps"]]

    assert keys.index(STEP) == keys.index("afleverlocaties") + 1
    assert keys.index("products") == keys.index(STEP) + 1


def test_kernlid_can_add_change_and_remove_a_responsible(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    created = _add(as_kernlid, world, name="  Jan Peeters  ", comments="Na 18u")
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Jan Peeters"
    assert body["team_id"] == world.own_team.id
    assert body["season_id"] == world.season.id

    # The wizard state (and so the Ploegfiche) includes the person.
    assert [row["name"] for row in _state(as_kernlid, world)["responsibles"]] == ["Jan Peeters"]

    updated = as_kernlid.put(
        f"{BASE}/wizard/{world.own_team.id}/responsibles/{body['id']}", json=_person(phone="0499", comments=" ")
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "0499"
    assert updated.json()["comments"] is None

    deleted = as_kernlid.delete(f"{BASE}/wizard/{world.own_team.id}/responsibles/{body['id']}")
    assert deleted.status_code == 204
    assert db_session.scalars(select(TeamResponsible)).all() == []


def test_required_fields_and_email_format_are_enforced(as_kernlid: TestClient, world: AltsienWorld) -> None:
    assert _add(as_kernlid, world, name="").status_code == 422
    assert _add(as_kernlid, world, phone="").status_code == 422
    assert _add(as_kernlid, world, email="not-an-email").status_code == 422
    # Only spaces counts as empty too.
    assert _add(as_kernlid, world, name="   ").status_code == 422
    assert _add(as_kernlid, world, phone="   ").status_code == 422
    assert _add(as_kernlid, world, comments="x" * 5001).status_code == 422


def test_kernlid_cannot_touch_another_teams_responsibles(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    assert _add(as_kernlid, world, team_id=world.other_team.id).status_code == 404

    # A row of another team can't be reached through the own team's URL either.
    foreign = TeamResponsible(
        season_id=world.season.id, team_id=world.other_team.id, name="X", email="x@example.com", phone="1"
    )
    db_session.add(foreign)
    db_session.commit()
    assert as_kernlid.put(f"{BASE}/wizard/{world.own_team.id}/responsibles/{foreign.id}", json=_person()).status_code == 404
    assert as_kernlid.delete(f"{BASE}/wizard/{world.own_team.id}/responsibles/{foreign.id}").status_code == 404


def test_closed_season_is_read_only(as_kernlid: TestClient, world: AltsienWorld, db_session: Session) -> None:
    world.season.periode_open = False
    db_session.commit()

    assert _add(as_kernlid, world).status_code == 403


def test_step_needs_at_least_one_responsible(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session
) -> None:
    assert _complete(as_kernlid, world).status_code == 400

    person_id = _add(as_kernlid, world).json()["id"]
    assert _complete(as_kernlid, world).status_code == 200

    # Removing the last person un-marks the step.
    as_kernlid.delete(f"{BASE}/wizard/{world.own_team.id}/responsibles/{person_id}")
    progress = db_session.scalars(
        select(AltsienSelectStepProgress).where(AltsienSelectStepProgress.step_key == STEP)
    ).all()
    assert progress == []
