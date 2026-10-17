# This file defines the "StockMaster_kar_manual_request" table: products a kar
# asks for on top of its needs, added with "Manueel product toevoegen" on Kar
# laden. One row = "in season S, kar K asked for N pieces of product P by
# hand"; it shows as a "Manueel" row in Kar laden's Karinhoud table and stays
# until it is removed there.
#
# What was delivered is not stored: it follows from the kar's contents (the
# pieces above the kar need count for the manual request), so undo, unload
# and returns keep it right on their own. Only
# app/modules/module_4/manual_request_service.py writes this table.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterKarManualRequest(Base):
    """How many pieces of one product were asked for by hand for one kar in one season."""

    __tablename__ = "StockMaster_kar_manual_request"

    # A product is on a kar's manual list at most once per season (adding it again adds up).
    __table_args__ = (
        UniqueConstraint("season_id", "kar_id", "product_id", name="uq_stockmaster_kar_manual_request"),
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

    # Whole number of pieces asked for, at least 1 ("Gevraagd door Vereniging" of the Manueel row).
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Who added it first (the logged-in user) and when; updated_at changes when pieces are added.
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
