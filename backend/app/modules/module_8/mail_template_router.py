# Altsien Select's (module-8) mails, as their own APIRouter on the module's
# /api/modules/module-8 prefix (included in app/main.py):
#
# - "Instellingen > E-mails" (screen altsienselect.mailtemplates): the subject
#   and body of each mail with an on/off switch, a test mail to yourself, and
#   the CC list — the addresses that get a copy of every Altsien Select mail.
# - POST /wizard/{team_id}/ploegfiche/mail: once every wizard step of a team
#   is done, the Kernlid gets the Ploegfiche PDF in their own mailbox (+ CC).
#
# Placeholders, default texts and the CC rule live in notifications.py. A text
# with an unknown placeholder is refused with HTTP detail
# "unknown_placeholder|<name>", translated under altsienSelect.mailTemplates.errors.

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.mail import MailAttachment, OutgoingMail
from app.db.models.user import User
from app.modules.module_8 import notifications
from app.modules.module_8.deps import get_season_or_404, get_team_in_scope, require_screen_permission
from app.modules.module_8.notifications import (
    EXAMPLE_VALUES,
    PLACEHOLDERS,
    PLOEGFICHE,
    TEMPLATE_KEYS,
    build_altsien_mail,
    get_settings,
    get_template,
    normalize_addresses,
    ploegfiche_values,
    split_addresses,
    stamp,
    unknown_placeholders,
)
from app.modules.module_8.ploegfiche_pdf import LABELS, build_ploegfiche_pdf
from app.modules.module_8.service import build_team_state
from app.schemas.altsien_select import (
    MailSettingsRequest,
    MailSettingsResponse,
    MailTemplateRequest,
    MailTemplateResponse,
    MailTemplatesResponse,
    MailTestRequest,
    MailTestResponse,
    PloegficheMailResponse,
)
from app.shared.mail_template import render

router = APIRouter(prefix="/api/modules/module-8", tags=["Altsien Select"])

MAIL_TEMPLATES_SCREEN = "altsienselect.mailtemplates"
WIZARD_SCREEN = "altsienselect.wizard"


def _check_key(key: str) -> None:
    """Only the known templates exist."""
    if key not in TEMPLATE_KEYS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mail template not found")


def _check_placeholders(subject: str, body: str) -> None:
    """Refuse a text using a placeholder that doesn't exist (names the first one)."""
    unknown = unknown_placeholders(subject) + unknown_placeholders(body)
    if unknown:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown_placeholder|{unknown[0]}")


# --- Mail texts -------------------------------------------------------------


@router.get("/mail-templates", response_model=MailTemplatesResponse)
def list_mail_templates(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(MAIL_TEMPLATES_SCREEN, "view")),
) -> MailTemplatesResponse:
    """Every mail text (the default one while never saved), the placeholders and example values."""
    return MailTemplatesResponse(
        templates=[MailTemplateResponse.model_validate(get_template(db, key)) for key in TEMPLATE_KEYS],
        placeholders=list(PLACEHOLDERS),
        example_values=EXAMPLE_VALUES,
    )


@router.put("/mail-templates/{key}", response_model=MailTemplateResponse)
def put_mail_template(
    key: str,
    payload: MailTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(MAIL_TEMPLATES_SCREEN, "edit")),
) -> MailTemplateResponse:
    """Save one mail text (subject, body, on/off)."""
    _check_key(key)
    subject, body = payload.subject.strip(), payload.body.strip()
    _check_placeholders(subject, body)
    template = get_template(db, key)
    # A template that was never saved is stored now.
    if template.id is None:
        db.add(template)
    template.subject = subject
    template.body = body
    template.active = payload.active
    stamp(template, current_user.display_name)
    db.commit()
    return MailTemplateResponse.model_validate(template)


@router.post("/mail-templates/{key}/test", response_model=MailTestResponse)
def post_mail_test(
    key: str,
    payload: MailTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_screen_permission(MAIL_TEMPLATES_SCREEN, "edit")),
) -> MailTestResponse:
    """Send the text as typed (saved or not) with the example values to the
    session user's own address only — a test never goes to the CC list."""
    _check_key(key)
    _check_placeholders(payload.subject, payload.body)
    if not current_user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_own_email")
    rendered = render(payload.subject, payload.body, EXAMPLE_VALUES)
    notifications.queue_mail(
        background_tasks,
        OutgoingMail(
            to=[current_user.email],
            subject=f"{settings.mail_subject_prefix}[Test] {rendered.subject}",
            html=rendered.html,
            text=rendered.text,
        ),
    )
    return MailTestResponse(sent_to=current_user.email)


# --- CC list ----------------------------------------------------------------


def _settings_response(db: Session) -> MailSettingsResponse:
    """The CC list as the screen shows it."""
    row = get_settings(db)
    return MailSettingsResponse(
        cc_addresses=split_addresses(row.cc_addresses),
        updated_by_name=row.updated_by_name,
        updated_at=row.updated_at,
    )


@router.get("/mail-settings", response_model=MailSettingsResponse)
def get_mail_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(MAIL_TEMPLATES_SCREEN, "view")),
) -> MailSettingsResponse:
    """The addresses that get a copy of every Altsien Select mail."""
    return _settings_response(db)


@router.put("/mail-settings", response_model=MailSettingsResponse)
def put_mail_settings(
    payload: MailSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(MAIL_TEMPLATES_SCREEN, "edit")),
) -> MailSettingsResponse:
    """Replace the CC list (lowercased, duplicates removed; each address was
    already checked as a valid email by the schema)."""
    row = get_settings(db)
    # A row that was never stored (no migration seed) is stored now.
    db.add(row)
    row.cc_addresses = ";".join(normalize_addresses([str(address) for address in payload.cc_addresses]))
    stamp(row, current_user.display_name)
    db.commit()
    return _settings_response(db)


# --- Ploegfiche by mail -------------------------------------------------------


@router.post("/wizard/{team_id}/ploegfiche/mail", response_model=PloegficheMailResponse)
def mail_ploegfiche(
    team_id: int,
    season_id: int,
    background_tasks: BackgroundTasks,
    locale: Literal["nl", "en"] = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WIZARD_SCREEN, "view")),
) -> PloegficheMailResponse:
    """Mail the team's Ploegfiche PDF (everything confirmed) to the session
    user, with the CC list in copy. Only once every wizard step is done."""
    season = get_season_or_404(db, season_id)
    team = get_team_in_scope(db, current_user, team_id)
    state = build_team_state(db, current_user, season, team)

    # Every step must be done: the PDF is "everything confirmed".
    done = {item.step_key for item in state.progress}
    if any(step.key not in done for step in state.steps):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="steps_not_done")
    if not current_user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_own_email")

    # The mail's step names follow the PDF's language.
    step_titles = LABELS.get(locale, LABELS["nl"])["steps"]
    values = ploegfiche_values(state, current_user.display_name, step_titles)
    attachment = MailAttachment(
        filename=f"Ploegfiche {team.name} {season.name}.pdf",
        content=build_ploegfiche_pdf(state, locale),
    )
    mail = build_altsien_mail(db, PLOEGFICHE, [current_user.email], values, [attachment])
    if mail is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="template_inactive")
    notifications.queue_mail(background_tasks, mail)
    return PloegficheMailResponse(sent_to=current_user.email, cc=list(mail.cc))
