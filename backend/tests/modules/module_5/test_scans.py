# Atelier's wristband scans (block 5): the public webhook (token, logging of
# every message, other events, unreadable bodies), the auto-registered
# scanners, team matching, the desk's polling per scanner, using a scan for a
# pick-up / return, the wristband number per festival, the "wristband
# required" switch, the Test-scan endpoint and the rights.

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.festival import Festival

# The block-1 fixtures and helpers, and the desk fixture of block 4.
from tests.modules.module_5.test_desk import DAY, desk  # noqa: F401  (fixtures)
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    _login,
    _make_role,
    _make_user,
    as_atelier,
    world,
)

WEBHOOK = "/api/public/atelier/wristband-scan"
TOKEN = "U7WbDSnefnR4OiE55WbHYzNMA9EOV6"


def _message(first: str = "Anaïs", last: str = "Wydaeghe", number: str = "557087", team: str = "rw TERRAS",
             device: int = 14734, event: str = "crew_participation", token: str = TOKEN, **extra) -> dict:
    """A message shaped like the wristband company's example."""
    return {
        "data": {
            "association": team,
            "attending_group": {"id": "25029", "name": team},
            "device": {"id": device, "name": "SUN0410", "uuid": "LB43225A30936"},
            "id": number,
            "person": {"first_name": first, "last_name": last, **extra},
            "profile": {"id": "1076", "name": "Vrijwilliger The Hive"},
        },
        "event": event,
        "token": token,
    }


@pytest.fixture()
def token(monkeypatch: pytest.MonkeyPatch) -> str:
    """The webhook token configured for the test."""
    monkeypatch.setattr(settings, "atelier_webhook_token", TOKEN)
    return TOKEN


def test_webhook_accepts_logs_and_registers(client: TestClient, as_atelier: TestClient, world: dict, token: str) -> None:
    response = client.post(WEBHOOK, content=json.dumps(_message(size="M")))
    assert response.status_code == 200 and response.json()["status"] == "new"

    # The scanner registered itself; the team matched ignoring case; data.id = wristband number.
    scanners = as_atelier.get(f"{BASE}/desk/scanners").json()
    assert [(scanner["device_id"], scanner["device_name"]) for scanner in scanners] == [("14734", "SUN0410")]
    scans = as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "14734"}).json()
    assert len(scans) == 1
    scan = scans[0]
    assert (scan["first_name"], scan["last_name"], scan["wristband_number"], scan["team_id"], scan["size"], scan["source"]) == (
        "Anaïs", "Wydaeghe", "557087", world["terras"].id, "M", "webhook"
    )
    # Another scanner sees nothing.
    assert as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "999"}).json() == []


def test_webhook_refuses_and_ignores_but_logs(client: TestClient, as_atelier: TestClient, token: str) -> None:
    assert client.post(WEBHOOK, content=json.dumps(_message(token="wrong"))).status_code == 401
    assert client.post(WEBHOOK, content="not json").status_code == 400
    assert client.post(WEBHOOK, content=json.dumps(_message(event="other_event"))).status_code == 200

    log = as_atelier.get(f"{BASE}/scans").json()
    assert [(entry["status"], entry["status_detail"]) for entry in log] == [
        ("ignored", "other_event"), ("refused", "unreadable"), ("refused", "bad_token"),
    ]
    assert log[1]["raw"] == "not json"
    # Nothing waits at the desk.
    assert as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "14734"}).json() == []


def test_no_token_configured_refuses_everything(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "atelier_webhook_token", "")
    assert client.post(WEBHOOK, content=json.dumps(_message(token=""))).status_code == 401


