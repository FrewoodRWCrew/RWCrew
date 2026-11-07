# app/core/mail.py: the CC list travels as Resend's "cc", only on the first
# chunk of a long "to" list (so a CC address never gets the mail twice).
# httpx.post is replaced by a collector, so nothing leaves the machine.

import pytest

from app.core import mail as mail_module
from app.core.mail import MAX_RECIPIENTS_PER_MAIL, OutgoingMail, send_email


class _Response:
    status_code = 200
    text = "{}"


@pytest.fixture()
def posted(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Every payload "posted" to Resend during the test."""
    payloads: list[dict] = []
    monkeypatch.setattr(mail_module.settings, "resend_api_key", "test-key")
    monkeypatch.setattr(mail_module.settings, "mail_from", "noreply@example.com")
    monkeypatch.setattr(mail_module.httpx, "post", lambda url, json, **_kwargs: payloads.append(json) or _Response())
    return payloads


def test_cc_only_on_the_first_chunk(posted: list[dict]) -> None:
    to = [f"user{number}@example.com" for number in range(MAX_RECIPIENTS_PER_MAIL + 1)]
    send_email(OutgoingMail(to=to, subject="S", html="<p>x</p>", text="x", cc=["copy@example.com"]))
    assert len(posted) == 2
    assert posted[0]["cc"] == ["copy@example.com"]
    assert "cc" not in posted[1]


def test_no_cc_key_without_cc(posted: list[dict]) -> None:
    send_email(OutgoingMail(to=["a@example.com"], subject="S", html="<p>x</p>", text="x"))
    assert "cc" not in posted[0]
