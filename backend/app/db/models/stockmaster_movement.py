# This file defines the "StockMaster_movement" table: the stock ledger.
# One row per product moved in a booking (StockMaster_document), from one
# place to another:
#   - "free"     the free stock on the product's fixed bin in its warehouse
#   - "kar"      inside a kar standing in the warehouse (from/to_kar_id)
#   - "external" outside our stock (supplier, team/festival, used, lost...)
#
# Rows are never edited or deleted; the current stock per place lives in
# StockMaster_balance and can always be rebuilt from this ledger.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterMovement(Base):
    """One product moved in one booking: how many, from where, to where."""

    __tablename__ = "StockMaster_movement"

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("StockMaster_document.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # No cascade: a product with stock history can't be deleted in MasterData
    # (its delete endpoint refuses it with a clear message).
    product_id: Mapped[int] = mapped_column(ForeignKey("MasterData_product.id"), index=True, nullable=False)

    # Always a whole number above zero; the direction is in from/to.
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    from_bucket: Mapped[str] = mapped_column(String(10), nullable=False)
    from_kar_id: Mapped[int | None] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="SET NULL"), index=True, nullable=True
    )
    to_bucket: Mapped[str] = mapped_column(String(10), nullable=False)
    to_kar_id: Mapped[int | None] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # The product's warehouse + bin at booking time, so the history still
    # shows where it lay after the bin is changed in MasterData.
    bin_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Later: the TagScan scan line this movement was booked from. Unique, so
    # one scanned line can never be booked twice.
    tagscan_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("Tagscan_line_data.id", ondelete="SET NULL"), unique=True, nullable=True
    )

    # Who booked it and when — the same as the document's, repeated so a
    # ledger line read on its own still tells who did it.
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