def test_scan_used_for_pick_up_and_return(client: TestClient, as_atelier: TestClient, world: dict, desk: dict, token: str) -> None:
    client.post(WEBHOOK, content=json.dumps(_message()))
    scan = as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "14734"}).json()[0]

    # Ophalen from the scan: no email needed; the wristband number is stored for this festival.
    handout = as_atelier.post(
        f"{BASE}/desk/handouts",
        json={"first_name": "Anaïs", "last_name": "Wydaeghe", "bracelet_number": "557087", "scan_id": scan["id"],
              "festival_id": desk["festival"], "team_id": world["terras"].id, "day": DAY,
              "lines": [{"article_id": desk["apron"], "article_size_id": desk["apron_size"]}]},
    )
    assert handout.status_code == 201 and handout.json()["bracelet_number"] == "557087"
    # The scan no longer waits, and can't be used twice.
    assert as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "14734"}).json() == []
    found = as_atelier.get(f"{BASE}/desk/persons/by-bracelet", params={"festival_id": desk["festival"], "number": "557087"}).json()
    assert found["name"] == "Anaïs Wydaeghe"

    # A second scan of the same wristband → Terugbrengen uses it.
    client.post(WEBHOOK, content=json.dumps(_message()))
    second = as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "14734"}).json()[0]
    line_id = handout.json()["lines"][0]["id"]
    returned = as_atelier.post(
        f"{BASE}/desk/handouts/{handout.json()['id']}/return", json={"line_ids": [line_id], "scan_id": second["id"]}
    )
    assert returned.json()["status"] == "returned"
    log = {entry["id"]: entry for entry in as_atelier.get(f"{BASE}/scans").json()}
    assert log[scan["id"]]["status"] == "used" and log[second["id"]]["status"] == "used"

    # Dismiss ("Negeren").
    client.post(WEBHOOK, content=json.dumps(_message()))
    third = as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "14734"}).json()[0]
    assert as_atelier.post(f"{BASE}/desk/scans/{third['id']}/dismiss").status_code == 204
    assert as_atelier.get(f"{BASE}/desk/scans", params={"device_id": "14734"}).json() == []


def test_wristband_per_festival_and_required_switch(
    as_atelier: TestClient, db_session: Session, world: dict, desk: dict
) -> None:
    def pick_up(first: str, number: str | None, festival_id: int = desk["festival"]):
        return as_atelier.post(
            f"{BASE}/desk/handouts",
            json={"first_name": first, "last_name": "Test", "bracelet_number": number, "festival_id": festival_id,
                  "team_id": world["terras"].id, "day": DAY,
                  "lines": [{"article_id": desk["apron"], "article_size_id": desk["apron_size"]}]},
        )

    assert pick_up("Jan", "100").status_code == 201
    # Same number, same festival, other person → refused.
    assert pick_up("Piet", "100").json()["detail"] == "bracelet_in_use|100|Jan Test"

    # Another festival: the same number may belong to someone else.
    tw = Festival(name="TW Classic", start_date=date(2026, 7, 3), end_date=date(2026, 7, 3), season_id=world["season"].id)
    db_session.add(tw)
    db_session.commit()
    as_atelier.put(
        f"{BASE}/reservations/{tw.id}",
        json={"reservations": [{"team_id": world["terras"].id, "persons": 1,
                                "lines": [{"article_id": desk["apron"], "quantity_per_person": 1}]}]},
    )
    assert pick_up("Piet", "100", tw.id).status_code == 201

    # The switch: without a wristband number a pick-up is refused (unless the person already has one there).
    assert as_atelier.put(f"{BASE}/settings", json={"wristband_required": True}).json()["wristband_required"] is True
    assert pick_up("Karel", None).json()["detail"] == "bracelet_required"
    assert pick_up("Karel", "200").status_code == 201


def test_test_scan_endpoint_and_rights(client: TestClient, as_atelier: TestClient, db_session: Session, world: dict) -> None:
    # No token needed; same processing; marked as a test.
    result = as_atelier.post(f"{BASE}/scans/test", json={"raw": json.dumps(_message(token="whatever", team="Onbekende ploeg"))}).json()
    assert (result["http_status"], result["scan"]["status"], result["scan"]["source"], result["team_name_matched"]) == (
        200, "new", "test", None
    )
    matched = as_atelier.post(f"{BASE}/scans/test", json={"raw": json.dumps(_message())}).json()
    assert matched["team_name_matched"] == "RW terras"
    # A file that isn't a crew scan is logged as such.
    assert as_atelier.post(f"{BASE}/scans/test", json={"raw": "{}"}).json()["scan"]["status"] == "ignored"
    # Scanner labels on the settings screen.
    scanner = as_atelier.get(f"{BASE}/scanners").json()[0]
    assert as_atelier.put(f"{BASE}/scanners/{scanner['id']}", json={"label": "Balie 1"}).json()["label"] == "Balie 1"

    # Someone who may only use the desk can't send test scans or change settings.
    as_atelier.post("/api/auth/logout")
    role = _make_role(db_session, "Balie", {"atelier.desk": (True, True, False, False)})
    _make_user(db_session, world, "balie@example.com", role)
    _login(client, "balie@example.com")
    assert client.post(f"{BASE}/scans/test", json={"raw": "{}"}).status_code == 403
    assert client.put(f"{BASE}/settings", json={"wristband_required": False}).status_code == 403
    assert client.get(f"{BASE}/desk/scanners").status_code == 200
