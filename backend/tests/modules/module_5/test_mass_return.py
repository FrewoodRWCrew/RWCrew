# Atelier's Massa-inname (the Raspberry Pi app): a team's box of clothing is
# read at once and every piece comes back, booked per person who had it out
# (one "Inname" mail each). One tag in the box that isn't a handed-out piece
# refuses the whole box. Its own right: atelier.massreturn "create".

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.mail import OutgoingMail
from app.db.models.atelier_handout_line import AtelierHandoutLine
from app.modules.module_5 import notifications
from tests.modules.module_5.test_desk import DAY, _stock, desk  # noqa: F401  (fixture)
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    _make_role,
    _make_user,
    as_atelier,
    world,
)
from tests.modules.module_5.test_rfid import _assign, _resolve


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[OutgoingMail]:
    """Every mail "sent" during the test."""
    mails: list[OutgoingMail] = []
    monkeypatch.setattr(notifications, "send_email", mails.append)
    return mails


def _hand_out(client: TestClient, world: dict, desk: dict, first: str, email: str | None,
              tags: list[tuple[str, str, int]]):
    """Ophalen by tag for one person: (article, size, tag id) per piece."""
    response = client.post(
        f"{BASE}/desk/handouts",
        json={"first_name": first, "last_name": "Peeters", "email": email, "festival_id": desk["festival"],
              "team_id": world["terras"].id, "day": DAY,
              "lines": [{"article_id": desk[article], "article_size_id": desk[size], "rfid_tag_id": tag_id}
                        for article, size, tag_id in tags]},
    )
    assert response.status_code == 201, response.json()


def _mass_return(client: TestClient, epcs: list[str], **extra):
    return client.post(f"{BASE}/desk/mass-return", json={"epcs": epcs, "source": "pi", **extra})


def _two_persons_out(client: TestClient, world: dict, desk: dict) -> dict[str, int]:
    """Jan has a T-shirt and an apron out, Piet a T-shirt; TS-3 stays in stock."""
    tags = {tag["epc"]: tag["rfid_tag_id"] for tag in _assign(client, ["TS-1", "TS-2", "TS-3"], desk["m"]).json()}
    tags["SCH-1"] = _assign(client, ["SCH-1"], desk["apron_size"]).json()[0]["rfid_tag_id"]
    _hand_out(client, world, desk, "Jan", "jan@example.com", [("tshirt", "m", tags["TS-1"]), ("apron", "apron_size", tags["SCH-1"])])
    _hand_out(client, world, desk, "Piet", None, [("tshirt", "m", tags["TS-2"])])
    return tags


def test_mass_return_books_per_person(as_atelier: TestClient, db_session: Session, world: dict, desk: dict,
                                      sent: list[OutgoingMail]) -> None:
    _two_persons_out(as_atelier, world, desk)
    assert _stock(as_atelier, desk["m"]) == (1, 0, 2)
    # The read tags say who has the piece and for which team.
    out = _resolve(as_atelier, ["TS-1"])["TS-1"]
    assert (out["person_name"], out["team_name"]) == ("Jan Peeters", "RW terras")
    sent.clear()

    booked = _mass_return(as_atelier, ["TS-1", "SCH-1", "TS-2", "TS-1"], reader={"name": "Pi 1", "location": "Atelier"})
    assert booked.status_code == 200, booked.json()
    body = booked.json()
    assert body["pieces"] == 3
    assert [(row["person_name"], row["pieces"], row["mailed"]) for row in body["persons"]] == [
        ("Jan Peeters", 2, True), ("Piet Peeters", 1, False)
    ]
    # Every piece is back (to wash), nothing is out any more.
    assert _stock(as_atelier, desk["m"]) == (1, 2, 0)
    assert all(tag["open_line_id"] is None for tag in _resolve(as_atelier, ["TS-1", "TS-2", "SCH-1"]).values())
    # The lines keep the tag read and that it was booked on the Pi.
    lines = db_session.query(AtelierHandoutLine).all()
    assert {(line.return_epc, line.return_source) for line in lines} == {("TS-1", "pi"), ("TS-2", "pi"), ("SCH-1", "pi")}
    # Only Jan has an email: one Inname mail.
    assert [mail.to for mail in sent] == [["jan@example.com"]]


def test_one_wrong_tag_blocks_the_box(as_atelier: TestClient, world: dict, desk: dict) -> None:
    _two_persons_out(as_atelier, world, desk)
    # TS-3 is in stock (not out), NEW-TAG unknown: nothing is booked.
    refused = _mass_return(as_atelier, ["TS-1", "TS-3", "NEW-TAG"])
    assert refused.status_code == 400
    assert refused.json()["detail"] == "mass_return_blocked|2"
    assert _stock(as_atelier, desk["m"]) == (1, 0, 2)
    assert _resolve(as_atelier, ["TS-1"])["TS-1"]["person_name"] == "Jan Peeters"
    # After taking them out, the box goes through.
    assert _mass_return(as_atelier, ["TS-1"]).status_code == 200
    # An empty box (only blanks) is refused.
    assert _mass_return(as_atelier, ["  "]).json()["detail"] == "mass_return_empty"


def test_mass_return_needs_its_own_right(client: TestClient, db_session: Session, world: dict, desk: dict) -> None:
    client.cookies.clear()
    # A desk worker may do Terugbrengen but not a mass return.
    desk_role = _make_role(db_session, "Balie", {"atelier.desk": (True, True, False, False)})
    _make_user(db_session, world, "balie@example.com", desk_role)
    mass_role = _make_role(db_session, "Inname", {"atelier.massreturn": (True, True, False, False)})
    _make_user(db_session, world, "inname@example.com", mass_role)

    def headers(email: str) -> dict[str, str]:
        tokens = client.post("/api/auth/token", json={"email": email, "password": "password123"}).json()
        return {"Authorization": f"Bearer {tokens['access_token']}"}

    balie, inname = headers("balie@example.com"), headers("inname@example.com")
    assert client.post(f"{BASE}/desk/mass-return", json={"epcs": ["X"]}, headers=balie).status_code == 403
    # The mass-return role may read the tags and book (here refused for the unknown tag, not for the right).
    assert client.post(f"{BASE}/rfid/resolve", json={"epcs": ["X"]}, headers=inname).status_code == 200
    assert client.post(f"{BASE}/desk/mass-return", json={"epcs": ["X"]}, headers=inname).json()["detail"] == "mass_return_blocked|1"
