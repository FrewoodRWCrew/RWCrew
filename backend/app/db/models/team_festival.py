# This file defines the "MasterData_team_festival" join table: at which
# festivals of a season a team is active. It is filled in by the Altsien
# Kernlid in step 1 of Altsien Select's Ploeg Wizard (module 8), but lives
# with the master data because other modules (products, walkies, Plan a
# kar) can reuse "team X is active at festival Y" as well.

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamFestival(Base):
    """One row means: in this season, this team is active at this festival."""

    __tablename__ = "MasterData_team_festival"

    # The same team can only be linked once to the same festival per season.
    __table_args__ = (
        UniqueConstraint("season_id", "team_id", "festival_id", name="uq_masterdata_team_festival"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Deleting the season, team or festival removes the link with it.
    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_season.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False)
    festival_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_festival.id", ondelete="CASCADE"), nullable=False
    )
