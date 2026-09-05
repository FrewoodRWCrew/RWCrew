# This file defines the "MasterData_team_location" database table: a
# location a team can be assigned to, managed on MasterData's Team
# Location screen (nested under "Teams").

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamLocation(Base):
    """One row per team location that's been defined."""

    __tablename__ = "MasterData_team_location"

    id: Mapped[int] = mapped_column(primary_key=True)
    location: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
