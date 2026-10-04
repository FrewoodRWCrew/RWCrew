# This file defines the "MasterData_team_responsible" table: the people
# responsible for a team ("Ploegverantwoordelijken") in a given season.
# They are plain contact records, NOT RWCrew users — so name/email/phone
# are stored here directly instead of pointing at Landing_users. Managed
# on MasterData's "Ploegverantwoordelijken" screen (nested under "Teams");
# a later Altsien Select wizard step is meant to edit this same table.

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamResponsible(Base):
    """One row per responsible person of one team in one season."""

    __tablename__ = "MasterData_team_responsible"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Deleting the season or team removes its responsible people with it.
    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_season.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Contact details — all required except the free-text comments.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
