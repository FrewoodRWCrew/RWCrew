# This file defines the "StockMaster_balance" table: the current stock of
# one product in one place — its free stock (kar_id empty) or the pieces
# loaded in one kar. A product can have a free-stock row and rows for
# several kars at the same time (e.g. 5 free, 2 in K101, 3 in K043).
#
# Only app/modules/module_4/stock_service.py writes here, in the same
# database transaction as the ledger lines (StockMaster_movement), locking
# the row first so two people can never both take the last piece. A row
# whose quantity drops to zero is removed, so a row always means "there is
# stock here".

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterBalance(Base):
    """How many pieces of one product lie in one place right now."""

    __tablename__ = "StockMaster_balance"

    # One free-stock row per product, and one row per product per kar. Two
    # partial unique indexes, because a plain unique constraint would allow
    # several rows with an empty kar_id (NULLs never count as equal).
    __table_args__ = (
        Index(
            "uq_stockmaster_balance_free",
            "product_id",
            unique=True,
            postgresql_where=text("kar_id IS NULL"),
            sqlite_where=text("kar_id IS NULL"),
        ),
        Index(
            "uq_stockmaster_balance_kar",
            "product_id",
            "kar_id",
            unique=True,
            postgresql_where=text("kar_id IS NOT NULL"),
            sqlite_where=text("kar_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # No cascades: a product or kar that still holds stock can't be deleted
    # (MasterData and KarTracker refuse it with a clear message instead).
    product_id: Mapped[int] = mapped_column(ForeignKey("MasterData_product.id"), index=True, nullable=False)
    kar_id: Mapped[int | None] = mapped_column(ForeignKey("KarTracker_karren.id"), index=True, nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
