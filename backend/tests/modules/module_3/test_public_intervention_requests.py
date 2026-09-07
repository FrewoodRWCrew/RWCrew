# These tests check the public (no-login) intervention-request endpoints
# in app/modules/module_3/public_router.py — reachable by customers via a
# QR code, with no authentication at all. Contrast with
# test_roles.py, which covers the staff-only, login-gated router.py.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.intervention_status import InterventionStatus
from app.db.models.team import Team


def _create_team(db_session: Session, *, name: str = "Team A") -> Team:
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _seed_default_status(db_session: Session) -> InterventionStatus:
    """The public create endpoint always assigns the "Nieuw" status — see
    app/modules/module_3/service.py's get_default_new_status.
    """
    status = InterventionStatus(name="Nieuw", is_open=True, color="gray")
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


def test_list_public_teams_requires_no_auth(client: TestClient, db_session: Session) -> None:
    _create_team(db_session, name="Team A")

    response = client.get("/api/public/intervention-requests/teams")

    assert response.status_code == 200
    assert [team["name"] for team in response.json()] == ["Team A"]


def test_create_public_request_with_existing_team(client: TestClient, db_session: Session) -> None:
    team = _create_team(db_session)
    default_status = _seed_default_status(db_session)

    response = client.post(
        "/api/public/intervention-requests",
        json={"team_id": team.id, "question": "Kar is stuk"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["team_id"] == team.id
    assert body["team_name"] is None
    assert body["status_id"] == default_status.id
    assert body["handled_by"] is None
    assert body["team_cart_user_id"] is None
    assert body["request_number"].startswith("IA")


def test_create_public_request_with_free_text_team_name(client: TestClient, db_session: Session) -> None:
    _seed_default_status(db_session)

    response = client.post(
        "/api/public/intervention-requests",
        json={"team_name": "Onbekende Ploeg", "question": "Vraag over levering"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["team_id"] is None
    assert body["team_name"] == "Onbekende Ploeg"


def test_create_public_request_rejects_both_team_id_and_team_name(client: TestClient, db_session: Session) -> None:
    team = _create_team(db_session)
    _seed_default_status(db_session)

    response = client.post(
        "/api/public/intervention-requests",
        json={"team_id": team.id, "team_name": "Andere Naam", "question": "Vraag"},
    )

    assert response.status_code == 422


def test_create_public_request_rejects_neither_team_id_nor_team_name(client: TestClient, db_session: Session) -> None:
    _seed_default_status(db_session)

    response = client.post(
        "/api/public/intervention-requests",
        json={"question": "Vraag"},
    )

    assert response.status_code == 422


def test_create_public_request_ignores_internal_only_fields(client: TestClient, db_session: Session) -> None:
    """status_id/handled_by/team_cart_user_id aren't accepted by the public
    schema at all — sending them is simply ignored by FastAPI/Pydantic
    rather than trusted, unlike the staff-only create endpoint.
    """
    team = _create_team(db_session)
    default_status = _seed_default_status(db_session)
    other_status = InterventionStatus(name="Geleverd", is_open=False, color="green")
    db_session.add(other_status)
    db_session.commit()
    db_session.refresh(other_status)

    response = client.post(
        "/api/public/intervention-requests",
        json={
            "team_id": team.id,
            "question": "Vraag",
            "status_id": other_status.id,
            "handled_by": "Iemand",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status_id"] == default_status.id
    assert body["handled_by"] is None


def test_create_public_request_404s_for_unknown_team_id(client: TestClient, db_session: Session) -> None:
    _seed_default_status(db_session)

    response = client.post(
        "/api/public/intervention-requests",
        json={"team_id": 9999, "question": "Vraag"},
    )

    assert response.status_code == 404


def test_create_public_request_fails_without_default_status_configured(
    client: TestClient, db_session: Session
) -> None:
    team = _create_team(db_session)

    response = client.post(
        "/api/public/intervention-requests",
        json={"team_id": team.id, "question": "Vraag"},
    )

    assert response.status_code == 500
