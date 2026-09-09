# This file defines the "KarTracker_kar_statuses" table: the small,
# centrally-managed lookup of statuses a kar can have (e.g. "Terug in
# Magazijn"), maintained on the KarStatussen screen and selected from a
# dropdown on the KarManagement screen — see kartracker_kar.py.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerKarStatus(Base):
    """One row per status a kar can be in."""

    __tablename__ = "KarTracker_kar_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The status' name, e.g. "Terug in Magazijn". Must be unique so the
    # same status can't accidentally be created twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
