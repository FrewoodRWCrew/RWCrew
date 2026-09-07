# This file defines the "MasterData_team_kernlid" join table: which
# Altsien Kernleden contacts (Kernleden) belong to which Team — a
# many-to-many relationship, the same shape as MasterData_team_team_task.

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamKernlid(Base):
    """One row means: this Altsien Kernleden contact belongs to this team."""

    __tablename__ = "MasterData_team_kernlid"

    # A team can only have one row per contact — no duplicate links.
    __table_args__ = (UniqueConstraint("team_id", "altsien_kernlid_id", name="uq_masterdata_team_kernlid"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False)
    altsien_kernlid_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_altsien_kernlid.id", ondelete="CASCADE"), nullable=False
    )
