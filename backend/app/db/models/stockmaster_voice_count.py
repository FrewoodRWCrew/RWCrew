# This file defines the "StockMaster_voice_count" table: one row per voice
# count made on the phone (/m/module-4/voice-count). Someone scans a kar's QR
# code, chooses Ophalen or Terugbrengen and says what is there; the recognised
# products and quantities are its lines (StockMaster_voice_count_line).
#
# Phase 1 only stores the count (status "new"); it doesn't change stock yet.
# Booking it into StockMaster (filling document_id, status "booked") is a later
# phase. Only app/modules/module_4/voice_count_service.py writes this table.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Why the kar was counted: goods picked up (Ophalen) or brought back (Terugbrengen).
DIRECTIONS = ("pickup", "return")
# new = saved, waiting; booked = turned into a StockMaster booking (later phase);
# cancelled = thrown away on the desktop "Spraaktellingen" screen.
STATUSES = ("new", "booked", "cancelled")


class StockMasterVoiceCount(Base):
    """One voice count of one kar: who counted, when, and why."""

    __tablename__ = "StockMaster_voice_count"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The season it was counted in (the module's current season at save time).
    season_id: Mapped[int] = mapped_column(ForeignKey("MasterData_season.id"), index=True, nullable=False)

    # The scanned kar, plus a copy of its number so the list stays readable if
    # the kar is later removed from KarTracker.
    kar_id: Mapped[int | None] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kar_nummer: Mapped[str] = mapped_column(String(50), nullable=False)

    # "pickup" (Ophalen) or "return" (Terugbrengen), see DIRECTIONS.
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    # "new", "booked" or "cancelled", see STATUSES.
    status: Mapped[str] = mapped_column(String(10), index=True, default="new", nullable=False)

    # The StockMaster booking made from it (later phase), if any.
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_document.id", ondelete="SET NULL"), nullable=True
    )

    # Who counted (always the logged-in user) plus a copy of their name.
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Who cancelled it and when (only for status "cancelled").
    cancelled_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
