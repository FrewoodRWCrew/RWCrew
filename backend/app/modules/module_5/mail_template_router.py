# Atelier's (module-5) "Instellingen > E-mails" screen: the subject and body
# of the two mails a person gets after a transaction at the counter desk
# ("handout" = Uitgifte after Ophalen, "return" = Inname after Terugbrengen),
# each with an on/off switch, plus a test mail to yourself. Its own APIRouter
# on the module's /api/modules/module-5 prefix (included in app/main.py).
#
# The rendering, placeholders and default texts live in notifications.py. A
# text with an unknown placeholder is refused with HTTP detail
# "unknown_placeholder|<name>", translated under atelier.mailTemplates.errors.

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.mail import OutgoingMail, send_email
from app.db.models.user import User
from app.modules.module_5.deps import require_screen_permission
from app.modules.module_5.notifications import (
    EXAMPLE_VALUES,
    PLACEHOLDERS,
    TEMPLATE_KEYS,
    get_template,
    render,
    unknown_placeholders,
)
from app.schemas.atelier import (
    MailTemplateRequest,
    MailTemplateResponse,
    MailTemplatesResponse,
    MailTestRequest,
    MailTestResponse,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

MAIL_TEMPLATES_SCREEN = "atelier.mailtemplates"


def _check_key(key: str) -> None:
    """Only the two known templates exist."""
    if key not in TEMPLATE_KEYS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mail template not found")


def _check_placeholders(subject: str, body: str) -> None:
    """Refuse a text using a placeholder that doesn't exist (names the first one)."""
    unknown = unknown_placeholders(subject) + unknown_placeholders(body)
    if unknown:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown_placeholder|{unknown[0]}")


@router.get("/mail-templates", response_model=MailTemplatesResponse)
def list_mail_templates(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(MAIL_TEMPLATES_SCREEN, "view")),
) -> MailTemplatesResponse:
    """Both mail texts (the default one while never saved), the placeholders and example values."""
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
    template.updated_by_name = current_user.display_name
    template.updated_at = datetime.now(timezone.utc)
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
    session user's own address."""
    _check_key(key)
    _check_placeholders(payload.subject, payload.body)
    if not current_user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_own_email")
    rendered = render(payload.subject, payload.body, EXAMPLE_VALUES)
    background_tasks.add_task(
        send_email,
        OutgoingMail(
            to=[current_user.email],
            subject=f"{settings.mail_subject_prefix}[Test] {rendered.subject}",
            html=rendered.html,
            text=rendered.text,
        ),
    )
    return MailTestResponse(sent_to=current_user.email)
