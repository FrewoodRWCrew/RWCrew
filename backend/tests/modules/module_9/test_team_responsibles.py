# These tests check the "Ploegverantwoordelijken" screen (nested under
# "Teams"): gated by normal module access + the
# "masterdata.team-responsibles" permission, with a super-admin bypass —
# mirrors test_team_locations.py's shape, plus the team/season links.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_responsible import TeamResponsible
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_9.screens import sync_screens

URL = "/api/modules/module-9/team-responsibles"


def _create_user(db_session: Session, *, email: str, is_super_admin: bool = False) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        display_name=email,
        is_super_admin=is_super_admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_masterdata_module(db_session: Session) -> Module:
    module = db_session.scalar(select(Module).where(Module.key == "module-9"))
    if module is not None:
        return module
    module = Module(key="module-9", name="MasterData", sort_order=9)
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module


def _grant_module_access(db_session: Session, user: User, module: Module) -> None:
    db_session.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db_session.commit()


def _grant_team_responsible_permission(
    db_session: Session,
    user: User,
    *,
    can_view: bool = False,
    can_create: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    role = MasterDataRole(name=f"Team Responsible Role {user.email}")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    screen = db_session.scalar(
        select(MasterDataScreen).where(MasterDataScreen.key == "masterdata.team-responsibles")
    )
    db_session.add(
        MasterDataRolePermission(
            role_id=role.id,
            screen_id=screen.id,
            can_view=can_view,
            can_create=can_create,
            can_edit=can_edit,
            can_delete=can_delete,
        )
    )
    db_session.add(MasterDataUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()


def _create_team(db_session: Session, *, name: str) -> Team:
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_season(db_session: Session, *, name: str) -> Season:
    season = Season(name=name)
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


def _create_team_responsible(db_session: Session, *, team: Team, season: Season, name: str) -> TeamResponsible:
    team_responsible = TeamResponsible(
        team_id=team.id, season_id=season.id, name=name, email=f"{name.lower()}@example.com", phone="0470"
    )
    db_session.add(team_responsible)
    db_session.commit()
    db_session.refresh(team_responsible)
    return team_responsible


def _payload(team: Team, season: Season, **overrides: object) -> dict:
    payload = {
        "team_id": team.id,
        "season_id": season.id,
        "name": "Jan Peeters",
        "email": "jan@example.com",
        "phone": "+32 470 12 34 56",
        "comments": "Bereikbaar na 18u",
    }
    payload.update(overrides)
    return payload


def _login(client: TestClient, email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def _login_super_admin(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    admin = _create_user(db_session, email="admin@example.com", is_super_admin=True)
    _grant_module_access(db_session, admin, module)
    _login(client, "admin@example.com")


def test_user_with_access_but_no_permission_cannot_list_team_responsibles(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="regular@example.com")
    _grant_module_access(db_session, user, module)
    _login(client, "regular@example.com")

    assert client.get(URL).status_code == 403
    assert client.get(f"{URL}/options").status_code == 403


def test_viewer_can_list_and_filter_team_responsibles(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_team_responsible_permission(db_session, user, can_view=True)
    team_b = _create_team(db_session, name="B-team")
    team_a = _create_team(db_session, name="A-team")
    season_2026 = _create_season(db_session, name="2026")
    season_2027 = _create_season(db_session, name="2027")
    _create_team_responsible(db_session, team=team_b, season=season_2026, name="Zoe")
    _create_team_responsible(db_session, team=team_a, season=season_2026, name="Wim")
    _create_team_responsible(db_session, team=team_a, season=season_2027, name="Ann")
    _login(client, "viewer@example.com")

    # Unfiltered: sorted by team name, then person name.
    response = client.get(URL)
    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Ann", "Wim", "Zoe"]

    # Filtered by season and by season + team.
    assert [row["name"] for row in client.get(URL, params={"season_id": season_2026.id}).json()] == ["Wim", "Zoe"]
    assert [
        row["name"] for row in client.get(URL, params={"season_id": season_2026.id, "team_id": team_b.id}).json()
    ] == ["Zoe"]

    # The dropdown options come with this screen's own view permission.
    options = client.get(f"{URL}/options").json()
    assert [team["name"] for team in options["teams"]] == ["A-team", "B-team"]
    assert [season["name"] for season in options["seasons"]] == ["2026", "2027"]


def test_view_only_permission_cannot_create_a_team_responsible(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = _create_masterdata_module(db_session)
    user = _create_user(db_session, email="viewer@example.com")
    _grant_module_access(db_session, user, module)
    _grant_team_responsible_permission(db_session, user, can_view=True)
    team = _create_team(db_session, name="A-team")
    season = _create_season(db_session, name="2026")
    _login(client, "viewer@example.com")

    assert client.post(URL, json=_payload(team, season)).status_code == 403


def test_super_admin_can_create_update_and_delete_a_team_responsible(
    client: TestClient, db_session: Session
) -> None:
    _login_super_admin(client, db_session)
    team = _create_team(db_session, name="A-team")
    other_team = _create_team(db_session, name="B-team")
    season = _create_season(db_session, name="2026")

    created = client.post(URL, json=_payload(team, season, name="  Jan Peeters  "))
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Jan Peeters"
    assert body["team_id"] == team.id
    assert body["comments"] == "Bereikbaar na 18u"

    updated = client.put(f"{URL}/{body['id']}", json=_payload(other_team, season, phone="0499", comments="  "))
    assert updated.status_code == 200
    assert updated.json()["team_id"] == other_team.id
    assert updated.json()["phone"] == "0499"
    # Blank comments are stored as "none".
    assert updated.json()["comments"] is None

    assert client.delete(f"{URL}/{body['id']}").status_code == 204
    assert client.get(URL).json() == []


def test_required_fields_and_email_format_are_enforced(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    team = _create_team(db_session, name="A-team")
    season = _create_season(db_session, name="2026")

    assert client.post(URL, json=_payload(team, season, name="")).status_code == 422
    assert client.post(URL, json=_payload(team, season, phone="")).status_code == 422
    assert client.post(URL, json=_payload(team, season, email="not-an-email")).status_code == 422
    # Only spaces counts as empty too.
    assert client.post(URL, json=_payload(team, season, name="   ")).status_code == 422
    assert client.post(URL, json=_payload(team, season, phone="   ")).status_code == 422
    assert client.post(URL, json=_payload(team, season, comments="x" * 5001)).status_code == 422
    # Comments are optional.
    assert client.post(URL, json=_payload(team, season, comments=None)).status_code == 201


def test_unknown_team_or_season_is_a_404(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    team = _create_team(db_session, name="A-team")
    season = _create_season(db_session, name="2026")

    assert client.post(URL, json=_payload(team, season, team_id=9999)).status_code == 404
    assert client.post(URL, json=_payload(team, season, season_id=9999)).status_code == 404
    assert client.put(f"{URL}/9999", json=_payload(team, season)).status_code == 404
    assert client.delete(f"{URL}/9999").status_code == 404


def test_deleting_a_team_removes_its_responsibles(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    team = _create_team(db_session, name="A-team")
    season = _create_season(db_session, name="2026")
    _create_team_responsible(db_session, team=team, season=season, name="Jan")

    assert client.delete(f"/api/modules/module-9/teams/{team.id}").status_code == 204
    assert db_session.scalars(select(TeamResponsible)).all() == []


# --- Altsien Select's "Ploegverantwoordelijken" wizard step -------------------


def _mark_step_done(db_session: Session, team: Team, season: Season) -> None:
    db_session.add(AltsienSelectStepProgress(season_id=season.id, team_id=team.id, step_key="ploegverantwoordelijken"))
    db_session.commit()


def _step_done(db_session: Session, team: Team, season: Season) -> bool:
    return (
        db_session.scalar(
            select(AltsienSelectStepProgress).where(
                AltsienSelectStepProgress.season_id == season.id,
                AltsienSelectStepProgress.team_id == team.id,
                AltsienSelectStepProgress.step_key == "ploegverantwoordelijken",
            )
        )
        is not None
    )


def test_moving_the_last_responsible_away_reopens_the_wizard_step(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    team = _create_team(db_session, name="A-team")
    other_team = _create_team(db_session, name="B-team")
    season = _create_season(db_session, name="2026")
    person = _create_team_responsible(db_session, team=team, season=season, name="Jan")
    _mark_step_done(db_session, team, season)

    # Editing without moving keeps the step done.
    assert client.put(f"{URL}/{person.id}", json=_payload(team, season, name="Jan")).status_code == 200
    assert _step_done(db_session, team, season)

    assert client.put(f"{URL}/{person.id}", json=_payload(other_team, season, name="Jan")).status_code == 200
    db_session.expire_all()
    assert not _step_done(db_session, team, season)


def test_moving_one_of_two_responsibles_keeps_the_wizard_step(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    team = _create_team(db_session, name="A-team")
    season = _create_season(db_session, name="2026")
    other_season = _create_season(db_session, name="2027")
    person = _create_team_responsible(db_session, team=team, season=season, name="Jan")
    _create_team_responsible(db_session, team=team, season=season, name="An")
    _mark_step_done(db_session, team, season)

    assert client.put(f"{URL}/{person.id}", json=_payload(team, other_season, name="Jan")).status_code == 200
    db_session.expire_all()
    assert _step_done(db_session, team, season)


def test_deleting_the_last_responsible_reopens_the_wizard_step(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    team = _create_team(db_session, name="A-team")
    season = _create_season(db_session, name="2026")
    person = _create_team_responsible(db_session, team=team, season=season, name="Jan")
    _mark_step_done(db_session, team, season)

    assert client.delete(f"{URL}/{person.id}").status_code == 204
    db_session.expire_all()
    assert not _step_done(db_session, team, season)
