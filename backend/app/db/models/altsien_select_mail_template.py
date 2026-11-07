# This file defines the "AltsienSelect_mail_template" table: the texts of the
# mails Altsien Select sends — one row per kind (today only "ploegfiche": the
# Ploegfiche PDF a Kernlid can ask for once every wizard step is done), with a
# subject, a body with placeholders such as {ploeg} and an on/off switch.
# Edited on Altsien Select's "Instellingen > E-mails" screen; read and
# rendered by module_8/notifications.py, which also holds the default texts.
# Same shape as Atelier_mail_template.

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AltsienSelectMailTemplate(Base):
    """One mail text (subject + body) of Altsien Select."""

    __tablename__ = "AltsienSelect_mail_template"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which mail, e.g. "ploegfiche".
    key: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    # Plain text with placeholders; line breaks are kept in the mail.
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Off = this mail is never sent.
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    # Who changed it last (snapshot of the name) and when.
    updated_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
