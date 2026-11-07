# The mails Atelier sends to a person after a transaction at the counter desk:
# "Uitgifte" after Ophalen and "Inname" after Terugbrengen, to the person's
# own (optional) email address. Their subject and body are written by an
# admin on "Instellingen > E-mails" (Atelier_mail_template), as plain text
# with placeholders such as {voornaam} or {stuks}; this file holds the
# placeholder list and the default texts; the placeholder check and the
# rendering are shared with Altsien Select (app/shared/mail_template.py).
#
# Like module_3/notifications.py: the mail is built inside the request's own
# DB session (after the booking is committed) and only the network call
# (app.core.mail.send_email) runs as a FastAPI background task, so a mail
# problem can never undo or delay the booking. No email or a switched-off
# template = no mail, silently.

import logging
from collections.abc import Iterable

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.mail import OutgoingMail, send_email
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_handout import AtelierHandout
from app.db.models.atelier_handout_line import AtelierHandoutLine
from app.db.models.atelier_mail_template import AtelierMailTemplate
from app.db.models.atelier_person import AtelierPerson
from app.db.models.atelier_size import AtelierSize
from app.db.models.festival import Festival
from app.db.models.team import Team
from app.modules.module_5.desk_service import open_lines_of
from app.shared.mail_template import RenderedMail, render  # noqa: F401  (re-exported for callers/tests)
from app.shared.mail_template import unknown_placeholders as shared_unknown_placeholders

logger = logging.getLogger(__name__)

# The two mails, by template key.
HANDOUT = "handout"
RETURN = "return"
TEMPLATE_KEYS = (HANDOUT, RETURN)

# Every placeholder a subject or body may use, in the order the settings
# screen lists them.
PLACEHOLDERS = ("voornaam", "familienaam", "ploeg", "festival", "dag", "polsband", "stuks", "openstaand")

# The fit as written in the mails.
_FIT_NAMES = {"women": "Dames", "men": "Heren", "unisex": "Unisex"}

# The texts used until an admin changes them (also seeded by the migration).
DEFAULT_TEMPLATES: dict[str, tuple[str, str]] = {
    HANDOUT: (
        "Je atelierkledij voor {festival}",
        "Dag {voornaam},\n\n"
        "Je hebt op {dag} aan de balie van het atelier deze kledij opgehaald voor ploeg {ploeg}:\n"
        "{stuks}\n\n"
        "Breng alles na je shift terug naar de balie van het atelier.\n\n"
        "Bedankt!\n"
        "Het atelier",
    ),
    RETURN: (
        "Je kledij is teruggebracht – {festival}",
        "Dag {voornaam},\n\n"
        "We hebben deze kledij goed terug ontvangen:\n"
        "{stuks}\n\n"
        "Nog in jouw bezit:\n"
        "{openstaand}\n\n"
        "Bedankt!\n"
        "Het atelier",
    ),
}

# Example values for the settings screen's preview and test mail.
EXAMPLE_VALUES: dict[str, str] = {
    "voornaam": "Jan",
    "familienaam": "Peeters",
    "ploeg": "VIP",
    "festival": "Rock Werchter",
    "dag": "03-07-2027",
    "polsband": "123456",
    "stuks": "- T-shirt · M · Heren\n- Hoodie · L · Unisex",
    "openstaand": "- Hoodie · L · Unisex",
}

# What {openstaand} says when the person has nothing out any more.
NOTHING_OPEN = "niets"


def unknown_placeholders(text: str) -> list[str]:
    """The placeholders in a text that don't exist (in order, once each)."""
    return shared_unknown_placeholders(text, PLACEHOLDERS)


def get_template(db: Session, key: str) -> AtelierMailTemplate:
    """The stored template, or (when its row is missing) an unsaved one with
    the default text, so sending always has something to work with."""
    row = db.scalar(select(AtelierMailTemplate).where(AtelierMailTemplate.key == key))
    if row is None:
        subject, body = DEFAULT_TEMPLATES[key]
        row = AtelierMailTemplate(key=key, subject=subject, body=body, active=True)
    return row


def _piece_list(db: Session, lines: Iterable[AtelierHandoutLine]) -> str:
    """The pieces as "- article · size · fit", one per line."""
    rows = []
    for line in lines:
        article = db.get(AtelierArticle, line.article_id)
        size = db.get(AtelierSize, db.get(AtelierArticleSize, line.article_size_id).size_id)
        rows.append(f"- {article.name} · {size.name} · {_FIT_NAMES.get(size.fit, size.fit)}")
    return "\n".join(rows)


def desk_values(
    db: Session, person: AtelierPerson, handout: AtelierHandout, lines: list[AtelierHandoutLine], bracelet: str | None
) -> dict[str, str]:
    """The placeholder values of one desk transaction: the person, the
    festival/team/day of the pick-up, this transaction's pieces and what the
    person still has out afterwards."""
    still_out = open_lines_of(db, person.id)
    return {
        "voornaam": person.first_name,
        "familienaam": person.last_name,
        "ploeg": db.get(Team, handout.team_id).name,
        "festival": db.get(Festival, handout.festival_id).name,
        "dag": handout.day.strftime("%d-%m-%Y"),
        "polsband": bracelet or "-",
        "stuks": _piece_list(db, lines),
        "openstaand": _piece_list(db, still_out) if still_out else NOTHING_OPEN,
    }


def build_mail(db: Session, key: str, to: str | None, values: dict[str, str]) -> OutgoingMail | None:
    """The mail of this template for one address, or None when there's no
    address or the template is switched off."""
    if not to:
        return None
    template = get_template(db, key)
    if not template.active:
        return None
    rendered = render(template.subject, template.body, values)
    return OutgoingMail(
        to=[to],
        subject=f"{settings.mail_subject_prefix}{rendered.subject}",
        html=rendered.html,
        text=rendered.text,
    )


def queue_desk_mail(
    db: Session,
    key: str,
    person: AtelierPerson,
    handout: AtelierHandout,
    lines: list[AtelierHandoutLine],
    bracelet: str | None,
    background_tasks: BackgroundTasks,
) -> None:
    """Called by the desk endpoints right after committing a pick-up (key
    HANDOUT) or a return (key RETURN): builds the mail now, sends it once the
    response has gone out. Errors are logged and ignored."""
    try:
        mail = build_mail(db, key, person.email, desk_values(db, person, handout, lines, bracelet))
    except Exception:
        logger.exception("Building the Atelier %s mail for person %s failed", key, person.id)
        return
    if mail is not None:
        background_tasks.add_task(send_email, mail)
