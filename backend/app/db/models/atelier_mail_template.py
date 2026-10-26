# This file defines the "Atelier_mail_template" table: the texts of the mails
# Atelier sends to a person after a transaction at the counter desk — one row
# per kind ("handout" after Ophalen, "return" after Terugbrengen), with a
# subject, a body with placeholders such as {voornaam} and an on/off switch.
# Edited on Atelier's "Instellingen > E-mails" screen; read and rendered by
# module_5/notifications.py, which also holds the default texts.

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierMailTemplate(Base):
    """One mail text (subject + body) of the counter desk."""

    __tablename__ = "Atelier_mail_template"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which mail: "handout" (Uitgifte) or "return" (Inname).
    key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    # Plain text with placeholders; line breaks are kept in the mail.
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Off = this mail is never sent.
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    # Who changed it last (snapshot of the name) and when.
    updated_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
