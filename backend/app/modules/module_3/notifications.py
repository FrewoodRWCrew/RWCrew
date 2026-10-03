# The "a new intervention request has arrived" mail, sent to every active
# address on the module's Mailing List (Settings > Mailing List) — for
# requests from both entry points: the staff screen (router.py, used by the
# desktop screen and the phone section /m alike) and the public QR form
# (public_router.py).
#
# Split in two on purpose: build_new_request_mail() does the database work
# (recipients, team name, PDF) inside the request's own DB session, and
# only the slow network call (app.core.mail.send_email) is handed to a
# FastAPI background task — so the caller gets its 201 straight away and a
# mail problem can never undo or delay saving the request.

import logging
from html import escape

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.mail import MailAttachment, OutgoingMail, send_email
from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_requests_mailing_recipient import InterventionRequestsMailingRecipient
from app.modules.module_3.intervention_request_pdf import build_delivery_note_pdf
from app.modules.module_3.service import resolve_team_name

logger = logging.getLogger(__name__)

# Where the link in the mail points to, relative to settings.app_public_url.
REQUESTS_SCREEN_PATH = "/nl/modules/module-3/intervention-requests"


def _format_datetime(value) -> str | None:
    """dd-mm-yyyy HH:mm, the same format as the PDF and the web screens."""
    return value.strftime("%d-%m-%Y %H:%M") if value is not None else None


def build_new_request_mail(db: Session, request: InterventionRequest) -> OutgoingMail | None:
    """Build the mail for one freshly created request, or None when the
    mailing list has no active addresses (then there's nothing to send).
    """
    recipients = list(
        db.scalars(
            select(InterventionRequestsMailingRecipient.email)
            .where(InterventionRequestsMailingRecipient.is_active.is_(True))
            .order_by(InterventionRequestsMailingRecipient.email)
        ).all()
    )
    if not recipients:
        return None

    team_name = resolve_team_name(db, request)

    # Every field worth knowing at a glance, in the mail's (Dutch) wording.
    fields: list[tuple[str, str | None]] = [
        ("Aanvraagnummer", request.request_number),
        ("Ingediend op", _format_datetime(request.submitted_at)),
        ("Ploeg", team_name or None),
        ("Kar nummer", request.cart_number),
        ("Zone", request.zone),
        ("Afleverplaats", request.delivery_location),
        ("Voorkeur moment van levering", _format_datetime(request.preferred_delivery_at)),
        ("Naam medewerker", request.employee_name),
        ("Mobiel nummer medewerker", request.employee_phone),
        ("Vraag / Opmerking", request.question),
    ]

    # The "open in RWCrew" link, only when the public address is configured.
    link = f"{settings.app_public_url.rstrip('/')}{REQUESTS_SCREEN_PATH}" if settings.app_public_url else None

    subject = f"{settings.mail_subject_prefix}Nieuwe interventie-aanvraag {request.request_number}"
    if team_name:
        subject += f" – {team_name}"

    # Plain-text version, for mail clients that don't show HTML.
    text_lines = ["Er is een nieuwe interventie-aanvraag binnengekomen.", ""]
    text_lines += [f"{label}: {value or '-'}" for label, value in fields]
    if link:
        text_lines += ["", f"Bekijk alle aanvragen: {link}"]

    # HTML version: a simple two-column table; every value is escaped since
    # most fields come straight from the (public, anonymous) request form.
    rows = "".join(
        f'<tr><td style="padding:4px 12px 4px 0;font-weight:bold;vertical-align:top">{escape(label)}</td>'
        f'<td style="padding:4px 0;white-space:pre-wrap">{escape(value or "-")}</td></tr>'
        for label, value in fields
    )
    html = (
        '<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937">'
        "<p>Er is een nieuwe interventie-aanvraag binnengekomen.</p>"
        f"<table>{rows}</table>"
        + (f'<p><a href="{escape(link)}">Bekijk alle aanvragen in RWCrew</a></p>' if link else "")
        + "<p>De leveringsbon zit als PDF in bijlage.</p></div>"
    )

    pdf_bytes = build_delivery_note_pdf(request, team_name=team_name, locale="nl")

    return OutgoingMail(
        to=recipients,
        subject=subject,
        html=html,
        text="\n".join(text_lines),
        attachments=[MailAttachment(filename=f"{request.request_number}.pdf", content=pdf_bytes)],
    )


def queue_new_request_mail(db: Session, request: InterventionRequest, background_tasks: BackgroundTasks) -> None:
    """Called by every "create request" endpoint right after saving: builds
    the mail now and sends it once the response has gone out. Any error
    while building it is logged and ignored, the request stays saved.
    """
    try:
        mail = build_new_request_mail(db, request)
    except Exception:
        logger.exception("Building the new-request mail for %s failed", request.request_number)
        return
    if mail is not None:
        background_tasks.add_task(send_email, mail)
