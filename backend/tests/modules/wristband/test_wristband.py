# The wristband scans as a shared part: every message kept as a .json file and
# browsable in the Scans module, which counters show a scan (only teams with
# a reservation in the season, plus unmatched teams), the first counter to use
# a scan winning, and sending a test scan from Scans, Atelier and Walkies with
# each module's own right.

import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.festival import Festival
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.tagscan_role import TagscanRole
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_settings import TagscanSettings
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.db.models.walkies_role import WalkiesRole
from app.db.models.walkies_role_permission import WalkiesRolePermission
from app.db.models.walkies_screen import WalkiesScreen
from app.db.models.walkies_user_role import WalkiesUserRole
from app.db.models.wristband_scan import WristbandScan
from app.modules.module_1.screens import sync_screens as sync_scans_screens
from app.modules.module_6.screens import sync_screens as sync_walkies_screens
from app.modules.wristband.webhook_token import hash_token
from tests.modules.module_5.test_desk import DAY, desk  # noqa: F401  (fixtures)
from tests.modules.module_5.test_masterdata import BASE, _login, as_atelier, world  # noqa: F401  (fixtures)
from tests.modules.module_5.test_scans import TOKEN, WEBHOOK, _message

SCANS = "/api/modules/module-1/wristband"
WALKIES = "/api/modules/module-6"


@pytest.fixture()
def token(db_session: Session) -> str:
    db_session.add(TagscanSettings(id=1, wristband_token_hash=hash_token(TOKEN)))
    db_session.commit()
    return TOKEN


def _user_with_module(db: Session, email: str, module_key: str, name: str, sort_order: int) -> User:
    """A user with access to this module (created when missing)."""
    module = db.scalar(select(Module).where(Module.key == module_key))
    if module is None:
        module = Module(key=module_key, name=name, sort_order=sort_order)
        db.add(module)
        db.flush()
    user = User(email=email, hashed_password=hash_password("password123"), display_name=email)
    db.add(user)
    db.flush()
    db.add(UserModuleAccess(user_id=user.id, module_id=module.id))
    db.commit()
    return user


def _scans_user(db: Session, email: str, keys: dict[str, tuple[bool, bool, bool, bool]]) -> None:
    """A Scans user with (view, create, edit, delete) per screen key."""
    sync_scans_screens(db)
    user = _user_with_module(db, email, "module-1", "Scans", 1)
    role = TagscanRole(name=email)
    db.add(role)
    db.flush()
    screens = {screen.key: screen for screen in db.scalars(select(TagscanScreen)).all()}
    for key, (view, create, edit, delete) in keys.items():
        db.add(TagscanRolePermission(role_id=role.id, screen_id=screens[key].id, can_view=view, can_create=create, can_edit=edit, can_delete=delete))
    db.add(TagscanUserRole(user_id=user.id, role_id=role.id))
    db.commit()


def _walkies_user(db: Session, email: str, can_send: bool) -> None:
    """A Walkies user with view (and maybe create) on the Test-scan screen."""
    sync_walkies_screens(db)
    user = _user_with_module(db, email, "module-6", "Walkies", 6)
    role = WalkiesRole(name=email)
    db.add(role)
    db.flush()
    screen = db.scalar(select(WalkiesScreen).where(WalkiesScreen.key == "walkies.scantest"))
    db.add(WalkiesRolePermission(role_id=role.id, screen_id=screen.id, can_view=True, can_create=can_send))
    db.add(WalkiesUserRole(user_id=user.id, role_id=role.id))
    db.commit()


ALL = (True, True, True, True)
EVERY_SCANS_SCREEN = {
    "tagscan.wristband-files": ALL,
    "tagscan.wristband-scans": ALL,
    "tagscan.wristband-scanners": ALL,
    "tagscan.wristband-test": ALL,
    "tagscan.settings": ALL,
}


def _send(client: TestClient, **fields) -> dict:
    response = client.post(WEBHOOK, content=json.dumps(_message(**fields)))
    assert response.status_code == 200, response.text
    return response.json()


def _desk_ids(client: TestClient, **params) -> list[int]:
    return [scan["id"] for scan in client.get(f"{BASE}/desk/scans", params=params).json()]


# --- The .json files ---------------------------------------------------------------------


def test_message_is_kept_as_a_file_and_browsable(
    client: TestClient, db_session: Session, world: dict, wristband_folder: Path, token: str
) -> None:
    sent = _send(client, first="Jan")
    day_folders = list(wristband_folder.iterdir())
    assert len(day_folders) == 1
    files = list(day_folders[0].iterdir())
    assert len(files) == 1 and files[0].name.endswith(f"_{sent['scan_id']}.json")
    assert json.loads(files[0].read_text(encoding="utf-8"))["data"]["person"]["first_name"] == "Jan"

    _scans_user(db_session, "scans@example.com", EVERY_SCANS_SCREEN)
    _login(client, "scans@example.com")
    tree = client.get(f"{SCANS}/files/tree").json()
    assert [child["name"] for child in tree["children"]] == [day_folders[0].name]
    listed = client.get(f"{SCANS}/files", params={"path": day_folders[0].name}).json()
    assert [entry["name"] for entry in listed] == [files[0].name]
    content = client.get(f"{SCANS}/files/content", params={"path": listed[0]["path"]}).json()
    assert "Jan" in content["content"]

    # Deleting the file keeps the table row.
    assert client.post(f"{SCANS}/files/delete", json={"paths": [listed[0]["path"]]}).json() == {"deleted": 1}
    assert not files[0].exists()
    assert [row["id"] for row in client.get(f"{SCANS}/scans").json()] == [sent["scan_id"]]


