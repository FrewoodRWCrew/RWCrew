# This file defines the "MasterData_team_alias" table: other names a Team goes
# by in outside applications, e.g. slightly differently spelled in the wristband
# company's system, so a wristband scan still finds our team. Managed on the team
# fiche and in the Teams XLSX; written only by module_9/team_alias_service.py.

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamAlias(Base):
    """One other name of a team."""

    __tablename__ = "MasterData_team_alias"

    id: Mapped[int] = mapped_column(primary_key=True)

    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # As typed, for the screen.
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    # Lowercase with single spaces: what's compared, and unique so an alias
    # can only ever point at one team.
    alias_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
