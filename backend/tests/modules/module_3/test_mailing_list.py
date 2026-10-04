# Tests for Intervention Requests' "Mailing List" settings screen and the
# "new request" mail it drives (app/modules/module_3/notifications.py):
# every new request — staff screen (desktop or phone) or public QR form — mails the
# active addresses on the list, with the delivery-note PDF attached, and a
# mail problem never stops the request from being saved.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import mail as mail_module
from app.core.config import settings
from app.core.mail import MailAttachment, OutgoingMail, send_email
from app.db.models.intervention_requests_mailing_recipient import InterventionRequestsMailingRecipient
from app.modules.module_3 import notifications
from tests.modules.module_3.helpers import create_status, create_user, give_requests_role, grant_access, login

WEB = "/api/modules/module-3"
LIST = f"{WEB}/mailing-list"


@pytest.fixture()
def sent_mails(monkeypatch) -> list[OutgoingMail]:
    """Replace the real Resend call with one that just records each mail."""
    sent: list[OutgoingMail] = []
    monkeypatch.setattr(notifications, "send_email", sent.append)
    return sent


def _boss(db: Session) -> None:
    """A super admin with module-3 access, so every screen right."""
    boss = create_user(db, "boss@example.com", is_super_admin=True)
    grant_access(db, boss, "module-3")


def _add_recipient(db: Session, email: str, *, is_active: bool = True) -> None:
    db.add(InterventionRequestsMailingRecipient(email=email, is_active=is_active))
    db.commit()


# --- The Mailing List screen ------------------------------------------------


def test_mailing_list_crud(client: TestClient, db_session: Session) -> None:
    _boss(db_session)
    login(client, "boss@example.com")

    # Create: the address is stored trimmed and lower-case, a blank name as none.
    created = client.post(LIST, json={"email": " Jan@Example.COM ", "name": " "})
    assert created.status_code == 201
    body = created.json()
    assert (body["email"], body["name"], body["is_active"]) == ("jan@example.com", None, True)

    # Update: rename and pause.
    updated = client.put(f"{LIST}/{body['id']}", json={"email": "jan@example.com", "name": "Jan", "is_active": False})
    assert updated.status_code == 200
    assert (updated.json()["name"], updated.json()["is_active"]) == ("Jan", False)

    # List, then delete.
    assert [row["email"] for row in client.get(LIST).json()] == ["jan@example.com"]
    assert client.delete(f"{LIST}/{body['id']}").status_code == 204
    assert client.get(LIST).json() == []


def test_duplicate_address_is_rejected(client: TestClient, db_session: Session) -> None:
    _boss(db_session)
    login(client, "boss@example.com")
    _add_recipient(db_session, "jan@example.com")

    response = client.post(LIST, json={"email": "JAN@example.com"})

    assert response.status_code == 409


def test_invalid_address_is_rejected(client: TestClient, db_session: Session) -> None:
    _boss(db_session)
    login(client, "boss@example.com")

    response = client.post(LIST, json={"email": "not-an-email"})

    assert response.status_code == 422


def test_requests_permission_does_not_open_the_mailing_list(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "a@example.com")
    grant_access(db_session, user, "module-3")
    give_requests_role(db_session, user, can_view=True, can_create=True, can_edit=True)
    login(client, "a@example.com")

    response = client.get(LIST)

    assert response.status_code == 403


# --- The "new request" mail -------------------------------------------------


def test_staff_created_request_mails_active_recipients_with_pdf(
    client: TestClient, db_session: Session, sent_mails: list[OutgoingMail]
) -> None:
    _boss(db_session)
    status = create_status(db_session, "Nieuw")
    _add_recipient(db_session, "b@example.com")
    _add_recipient(db_session, "a@example.com")
    _add_recipient(db_session, "paused@example.com", is_active=False)
    login(client, "boss@example.com")

    response = client.post(
        f"{WEB}/intervention-requests",
        json={"team_name": "Vereniging <X>", "question": "Kar stuk", "status_id": status.id},
    )

    assert response.status_code == 201
    number = response.json()["request_number"]
    assert len(sent_mails) == 1
    mail = sent_mails[0]
    assert mail.to == ["a@example.com", "b@example.com"]
    assert number in mail.subject and "Vereniging <X>" in mail.subject
    # User-typed text is escaped in the HTML body.
    assert "Vereniging &lt;X&gt;" in mail.html
    assert "Kar stuk" in mail.text
    assert mail.attachments[0].filename == f"{number}.pdf"
    assert mail.attachments[0].content.startswith(b"%PDF")