def test_path_outside_the_json_folder_is_refused(client: TestClient, db_session: Session, world: dict) -> None:
    _scans_user(db_session, "scans@example.com", EVERY_SCANS_SCREEN)
    _login(client, "scans@example.com")
    assert client.get(f"{SCANS}/files", params={"path": "../.."}).status_code == 400
    assert client.get(f"{SCANS}/files/content", params={"path": "../secret.txt"}).status_code == 400
    assert client.post(f"{SCANS}/files/delete", json={"paths": ["../secret.txt"]}).status_code == 400


def test_failed_file_write_never_loses_the_scan(
    client: TestClient, world: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, token: str
) -> None:
    # The JSON "folder" is a file, so writing into it fails.
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x")
    monkeypatch.setattr(settings, "wristband_source_dir", str(blocker))
    assert _send(client)["status"] == "new"


def test_refused_senders_leave_no_file(client: TestClient, world: dict, wristband_folder: Path, token: str) -> None:
    # Anyone can post to the public address: without the token nothing lands on disk.
    assert client.post(WEBHOOK, content=json.dumps(_message(token="wrong"))).status_code == 401
    assert client.post(WEBHOOK, content="not json").status_code == 400
    assert list(wristband_folder.iterdir()) == []


# --- Which counter shows a scan ------------------------------------------------------------


def test_only_teams_with_a_reservation_show_at_the_atelier_desk(
    client: TestClient, as_atelier: TestClient, db_session: Session, world: dict, desk: dict, token: str
) -> None:
    with_reservation = _send(client, team="RW terras")["scan_id"]
    without = _send(client, team="VIP")["scan_id"]
    unmatched = _send(client, team="Ploeg die we niet kennen")["scan_id"]

    # VIP has no package: hidden. A name we can't match stays, so nobody gets stuck.
    assert set(_desk_ids(as_atelier)) == {with_reservation, unmatched}

    # It isn't lost: the log shows it as new, waiting at no counter.
    log = {row["id"]: row for row in as_atelier.get(f"{BASE}/wristband-test/log").json()}
    assert log[without]["status"] == "new" and log[without]["visible_at"] == []
    assert log[with_reservation]["visible_at"] == ["atelier"]


def test_a_reservation_at_any_festival_of_the_season_counts(
    client: TestClient, as_atelier: TestClient, db_session: Session, world: dict, desk: dict, token: str
) -> None:
    # terras' only package is at Rock Werchter; another festival doesn't change that.
    db_session.add(Festival(name="TW Classic", start_date=date(2026, 7, 3), end_date=date(2026, 7, 3), season_id=world["season"].id))
    db_session.commit()
    scan_id = _send(client)["scan_id"]
    assert _desk_ids(as_atelier, season_id=world["season"].id) == [scan_id]
    # Another season: no reservation there.
    assert _desk_ids(as_atelier, season_id=world["previous"].id) == []


def test_without_season_the_last_open_one_counts(
    client: TestClient, as_atelier: TestClient, db_session: Session, world: dict, desk: dict, token: str
) -> None:
    scan_id = _send(client)["scan_id"]
    assert _desk_ids(as_atelier) == [scan_id]
    # A newer, still empty open season takes over.
    db_session.add(Season(name="2027", periode_open=True))
    db_session.commit()
    assert _desk_ids(as_atelier) == []


def test_first_counter_to_use_a_scan_wins(
    client: TestClient, as_atelier: TestClient, db_session: Session, world: dict, desk: dict, token: str
) -> None:
    scan_id = _send(client)["scan_id"]
    scan = db_session.get(WristbandScan, scan_id)
    scan.status, scan.used_by_module = "used", "module-6"
    db_session.commit()
    refused = as_atelier.post(
        f"{BASE}/desk/handouts",
        json={"first_name": "Anaïs", "last_name": "Wydaeghe", "scan_id": scan_id, "festival_id": desk["festival"],
              "team_id": world["terras"].id, "day": DAY,
              "lines": [{"article_id": desk["apron"], "article_size_id": desk["apron_size"]}]},
    )
    assert refused.status_code == 400 and refused.json()["detail"] == "scan_not_waiting"


# --- Test scans from three modules ---------------------------------------------------------


