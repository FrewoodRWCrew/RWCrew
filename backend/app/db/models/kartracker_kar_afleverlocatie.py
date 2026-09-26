# This file defines the "KarTracker_kar_afleverlocaties" table: the "Plan a
# kar" assignments. One row says "in this season, team X delivers to
# afleverlocatie Y at festival Z". The unique constraint on
# (season, festival, team) is what guarantees saving the same combination
# again updates the existing row instead of adding a second one.

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerKarAfleverlocatie(Base):
    """One row per (season, festival, team) with its chosen delivery location."""

    __tablename__ = "KarTracker_kar_afleverlocaties"
    __table_args__ = (
        UniqueConstraint("season_id", "festival_id", "team_id", name="uq_kar_afleverlocatie_season_festival_team"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # The season, festival and team this assignment belongs to. Deleting any
    # of them removes the assignments that pointed at it.
    season_id: Mapped[int] = mapped_column(
        ForeignKey("MasterData_season.id", ondelete="CASCADE"), nullable=False
    )
    festival_id: Mapped[int] = mapped_column(
        ForeignKey("MasterData_festival.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False
    )

    # The chosen delivery location. No cascade: a location that is still
    # referenced by a plan can't be deleted (deactivate it instead).
    afleverlocatie_id: Mapped[int] = mapped_column(
        ForeignKey("KarTracker_afleverlocaties.id"), nullable=False
    )
