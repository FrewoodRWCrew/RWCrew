# This file defines the "KarTracker_speciale_levertoeren" table: the special
# delivery tours (e.g. "Kleine wastoer", "Ijsblokken") that regularly pass by
# a number of teams to check whether there is laundry, ice cubes, ... to
# deliver. Maintained on KarTracker's "Speciale levertoeren" screen; teams are
# linked to them on MasterData's team fiche (see team_speciale_levertoer.py).

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerSpecialeLevertoer(Base):
    """One row per special delivery tour."""

    __tablename__ = "KarTracker_speciale_levertoeren"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The tour's name — required and unique, so the same tour can't be created twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Free text: what the tour checks / when it runs.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # An inactive tour can no longer be picked for a team, but keeps its links.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
