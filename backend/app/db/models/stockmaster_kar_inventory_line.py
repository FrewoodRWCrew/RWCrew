# This file defines the "StockMaster_kar_inventory_line" table: one product of a
# kar inventory (StockMaster_kar_inventory) — what should be in the kar
# (`expected`, worked out by the server when saving) and what the team counted.
# Only app/modules/module_4/kar_inventory_service.py writes this table.

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterKarInventoryLine(Base):
    """One counted product of a kar inventory."""

    __tablename__ = "StockMaster_kar_inventory_line"

    id: Mapped[int] = mapped_column(primary_key=True)

    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("StockMaster_kar_inventory.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The product, and its name at the time (the line stays readable when the product goes).
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_product.id", ondelete="SET NULL"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # What left with the kar (or is in it in the warehouse) when the count was saved,
    # and what the team counted. Both whole pieces, never negative.
    expected: Mapped[int] = mapped_column(Integer, nullable=False)
    counted: Mapped[int] = mapped_column(Integer, nullable=False)

    # True for a product the team added itself (not on the kar's list; expected 0).
    is_extra: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
