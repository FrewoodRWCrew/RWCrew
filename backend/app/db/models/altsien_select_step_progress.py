# This file defines the "AltsienSelect_step_progress" table: which steps
# of the Ploeg Wizard have been completed for one team in one season. Only
# the fact that a step is done is stored here — the actual choices live in
# their own tables (festivals in MasterData_team_festival, delivery
# locations in KarTracker_kar_afleverlocaties, ...).
#
# Steps are identified by a plain string key (see
# app/modules/module_8/steps.py) rather than a foreign key, so adding a new
# wizard step later needs no database migration.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AltsienSelectStepProgress(Base):
    """One row means: this wizard step is done for this team in this season."""

    __tablename__ = "AltsienSelect_step_progress"

    # A step can only be completed once per team per season.
    __table_args__ = (
        UniqueConstraint("season_id", "team_id", "step_key", name="uq_altsienselect_step_progress"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_season.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False)

    # The step's stable key, e.g. "festivals" (see module_8/steps.py).
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)

    # When and by whom the step was marked as done. The user link is
    # optional so deleting a user doesn't wipe the team's progress.
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
