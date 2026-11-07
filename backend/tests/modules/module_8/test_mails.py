# Altsien Select's mails: the "Instellingen > E-mails" endpoints (texts,
# placeholder check, test mail, CC list, rights) and the Ploegfiche PDF mail a
# Kernlid can ask for once every wizard step is done — to their own address,
# with the CC list in copy and the PDF attached. send_email is replaced by a
# collector, so nothing leaves the machine.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.mail import OutgoingMail
from app.db.models.altsien_select_screen import AltsienSelectScreen
from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.altsien_select_role_permission import AltsienSelectRolePermission
from app.modules.module_8 import notifications
from app.modules.module_8.steps import STEP_DEFINITIONS

from tests.modules.module_8.conftest import AltsienWorld, login

BASE = "/api/modules/module-8"


@pytest.fixture()
def sent(monkeypatch: pytest.MonkeyPatch) -> list[OutgoingMail]:
    """Every mail "sent" during the test."""
    mails: list[OutgoingMail] = []
    monkeypatch.setattr(notifications, "send_email", mails.append)
    return mails


def _grant_mail_screen(db: Session, world: AltsienWorld, *, edit: bool) -> None:
    """Give the organisation role view (and maybe edit) on the E-mails screen."""
    screen = db.scalar(select(AltsienSelectScreen).where(AltsienSelectScreen.key == "altsienselect.mailtemplates"))
    db.add(
        AltsienSelectRolePermission(
            role_id=world.organisation_role.id, screen_id=screen.id, can_view=True, can_edit=edit
        )
    )
    db.commit()


@pytest.fixture()
def as_admin(client: TestClient, world: AltsienWorld, make_user, db_session: Session) -> TestClient:
    """An organisation user who may edit the mail texts and CC list."""
    _grant_mail_screen(db_session, world, edit=True)
    make_user("admin@example.com", world.organisation_role)
    login(client, "admin@example.com")
    return client


def _complete_all(db: Session, world: AltsienWorld) -> None:
    """Mark every wizard step of own_team done (whatever the steps are)."""
    for step in STEP_DEFINITIONS:
        db.add(AltsienSelectStepProgress(season_id=world.season.id, team_id=world.own_team.id, step_key=step.key))
    db.commit()


def _mail_url(world: AltsienWorld, team_id: int | None = None) -> str:
    return f"{BASE}/wizard/{team_id or world.own_team.id}/ploegfiche/mail?season_id={world.season.id}&locale=nl"


def test_templates_and_placeholder_check(as_admin: TestClient) -> None:
    body = as_admin.get(f"{BASE}/mail-templates").json()
    assert [template["key"] for template in body["templates"]] == ["ploegfiche"]
    assert body["placeholders"] == ["naam", "ploeg", "jaartal", "datum", "stappen"]

    bad = as_admin.put(
        f"{BASE}/mail-templates/ploegfiche", json={"subject": "Hoi {voornaam}", "body": "x", "active": True}
    )
    assert bad.status_code == 400 and bad.json()["detail"] == "unknown_placeholder|voornaam"

    saved = as_admin.put(
        f"{BASE}/mail-templates/ploegfiche", json={"subject": " Fiche {ploeg} ", "body": "Dag {naam}", "active": True}
    )
    assert saved.status_code == 200 and saved.json()["subject"] == "Fiche {ploeg}"
    assert saved.json()["updated_by_name"] == "admin@example.com"
    assert as_admin.put(f"{BASE}/mail-templates/other", json={"subject": "a", "body": "b", "active": True}).status_code == 404


def test_cc_list_is_validated_and_normalized(as_admin: TestClient) -> None:
    assert as_admin.get(f"{BASE}/mail-settings").json()["cc_addresses"] == []
    assert as_admin.put(f"{BASE}/mail-settings", json={"cc_addresses": ["geen-adres"]}).status_code == 422

    saved = as_admin.put(
        f"{BASE}/mail-settings", json={"cc_addresses": ["Org@Example.com", "org@example.com", "b@example.com"]}
    )
    assert saved.status_code == 200
    assert saved.json()["cc_addresses"] == ["org@example.com", "b@example.com"]
    assert as_admin.get(f"{BASE}/mail-settings").json()["cc_addresses"] == ["org@example.com", "b@example.com"]


def test_test_mail_goes_only_to_yourself(as_admin: TestClient, sent: list[OutgoingMail]) -> None:
    as_admin.put(f"{BASE}/mail-settings", json={"cc_addresses": ["org@example.com"]})
    response = as_admin.post(f"{BASE}/mail-templates/ploegfiche/test", json={"subject": "Fiche {ploeg}", "body": "Dag {naam}"})
    assert response.json() == {"sent_to": "admin@example.com"}
    assert sent[0].to == ["admin@example.com"] and sent[0].cc == []
    assert sent[0].subject == "[Test] Fiche Chiro Werchter" and sent[0].text == "Dag Jan Peeters"


def test_mail_screen_rights(client: TestClient, world: AltsienWorld, make_user, db_session: Session) -> None:
    # A Kernlid without the screen sees nothing; view-only can't save.
    make_user("kernlid@example.com", world.kernlid_role, [world.own_team])
    login(client, "kernlid@example.com")
    assert client.get(f"{BASE}/mail-templates").status_code == 403
    _grant_mail_screen(db_session, world, edit=False)
    make_user("viewer@example.com", world.organisation_role)
    login(client, "viewer@example.com")
    assert client.get(f"{BASE}/mail-settings").status_code == 200
    assert client.put(f"{BASE}/mail-settings", json={"cc_addresses": []}).status_code == 403


def test_ploegfiche_mail_needs_every_step(
    as_kernlid: TestClient, world: AltsienWorld, sent: list[OutgoingMail]
) -> None:
    response = as_kernlid.post(_mail_url(world))
    assert response.status_code == 400 and response.json()["detail"] == "steps_not_done"
    assert sent == []


def test_ploegfiche_mail_with_pdf_and_cc(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session, sent: list[OutgoingMail]
) -> None:
    settings_row = notifications.get_settings(db_session)
    settings_row.cc_addresses = "org@example.com;kernlid@example.com"
    db_session.add(settings_row)
    _complete_all(db_session, world)

    response = as_kernlid.post(_mail_url(world))
    assert response.status_code == 200
    # The Kernlid's own address isn't repeated in CC.
    assert response.json() == {"sent_to": "kernlid@example.com", "cc": ["org@example.com"]}
    mail = sent[0]
    assert mail.to == ["kernlid@example.com"] and mail.cc == ["org@example.com"]
    assert mail.subject == "Ploegfiche Chiro Werchter – 2026"
    assert "Dag kernlid@example.com," in mail.text and "- Festivals" in mail.text
    assert mail.attachments[0].filename == "Ploegfiche Chiro Werchter 2026.pdf"
    assert mail.attachments[0].content.startswith(b"%PDF")


def test_ploegfiche_mail_scope_and_switched_off(
    as_kernlid: TestClient, world: AltsienWorld, db_session: Session, sent: list[OutgoingMail]
) -> None:
    _complete_all(db_session, world)
    # Another team is outside the Kernlid's scope.
    assert as_kernlid.post(_mail_url(world, world.other_team.id)).status_code == 404

    # A switched-off template sends nothing.
    template = notifications.get_template(db_session, notifications.PLOEGFICHE)
    template.active = False
    db_session.add(template)
    db_session.commit()
    response = as_kernlid.post(_mail_url(world))
    assert response.status_code == 409 and response.json()["detail"] == "template_inactive"
    assert sent == []
