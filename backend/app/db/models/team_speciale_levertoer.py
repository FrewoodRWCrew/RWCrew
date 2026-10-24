# This file defines the "MasterData_team_speciale_levertoer" join table: which
# special delivery tours (KarTracker "Speciale levertoeren") pass by which
# Team — a many-to-many relationship, the same shape as MasterData_team_team_task.

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamSpecialeLevertoer(Base):
    """One row means: this special delivery tour passes by this team."""

    __tablename__ = "MasterData_team_speciale_levertoer"

    # A team can only be on the same tour once — no duplicate links.
    __table_args__ = (UniqueConstraint("team_id", "levertoer_id", name="uq_masterdata_team_speciale_levertoer"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False)
    levertoer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("KarTracker_speciale_levertoeren.id", ondelete="CASCADE"), nullable=False
    )