def test_public_form_request_also_mails(
    client: TestClient, db_session: Session, sent_mails: list[OutgoingMail]
) -> None:
    create_status(db_session, "Nieuw")
    _add_recipient(db_session, "a@example.com")

    response = client.post("/api/public/intervention-requests", json={"team_name": "Ploeg", "question": "Vraag"})

    assert response.status_code == 201
    assert len(sent_mails) == 1


def test_request_by_a_plain_requests_role_also_mails(
    client: TestClient, db_session: Session, sent_mails: list[OutgoingMail]
) -> None:
    # The phone section (/m) creates requests through this same endpoint, as
    # a user who usually only has the requests screen's create right.
    user = create_user(db_session, "a@example.com")
    grant_access(db_session, user, "module-3")
    give_requests_role(db_session, user, can_view=True, can_create=True)
    status = create_status(db_session, "Nieuw")
    _add_recipient(db_session, "list@example.com")
    login(client, "a@example.com")

    response = client.post(
        f"{WEB}/intervention-requests", json={"team_name": "Ploeg", "question": "Vraag", "status_id": status.id}
    )

    assert response.status_code == 201
    assert len(sent_mails) == 1


def test_editing_a_request_does_not_mail(
    client: TestClient, db_session: Session, sent_mails: list[OutgoingMail]
) -> None:
    _boss(db_session)
    status = create_status(db_session, "Nieuw")
    login(client, "boss@example.com")
    body = {"team_name": "Ploeg", "question": "Vraag", "status_id": status.id}
    created = client.post(f"{WEB}/intervention-requests", json=body).json()
    _add_recipient(db_session, "a@example.com")

    client.put(f"{WEB}/intervention-requests/{created['id']}", json={**body, "question": "Anders"})

    assert sent_mails == []


def test_no_active_recipients_means_no_mail(
    client: TestClient, db_session: Session, sent_mails: list[OutgoingMail]
) -> None:
    create_status(db_session, "Nieuw")
    _add_recipient(db_session, "paused@example.com", is_active=False)

    response = client.post("/api/public/intervention-requests", json={"team_name": "Ploeg", "question": "Vraag"})

    assert response.status_code == 201
    assert sent_mails == []


def test_a_failing_mail_never_blocks_the_request(client: TestClient, db_session: Session, monkeypatch) -> None:
    create_status(db_session, "Nieuw")
    _add_recipient(db_session, "a@example.com")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("PDF broke")

    monkeypatch.setattr(notifications, "build_delivery_note_pdf", _boom)

    response = client.post("/api/public/intervention-requests", json={"team_name": "Ploeg", "question": "Vraag"})

    assert response.status_code == 201


# --- app/core/mail.py (the Resend call itself) ------------------------------


def _mail(to: list[str]) -> OutgoingMail:
    return OutgoingMail(
        to=to, subject="S", html="<p>H</p>", text="T", attachments=[MailAttachment("a.pdf", b"%PDF-1")]
    )


def test_send_email_is_skipped_without_configuration(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(mail_module.httpx, "post", lambda *a, **k: calls.append(k))

    send_email(_mail(["a@example.com"]))

    assert calls == []


def test_send_email_chunks_recipients_and_swallows_errors(monkeypatch) -> None:
    calls = []

    def _fake_post(url, *, json, headers, timeout):
        calls.append(json)
        raise RuntimeError("network down")

    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "mail_from", "RWCrew <noreply@example.com>")
    monkeypatch.setattr(mail_module.httpx, "post", _fake_post)

    # 120 addresses → 3 calls of at most 50; the error is logged, not raised.
    send_email(_mail([f"u{i}@example.com" for i in range(120)]))

    assert [len(call["to"]) for call in calls] == [50, 50, 20]
    assert calls[0]["attachments"][0]["filename"] == "a.pdf"
