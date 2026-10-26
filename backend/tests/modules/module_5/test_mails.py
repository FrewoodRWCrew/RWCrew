# Atelier's desk mails: after Ophalen and after Terugbrengen (the person-level
# return) the person gets the "Uitgifte" / "Inname" mail built from the admin's
# templates — none without an email or with the template switched off, one for
# a return spanning several pick-ups — and the "Instellingen > E-mails"
# endpoints (placeholder check, test mail, rights). send_email is replaced by a
# collector, so nothing leaves the machine.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.mail import OutgoingMail
from app.modules.module_5 import mail_template_router, notifications
from app.modules.module_5.notifications import render, unknown_placeholders

from tests.modules.module_5.test_desk import _pick_up, desk  # noqa: F401  (fixture)
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    _login,
    _make_role,
    _make_user,
    as_atelier,
    world,
)


@pytest.fixture()
def sent(monkeypatch: pytest.MonkeyPatch) -> list[OutgoingMail]:
    """Every mail "sent" during the test."""
    mails: list[OutgoingMail] = []
    monkeypatch.setattr(notifications, "send_email", mails.append)
    monkeypatch.setattr(mail_template_router, "send_email", mails.append)
    return mails


def test_placeholders_and_rendering() -> None:
    assert unknown_placeholders("Dag {voornaam}, {naam} en {naam} {}") == ["naam", ""]
    rendered = render("Hoi {voornaam}\n", "<b>{voornaam}</b>\n{stuks}", {"voornaam": "A&B", "stuks": "- x\n- y"})
    assert rendered.subject == "Hoi A&B\n"
    assert rendered.text == "<b>A&B</b>\n- x\n- y"
    # In HTML the text and the values are escaped and line breaks kept.
    assert "&lt;b&gt;A&amp;B&lt;/b&gt;<br>- x<br>- y" in rendered.html


def test_mail_after_pick_up_and_one_mail_per_return(
    as_atelier: TestClient, world: dict, desk: dict, sent: list[OutgoingMail]
) -> None:
    first = _pick_up(as_atelier, world, desk, [("tshirt", "m")], bracelet="RW-1").json()
    second = _pick_up(as_atelier, world, desk, [("apron", "apron_size")]).json()
    # One "Uitgifte" mail per pick-up, to the person's address, with the pieces.
    assert [mail.to for mail in sent] == [["jan@example.com"], ["jan@example.com"]]
    assert sent[0].subject == "Je atelierkledij voor Rock Werchter"
    assert "Dag Jan," in sent[0].text and "- T-shirt · M · Heren" in sent[0].text and "ploeg RW terras" in sent[0].text
    assert "03-07-2026" in sent[0].text

    # Both pieces come back in one transaction (two pick-ups): one "Inname" mail.
    sent.clear()
    person_id = first["person_id"]
    lines = [first["lines"][0]["id"], second["lines"][0]["id"]]
    response = as_atelier.post(f"{BASE}/desk/persons/{person_id}/return", json={"line_ids": lines})
    assert response.status_code == 200
    assert [row["status"] for row in response.json()] == ["returned", "returned"]
    assert len(sent) == 1
    assert "- T-shirt · M · Heren\n- Schort · OneSize · Unisex" in sent[0].text
    assert "Nog in jouw bezit:\nniets" in sent[0].text

    # The per-pick-up return sends no mail.
    sent.clear()
    third = _pick_up(as_atelier, world, desk, [("tshirt", "m")]).json()
    sent.clear()
    as_atelier.post(f"{BASE}/desk/handouts/{third['id']}/return", json={"line_ids": [third["lines"][0]["id"]]})
    assert sent == []


def test_person_return_refuses_someone_elses_piece(as_atelier: TestClient, world: dict, desk: dict) -> None:
    jan = _pick_up(as_atelier, world, desk, [("tshirt", "m")]).json()
    an = _pick_up(as_atelier, world, desk, [("apron", "apron_size")], first="An", email="an@example.com").json()
    response = as_atelier.post(
        f"{BASE}/desk/persons/{jan['person_id']}/return", json={"line_ids": [an["lines"][0]["id"]]}
    )
    assert (response.status_code, response.json()["detail"]) == (404, "line_not_found")


def test_no_mail_without_email_or_when_switched_off(
    as_atelier: TestClient, world: dict, desk: dict, sent: list[OutgoingMail]
) -> None:
    _pick_up(as_atelier, world, desk, [("apron", "apron_size")], first="Zonder", email="")
    assert sent == []

    # Switched off: no "Uitgifte" mail any more.
    template = {"subject": "Hallo {voornaam}", "body": "Je kreeg:\n{stuks}", "active": False}
    assert as_atelier.put(f"{BASE}/mail-templates/handout", json=template).status_code == 200
    _pick_up(as_atelier, world, desk, [("tshirt", "m")])
    assert sent == []


def test_template_screen(as_atelier: TestClient, world: dict, sent: list[OutgoingMail]) -> None:
    # Both templates with their default text, the placeholders and example values.
    data = as_atelier.get(f"{BASE}/mail-templates").json()
    assert [row["key"] for row in data["templates"]] == ["handout", "return"]
    assert "{stuks}" in data["templates"][0]["body"] and "openstaand" in data["placeholders"]

    # Saving keeps the changer; an unknown placeholder is refused.
    saved = as_atelier.put(
        f"{BASE}/mail-templates/return", json={"subject": "Terug: {festival}", "body": "Dag {voornaam}", "active": True}
    ).json()
    assert (saved["subject"], saved["updated_by_name"]) == ("Terug: {festival}", "atelier@example.com")
    bad = as_atelier.put(f"{BASE}/mail-templates/return", json={"subject": "x", "body": "Dag {naam}", "active": True})
    assert (bad.status_code, bad.json()["detail"]) == (400, "unknown_placeholder|naam")
    assert as_atelier.put(f"{BASE}/mail-templates/other", json={"subject": "x", "body": "y", "active": True}).status_code == 404

    # The test mail goes to yourself, filled with the example values.
    test = as_atelier.post(f"{BASE}/mail-templates/handout/test", json={"subject": "Hoi {voornaam}", "body": "{stuks}"})
    assert test.json() == {"sent_to": "atelier@example.com"}
    assert (sent[0].to, sent[0].subject) == (["atelier@example.com"], "[Test] Hoi Jan")


def test_template_rights(client: TestClient, db_session: Session, world: dict) -> None:
    # View only: may read, not save or send a test.
    role = _make_role(db_session, "Lezer", {"atelier.mailtemplates": (True, False, False, False)})
    _make_user(db_session, world, "lezer@example.com", role)
    _login(client, "lezer@example.com")
    assert client.get(f"{BASE}/mail-templates").status_code == 200
    payload = {"subject": "x", "body": "y", "active": True}
    assert client.put(f"{BASE}/mail-templates/handout", json=payload).status_code == 403
    assert client.post(f"{BASE}/mail-templates/handout/test", json={"subject": "x", "body": "y"}).status_code == 403
