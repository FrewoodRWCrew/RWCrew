# This file defines the "MasterData_team_task" database table: a task
# that can be assigned to a team, managed on MasterData's Team Tasks
# screen (nested under "Teams").

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamTask(Base):
    """One row per team task that's been defined."""

    __tablename__ = "MasterData_team_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_tasks: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
