# This file defines the "MasterData_festival" database table: a festival
# organized within a specific season, managed on MasterData's Festivals
# screen (a sibling to the Season screen).

from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Festival(Base):
    """One row per festival that's been defined, tied to the season it runs in."""

    __tablename__ = "MasterData_festival"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Every festival belongs to exactly one season.
    season_id: Mapped[int] = mapped_column(ForeignKey("MasterData_season.id"), nullable=False)
