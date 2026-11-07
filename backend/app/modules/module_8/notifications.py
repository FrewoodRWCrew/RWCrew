# The mails Altsien Select (module-8) sends. Today one: "ploegfiche" — once
# every step of a team's Ploeg Wizard is done, the Kernlid can ask for the
# Ploegfiche PDF (everything confirmed) in their own mailbox. Subject and body
# are written by an admin on "Instellingen > E-mails"
# (AltsienSelect_mail_template), as plain text with placeholders such as
# {ploeg}; this file holds the placeholder list and default texts (the check
# and rendering are shared with Atelier, app/shared/mail_template.py).
#
# **Every Altsien Select mail goes through build_altsien_mail**: it always
# adds the CC list of AltsienSelect_settings, so the organisation gets a copy
# of everything. Like module_3/module_5: the mail is built inside the
# request's DB session and only the network call (send_email) runs as a
# FastAPI background task.

from datetime import datetime, timezone

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.mail import MailAttachment, OutgoingMail, send_email
from app.core.timezone import belgian_today
from app.db.models.altsien_select_mail_template import AltsienSelectMailTemplate
from app.db.models.altsien_select_settings import AltsienSelectSettings
from app.schemas.altsien_select import TeamStateResponse
from app.shared.mail_template import render
from app.shared.mail_template import unknown_placeholders as shared_unknown_placeholders

# The mails, by template key.
PLOEGFICHE = "ploegfiche"
TEMPLATE_KEYS = (PLOEGFICHE,)

# Every placeholder a subject or body may use, in the order the settings
# screen lists them.
PLACEHOLDERS = ("naam", "ploeg", "jaartal", "datum", "stappen")

# The texts used until an admin changes them (also seeded by the migration).
DEFAULT_TEMPLATES: dict[str, tuple[str, str]] = {
    PLOEGFICHE: (
        "Ploegfiche {ploeg} – {jaartal}",
        "Dag {naam},\n\n"
        "Alle stappen van de Ploeg Wizard voor ploeg {ploeg} ({jaartal}) zijn afgerond.\n"
        "In bijlage vind je de Ploegfiche met alle bevestigde gegevens:\n"
        "{stappen}\n\n"
        "Verstuurd op {datum}.\n\n"
        "Bedankt!\n"
        "Altsien",
    ),
}

# Example values for the settings screen's preview and test mail.
EXAMPLE_VALUES: dict[str, str] = {
    "naam": "Jan Peeters",
    "ploeg": "Chiro Werchter",
    "jaartal": "2027",
    "datum": "15-05-2027",
    "stappen": "- Festivals\n- Afleverlocaties\n- Ploegverantwoordelijken\n- Producten\n- Speciale aanvragen",
}

# The id of the single AltsienSelect_settings row.
SETTINGS_ROW_ID = 1


def unknown_placeholders(text: str) -> list[str]:
    """The placeholders in a text that don't exist (in order, once each)."""
    return shared_unknown_placeholders(text, PLACEHOLDERS)


def get_template(db: Session, key: str) -> AltsienSelectMailTemplate:
    """The stored template, or (when its row is missing) an unsaved one with
    the default text, so sending always has something to work with."""
    row = db.scalar(select(AltsienSelectMailTemplate).where(AltsienSelectMailTemplate.key == key))
    if row is None:
        subject, body = DEFAULT_TEMPLATES[key]
        row = AltsienSelectMailTemplate(key=key, subject=subject, body=body, active=True)
    return row


def get_settings(db: Session) -> AltsienSelectSettings:
    """The single settings row, or (when the migration's row is missing, e.g.
    in tests) an empty unsaved one; a writer adds it to the session."""
    row = db.get(AltsienSelectSettings, SETTINGS_ROW_ID)
    if row is None:
        row = AltsienSelectSettings(id=SETTINGS_ROW_ID, cc_addresses="")
    return row


def split_addresses(stored: str) -> list[str]:
    """The stored ";"-separated CC list as a list."""
    return [part for part in (piece.strip() for piece in stored.split(";")) if part]


def normalize_addresses(addresses: list[str]) -> list[str]:
    """Trimmed, lowercase, without empties or duplicates (first one kept)."""
    result: list[str] = []
    for address in addresses:
        cleaned = address.strip().lower()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def cc_addresses(db: Session) -> list[str]:
    """Everyone who gets a copy of every Altsien Select mail."""
    row = db.get(AltsienSelectSettings, SETTINGS_ROW_ID)
    return split_addresses(row.cc_addresses) if row is not None else []


def build_altsien_mail(
    db: Session,
    key: str,
    to: list[str],
    values: dict[str, str],
    attachments: list[MailAttachment] | None = None,
) -> OutgoingMail | None:
    """The mail of this template, always with the CC list (minus addresses
    already in "to"), or None when there's no address or the template is
    switched off. Every Altsien Select mail must be built here."""
    recipients = normalize_addresses(to)
    if not recipients:
        return None
    template = get_template(db, key)
    if not template.active:
        return None
    rendered = render(template.subject, template.body, values)
    return OutgoingMail(
        to=recipients,
        cc=[address for address in cc_addresses(db) if address not in recipients],
        subject=f"{settings.mail_subject_prefix}{rendered.subject}",
        html=rendered.html,
        text=rendered.text,
        attachments=attachments or [],
    )


def ploegfiche_values(state: TeamStateResponse, user_name: str, step_titles: dict[str, str]) -> dict[str, str]:
    """The placeholder values of the Ploegfiche mail: who asked, the team, the
    year, today (Belgian) and the done steps, one per line."""
    done = {item.step_key for item in state.progress}
    steps = [f"- {step_titles.get(step.key, step.label)}" for step in state.steps if step.key in done]
    return {
        "naam": user_name,
        "ploeg": state.team.name,
        "jaartal": state.season_name,
        "datum": belgian_today().strftime("%d-%m-%Y"),
        "stappen": "\n".join(steps) or "-",
    }


def queue_mail(background_tasks: BackgroundTasks, mail: OutgoingMail) -> None:
    """Send the mail once the response has gone out (errors are logged by send_email)."""
    background_tasks.add_task(send_email, mail)


def stamp(row: AltsienSelectMailTemplate | AltsienSelectSettings, user_name: str) -> None:
    """Note who changed a template or the settings, and when."""
    row.updated_by_name = user_name
    row.updated_at = datetime.now(timezone.utc)
