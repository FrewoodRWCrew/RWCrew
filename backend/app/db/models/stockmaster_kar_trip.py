# This file defines the "StockMaster_kar_trip" table: one row per time a kar
# left the warehouse ("Kar vertrekt") until it came back ("Kar terug").
#
# Kar stock only exists while the kar stands in the warehouse: on departure
# its whole contents are booked out, on return what came back is booked in
# again. A kar with an open trip (no return yet) is "onderweg" and can't be
# loaded, unloaded or counted.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterKarTrip(Base):
    """One departure of a kar, and its return once it's back."""

    __tablename__ = "StockMaster_kar_trip"

    id: Mapped[int] = mapped_column(primary_key=True)

    kar_id: Mapped[int] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="CASCADE"), index=True, nullable=False
    )
    season_id: Mapped[int] = mapped_column(ForeignKey("MasterData_season.id"), index=True, nullable=False)
    # Where the kar went (defaulted from the kar's team in KarTracker).
    team_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_team.id", ondelete="SET NULL"), nullable=True)
    festival_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_festival.id", ondelete="SET NULL"), nullable=True
    )

    # The "Kar vertrekt" booking that opened the trip, and the "Kar terug"
    # booking that closed it (empty while the kar is still out).
    dispatch_document_id: Mapped[int] = mapped_column(
        ForeignKey("StockMaster_document.id", ondelete="CASCADE"), nullable=False
    )
    return_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("StockMaster_document.id", ondelete="SET NULL"), nullable=True
    )

    dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
