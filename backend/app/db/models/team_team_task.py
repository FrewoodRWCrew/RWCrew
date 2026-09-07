# This file defines the "MasterData_team_team_task" join table: which
# Team Tasks (Taken) are assigned to which Team — a many-to-many
# relationship, the same shape as MasterData_role_permissions.

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamTeamTask(Base):
    """One row means: this team has this team task assigned to it."""

    __tablename__ = "MasterData_team_team_task"

    # A team can only have one row per task — no duplicate links.
    __table_args__ = (UniqueConstraint("team_id", "team_task_id", name="uq_masterdata_team_team_task"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False)
    team_task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_team_task.id", ondelete="CASCADE"), nullable=False
    )
