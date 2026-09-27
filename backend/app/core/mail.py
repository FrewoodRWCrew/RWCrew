# A tiny, reusable "send an email" helper for the whole backend, built on
# Resend's HTTP API (https://resend.com/docs/api-reference/emails/send-email)
# and the httpx library we already depend on — so no extra (possibly
# compiled) package is needed, see CLAUDE.md's Python 3.14 gotcha.
#
# Sending mail is always a side effect "on top of" the real work (e.g.
# saving a new intervention request), so send_email() never raises: every
# problem is logged and swallowed, and the caller's work stays done.

import base64
import logging
from dataclasses import dataclass, field

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"

# Resend accepts at most 50 addresses in one mail's "to" list, so longer
# recipient lists are split into several mails of this size.
MAX_RECIPIENTS_PER_MAIL = 50

# How long to wait for Resend before giving up on one call, in seconds.
REQUEST_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class MailAttachment:
    """One file attached to a mail: its file name and raw bytes."""

    filename: str
    content: bytes


@dataclass(frozen=True)
class OutgoingMail:
    """Everything needed to send one mail, ready to hand to send_email()
    (e.g. from a FastAPI background task, after the request's own database
    session is already gone).
    """

    to: list[str]
    subject: str
    html: str
    text: str
    attachments: list[MailAttachment] = field(default_factory=list)


def send_email(mail: OutgoingMail) -> None:
    """Send one mail through Resend. Skips (with a log line) when no API
    key or sender is configured, and never raises.
    """
    # Nothing to send, or sending isn't configured in this environment.
    if not mail.to:
        return
    if not settings.resend_api_key or not settings.mail_from:
        logger.info("Mail %r not sent: RESEND_API_KEY/MAIL_FROM not configured", mail.subject)
        return

    # Attachments travel as base64 text inside the JSON body.
    attachments = [
        {"filename": attachment.filename, "content": base64.b64encode(attachment.content).decode("ascii")}
        for attachment in mail.attachments
    ]

    # One API call per chunk of at most MAX_RECIPIENTS_PER_MAIL addresses.
    for start in range(0, len(mail.to), MAX_RECIPIENTS_PER_MAIL):
        recipients = mail.to[start : start + MAX_RECIPIENTS_PER_MAIL]
        payload = {
            "from": settings.mail_from,
            "to": recipients,
            "subject": mail.subject,
            "html": mail.html,
            "text": mail.text,
        }
        if attachments:
            payload["attachments"] = attachments

        try:
            response = httpx.post(
                RESEND_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            # Resend answers 200 with the new mail's id; anything else is an
            # error whose body explains why (bad key, unverified domain, ...).
            if response.status_code >= 400:
                logger.error(
                    "Resend refused mail %r (%s): %s", mail.subject, response.status_code, response.text[:500]
                )
        except Exception:
            # Network trouble, timeouts, ... — log it, never break the caller.
            logger.exception("Sending mail %r through Resend failed", mail.subject)
