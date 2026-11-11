# This file defines the "StockMaster_kar_inventory" table: a count a team made
# of its own kar at the end of a festival, before the kar is picked up. The
# team reaches it without an RWCrew login through the karblad's QR code
# (public kar page → "Kar inventaris") and unlocks it with the kar's lock code.
#
# Purely informative: an inventory never books or changes stock. It shows
# StockMaster what is (still) in the kar so the most products come back. Every
# save is a new row (a log): nothing is edited or deleted afterwards. Only
# app/modules/module_4/kar_inventory_service.py writes this table.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterKarInventory(Base):
    """One inventory of one kar, with its lines in StockMaster_kar_inventory_line."""

    __tablename__ = "StockMaster_kar_inventory"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The counted kar; its inventories go when the kar is deleted.
    kar_id: Mapped[int] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The kar number at the time of counting (survives renumbering).
    kar_nummer: Mapped[str] = mapped_column(String(50), nullable=False)
    # The season it was counted in (the last open season), the kar's team then,
    # and the trip it was counted against while the kar was out (NULL = in the warehouse).
    season_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_season.id", ondelete="SET NULL"), index=True, nullable=True
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_team.id", ondelete="SET NULL"), nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_kar_trip.id", ondelete="SET NULL"), nullable=True
    )

    # Who counted (typed by the team member, not an RWCrew user) and an optional remark.
    counted_by_name: Mapped[str] = mapped_column(String(100), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When it was saved, and from which address (to trace abuse of the public page).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
