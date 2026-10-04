# This file defines the "KarTracker_kar_actions" table ("KarActions"): the
# log of manual kar movements, filled on KarTracker's "Manuele kar beweging"
# screen. Every time a deliverer moves a kar, one row records which kar,
# its new status, the GPS location, when, and the team the kar belonged to
# at that moment. Logging a movement also updates the kar's own "last
# known" status/location in KarTracker_karren — see module_2/router.py.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerKarAction(Base):
    """One row per logged kar movement."""

    __tablename__ = "KarTracker_kar_actions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The kar that was moved. Deleting the kar removes its movement log.
    kar_id: Mapped[int] = mapped_column(
        ForeignKey("KarTracker_karren.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # The status selected for the kar (from the KarStatussen lookup). No
    # cascade: a status still used in the log can't be deleted.
    status_id: Mapped[int] = mapped_column(ForeignKey("KarTracker_kar_statuses.id"), nullable=False)

    # A snapshot of the kar's team at the time of logging (not the kar's
    # current team). Empty when the kar had no team, or the team was deleted.
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_team.id", ondelete="SET NULL"), nullable=True
    )

    # The GPS location chosen for the movement (device GPS or map click).
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)

    # When the movement was logged, set by the server (UTC).
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )

    # Who logged the movement. Kept (as empty) when the user is deleted.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
