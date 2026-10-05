# This file defines the "StockMaster_document" table: one row per booking
# made in StockMaster (Inboeken, Kar laden, Uitboeken, Kar vertrekt, Kar
# terug, Kar uitladen, Telling, or the reversal of one of those). A booking
# groups one or more ledger lines (StockMaster_movement) that were posted
# together, e.g. "load kar K047 with 6 products".
#
# Bookings are never edited or deleted: a mistake is undone by a reversal,
# which is a new document of type "reversal" pointing back to the original
# (reversal_of_id) — see app/modules/module_4/stock_service.py.
#
# Every booking is stored under the logged-in user who made it
# (created_by), plus a copy of their name (created_by_name) so the history
# still shows who booked even after that user is removed.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterDocument(Base):
    """One booking: its type, context (season/kar/team/festival) and who made it."""

    __tablename__ = "StockMaster_document"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Readable number shown to people and printed on the PDFs, e.g.
    # "SM-2026-00123" (Belgian year + the row id).
    doc_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)

    # What kind of booking this is: book_in, book_out, kar_load, kar_unload,
    # kar_dispatch, kar_return, count or reversal (see stock_service.py).
    doc_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    # The season the booking belongs to (the module's own season dropdown).
    # No cascade: a season with bookings can't silently wipe the history.
    season_id: Mapped[int] = mapped_column(ForeignKey("MasterData_season.id"), index=True, nullable=False)

    # The kar the booking is about (load/unload/dispatch/return/count of a
    # kar, or "uitboeken" out of a kar), plus a copy of its number so the
    # history stays readable if the kar is later removed from KarTracker.
    kar_id: Mapped[int | None] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kar_nummer: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # The other kar on a kar-to-kar move ("Kar laden" from another kar).
    from_kar_id: Mapped[int | None] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="SET NULL"), nullable=True
    )
    from_kar_nummer: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Where a dispatched kar goes (Kar vertrekt / Kar terug).
    team_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_team.id", ondelete="SET NULL"), nullable=True)
    festival_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_festival.id", ondelete="SET NULL"), nullable=True
    )

    # Delivery note, order number or any free reference.
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Why stock left or changed (required on Uitboeken, used on Telling).
    reason_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_reason.id", ondelete="SET NULL"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "posted", or "reversed" once a reversal document cancelled it.
    status: Mapped[str] = mapped_column(String(20), default="posted", nullable=False)
    # On a reversal document: the booking it cancels.
    reversal_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_document.id", ondelete="SET NULL"), nullable=True
    )

    # Where the booking came from: "manual" (a screen) or, later, "tagscan"
    # (an automated booking from a TagScan CSV, with its scan file).
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    tagscan_header_id: Mapped[int | None] = mapped_column(
        ForeignKey("Tagscan_header_data.id", ondelete="SET NULL"), nullable=True
    )

    # Who made the booking (always the logged-in user, taken from the
    # session on the server) and when.
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
