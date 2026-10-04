# This file defines the "InterventionRequests_mailing_recipient" database
# table: the mailing list that gets an email (with the delivery-note PDF
# attached) every time a new intervention request arrives — whether it came
# from the public QR form, the staff screen or the phone app (see
# app/modules/module_3/notifications.py). Managed on the module's
# "Settings > Mailing List" screen.

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InterventionRequestsMailingRecipient(Base):
    """One row per email address on the new-request mailing list."""

    __tablename__ = "InterventionRequests_mailing_recipient"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The address to mail, stored lower-case (see the schemas) and unique so
    # the same person can't be on the list twice.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # An optional display name, only to make the list easier to read.
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Unchecked = temporarily paused (e.g. someone on holiday) without
    # removing them from the list. Only active rows receive mails.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