def test_test_scan_from_scans_and_walkies(client: TestClient, db_session: Session, world: dict, wristband_folder: Path) -> None:
    _scans_user(db_session, "scans@example.com", EVERY_SCANS_SCREEN)
    _login(client, "scans@example.com")
    result = client.post(f"{SCANS}/wristband-test/send", json={"raw": json.dumps(_message(team="VIP"))}).json()
    assert result["scan"]["source"] == "test" and result["team_name_matched"] == "VIP"
    # VIP has no reservation: the screen can say why nothing pops up.
    assert result["visible_at"] == []
    assert next(wristband_folder.rglob("*.json")).name.endswith("_test.json")
    client.post("/api/auth/logout")

    _walkies_user(db_session, "walkies@example.com", can_send=True)
    _login(client, "walkies@example.com")
    assert client.post(f"{WALKIES}/wristband-test/send", json={"raw": json.dumps(_message())}).status_code == 200
    assert len(client.get(f"{WALKIES}/wristband-test/log").json()) == 2


def test_each_module_needs_its_own_right(client: TestClient, db_session: Session, world: dict) -> None:
    _scans_user(db_session, "rfid@example.com", {"tagscan.dashboard": (True, False, False, False)})
    _walkies_user(db_session, "kijker@example.com", can_send=False)
    _login(client, "kijker@example.com")
    assert client.get(f"{WALKIES}/wristband-test/log").status_code == 200
    assert client.post(f"{WALKIES}/wristband-test/send", json={"raw": "{}"}).status_code == 403
    # Walkies rights don't open the Scans module.
    assert client.get(f"{SCANS}/scans").status_code == 403
    client.post("/api/auth/logout")

    _login(client, "rfid@example.com")
    assert client.get(f"{SCANS}/files/tree").status_code == 403
    assert client.get(f"{SCANS}/scans").status_code == 403
    assert client.post(f"{SCANS}/wristband-test/send", json={"raw": "{}"}).status_code == 403


def test_scanner_label_and_settings_in_scans(client: TestClient, db_session: Session, world: dict, token: str) -> None:
    _send(client)
    _scans_user(db_session, "scans@example.com", EVERY_SCANS_SCREEN)
    _login(client, "scans@example.com")
    scanner = client.get(f"{SCANS}/scanners").json()[0]
    assert client.put(f"{SCANS}/scanners/{scanner['id']}", json={"label": "Balie 1"}).json()["label"] == "Balie 1"
    details = client.get(f"{SCANS}/settings").json()
    assert details["webhook_path"] == WEBHOOK and details["webhook_token_configured"] is True


def test_scan_filters(client: TestClient, db_session: Session, world: dict, token: str) -> None:
    first = _send(client, team="RW terras", device=1)["scan_id"]
    second = _send(client, team="VIP", device=2)["scan_id"]
    _scans_user(db_session, "scans@example.com", EVERY_SCANS_SCREEN)
    _login(client, "scans@example.com")
    assert [row["id"] for row in client.get(f"{SCANS}/scans", params={"team": "terr"}).json()] == [first]
    assert [row["id"] for row in client.get(f"{SCANS}/scans", params={"device_id": "2"}).json()] == [second]
    assert client.get(f"{SCANS}/scans", params={"status": "used"}).json() == []


# --- The webhook token ---------------------------------------------------------------------


def _post(client: TestClient, key: str) -> int:
    return client.post(WEBHOOK, content=json.dumps(_message(token=key))).status_code


def test_generated_token_is_accepted_replaced_and_revoked(client: TestClient, db_session: Session, world: dict) -> None:
    _scans_user(db_session, "scans@example.com", EVERY_SCANS_SCREEN)
    _login(client, "scans@example.com")
    assert client.get(f"{SCANS}/settings").json()["webhook_token_configured"] is False
    assert _post(client, "") == 401

    first = client.post(f"{SCANS}/settings/token").json()["token"]
    assert first.startswith("wristband_")
    assert _post(client, first) == 200
    assert _post(client, "wristband_wrong") == 401
    details = client.get(f"{SCANS}/settings").json()
    assert details["webhook_token_configured"] is True and details["webhook_token_last_used_at"] is not None

    # The key is never stored or sent again.
    row = db_session.get(TagscanSettings, 1)
    assert row.wristband_token_hash == hash_token(first) and first not in row.wristband_token_hash
    assert first not in client.get(f"{SCANS}/settings").text

    # A new one stops the old one, and resets "last used".
    second = client.post(f"{SCANS}/settings/token").json()["token"]
    assert _post(client, first) == 401
    assert client.get(f"{SCANS}/settings").json()["webhook_token_last_used_at"] is None
    assert _post(client, second) == 200

    # Revoked: nothing is accepted.
    assert client.delete(f"{SCANS}/settings/token").status_code == 204
    assert _post(client, second) == 401
    assert client.get(f"{SCANS}/settings").json()["webhook_token_configured"] is False


def test_only_edit_on_settings_may_change_the_token(client: TestClient, db_session: Session, world: dict) -> None:
    _scans_user(db_session, "kijker@example.com", {"tagscan.settings": (True, False, False, False)})
    _login(client, "kijker@example.com")
    assert client.get(f"{SCANS}/settings").status_code == 200
    assert client.post(f"{SCANS}/settings/token").status_code == 403
    assert client.delete(f"{SCANS}/settings/token").status_code == 403
