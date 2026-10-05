# This file defines the "StockMaster_kar_requirement" table: what a team
# needs in which kar, per season ("Benodigdheden"). One row = "in season S,
# kar K needs N pieces of product P". The team follows from the kar's own
# team in KarTracker.
#
# The needs drive "Kar laden" (pre-filled with what is still missing), the
# kars' loading progress, and "Te bestellen" (needs versus stock). Only
# app/modules/module_4/requirement_service.py reads and writes this table,
# so Altsien Select's future Products wizard step can reuse it.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterKarRequirement(Base):
    """How many pieces of one product one kar needs in one season."""

    __tablename__ = "StockMaster_kar_requirement"

    # A product is listed at most once per kar per season.
    __table_args__ = (
        UniqueConstraint("season_id", "kar_id", "product_id", name="uq_stockmaster_kar_requirement"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    season_id: Mapped[int] = mapped_column(
        ForeignKey("MasterData_season.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kar_id: Mapped[int] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("MasterData_product.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Whole number of pieces, at least 1.
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Who last changed this line (the logged-in user) and when.
    updated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
