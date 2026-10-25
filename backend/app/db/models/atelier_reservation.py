# This file defines the "Atelier_reservation" table: how many people of a
# ploeg (MasterData team) need work clothing at a festival. The team works
# every day of the festival with that many people and returns the clothing
# every evening, so each festival day needs persons x the team's package
# again (see module_5/preparation_service.py). Entered by the atelier team on
# the Reservaties screen; written only by module_5/reservation_service.py.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierReservation(Base):
    """One row per team per festival: the number of persons."""

    __tablename__ = "Atelier_reservation"

    # A team has one reservation per festival.
    __table_args__ = (UniqueConstraint("festival_id", "team_id", name="uq_atelier_reservation"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # The festival's season, stored for quick per-season lists.
    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_season.id", ondelete="CASCADE"), index=True, nullable=False
    )
    festival_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_festival.id", ondelete="CASCADE"), index=True, nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # How many people of the team work each festival day (0 = none).
    persons: Mapped[int] = mapped_column(Integer, nullable=False)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Who last changed it — always the session user, with a name snapshot so
    # it stays readable if the account is removed.
    updated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
