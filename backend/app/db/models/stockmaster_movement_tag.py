# This file defines the "StockMaster_movement_tag" table: which RFID tags a
# booking made on the RWCrew Pi moved, and from which place to which (the
# per-piece trace of StockMaster). Written only by module_4/tag_service.py.
#
# One row per tag per booking. It is both the tag's history (Tag-historiek)
# and what an "Ongedaan maken" needs to put the tags back where they were.
# The EPC is kept as text, so the trace survives deleting or relinking the
# tag in TagScan's register.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterMovementTag(Base):
    """One tag moved by one booking: from which place to which."""

    __tablename__ = "StockMaster_movement_tag"

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("StockMaster_document.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The ledger line the piece was counted in; empty when only the tag's
    # place changed (e.g. a count where the quantity already matched).
    movement_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_movement.id", ondelete="SET NULL"), nullable=True
    )
    rfid_tag_id: Mapped[int | None] = mapped_column(
        ForeignKey("Tagscan_rfid_tag.id", ondelete="SET NULL"), index=True, nullable=True
    )
    epc: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_product.id", ondelete="SET NULL"), nullable=True
    )

    # The place before and after (see RfidTag.stock_place; NULL = unknown).
    from_place: Mapped[str | None] = mapped_column(String(12), nullable=True)
    from_kar_id: Mapped[int | None] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="SET NULL"), nullable=True
    )
    from_trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_kar_trip.id", ondelete="SET NULL"), nullable=True
    )
    # The booking that had set the "from" place (a reversal hands the tag
    # back to it, so undoing an older booking afterwards still finds it).
    from_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_document.id", ondelete="SET NULL"), nullable=True
    )
    to_place: Mapped[str | None] = mapped_column(String(12), nullable=True)
    to_kar_id: Mapped[int | None] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="SET NULL"), nullable=True
    )
    to_trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_kar_trip.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
