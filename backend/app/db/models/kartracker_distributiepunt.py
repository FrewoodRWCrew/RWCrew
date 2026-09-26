# This file defines the "KarTracker_distributiepunten" table: the
# distribution-point master data, maintained on the Distributiepunten
# screen and referenced from Afleverlocatie (see
# kartracker_afleverlocatie.py). Altsien Kernlid is an optional reference
# to a user flagged Altsien Kernlid — same
# cross-module FK pattern as KarTrackerKar.team_id/transport_type_id.

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerDistributiepunt(Base):
    """One row per distribution point."""

    __tablename__ = "KarTracker_distributiepunten"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The distribution point's name — required and unique.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Last known location, split into separate numeric columns — same
    # pattern as KarTrackerKar.last_latitude/last_longitude.
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    # Free-text on-site position (e.g. a slot/row code) — optional, no
    # fixed format was specified.
    terrein_positie: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Selected from the users flagged "Altsien Kernlid" on Manage Access —
    # optional, a distribution point need not have one assigned.
    altsien_kernlid_id: Mapped[int | None] = mapped_column(
        ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
