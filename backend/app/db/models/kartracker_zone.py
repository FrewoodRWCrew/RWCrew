# This file defines the "KarTracker_zones" table: a small, centrally
# managed lookup of delivery zones, maintained on the Zone screen and
# referenced from Afleverlocatie (see kartracker_afleverlocatie.py).

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerZone(Base):
    """One row per delivery zone."""

    __tablename__ = "KarTracker_zones"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The zone's name — required and unique, so the same zone can't
    # accidentally be created twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
