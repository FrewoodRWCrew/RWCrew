# This file defines the "KarTracker_screens" table: the registry of every
# screen that exists inside the KarTracker module (e.g. "Roles", "Users").
#
# This table is never edited by hand — it's kept in sync automatically
# every time the backend starts (see app/modules/module_2/screens.py), from
# a plain Python list in that file. Adding a new screen there is the only
# step needed for it to start showing up as a new row in every role's
# permission matrix on the Roles screen.

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerScreen(Base):
    """One row per screen that exists inside the KarTracker module."""

    __tablename__ = "KarTracker_screens"

    id: Mapped[int] = mapped_column(primary_key=True)

    # A stable, code-friendly identifier, e.g. "kartracker.roles". This is
    # what the rest of the code uses to refer to a screen, since it never
    # changes even if its display label later does.
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # The name shown in the UI, e.g. "Roles".
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    # Controls the order screens are listed in (e.g. in the permission matrix).
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
