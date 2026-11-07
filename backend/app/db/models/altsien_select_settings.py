# This file defines the "AltsienSelect_settings" table: Altsien Select-wide
# settings, always one row (id 1, seeded by its migration). Today only the
# addresses that get a copy (CC) of every mail Altsien Select sends, set on
# "Instellingen > E-mails" and added by module_8/notifications.py.

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AltsienSelectSettings(Base):
    """The single settings row of Altsien Select."""

    __tablename__ = "AltsienSelect_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The CC addresses, ";"-separated, lowercase, each a valid email (checked
    # by the API), no duplicates. Empty = nobody in copy.
    cc_addresses: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)

    # Who changed it last (snapshot of the name) and when.
    updated_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
