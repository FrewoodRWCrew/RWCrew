# This file defines the "StockMaster_reason" table: the reasons a person
# picks when stock leaves or changes (e.g. "Verbruikt", "Defect",
# "Verloren", "Telverschil"), managed on StockMaster's "Instellingen >
# Redenen" screen.

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterReason(Base):
    """One reason that can be chosen on a booking."""

    __tablename__ = "StockMaster_reason"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # The booking type this reason is offered on ("book_out", "count", ...),
    # or empty for "every booking type".
    applies_to: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Inactive reasons stay on old bookings but are no longer offered.
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Who added it.
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
