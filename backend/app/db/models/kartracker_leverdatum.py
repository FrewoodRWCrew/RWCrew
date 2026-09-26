# This file defines the "Festivals_leverdatum" table: the delivery date and
# the pick-up date of a festival, managed on KarTracker's "Delivery Dates"
# screen. There is at most one row per festival — the unique constraint on
# festival_id is what guarantees saving a festival again updates its
# existing row instead of adding a second line.

from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerLeverdatum(Base):
    """One row per festival with its delivery date and pick-up date."""

    __tablename__ = "Festivals_leverdatum"
    __table_args__ = (UniqueConstraint("festival_id", name="uq_leverdatum_festival"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # The festival these dates belong to. Deleting the festival removes its dates.
    festival_id: Mapped[int] = mapped_column(
        ForeignKey("MasterData_festival.id", ondelete="CASCADE"), nullable=False
    )

    # Either date may be left empty; a festival with neither has no row at all.
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pickup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
