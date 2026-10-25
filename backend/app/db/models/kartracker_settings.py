# This file defines the "KarTracker_settings" table: a single-row (id=1)
# record of KarTracker-wide settings, edited on the module's "Instellingen"
# screen ("kartracker.settings"). For now it holds the karcode formula: the
# Excel-like expression that turns a kar number into the code of the kar's
# lock (see app/modules/module_2/karcode_formula.py, the only place it is
# checked and computed). The migration inserts the row with the default
# formula, so it normally always exists.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class KarTrackerSettings(Base):
    """A single row (id=1) of KarTracker-wide settings."""

    __tablename__ = "KarTracker_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The karcode formula, e.g. "LEFT(kar*500+3118; 4)".
    karcode_formula: Mapped[str] = mapped_column(Text, nullable=False)

    # Who last saved the formula: the user (kept NULL if that user is
    # deleted) plus a snapshot of their name, shown on the screen.
    karcode_updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    karcode_updated_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    karcode_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
