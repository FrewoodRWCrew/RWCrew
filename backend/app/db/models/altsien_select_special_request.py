# This file defines the "AltsienSelect_special_requests" table: the
# special requests/comments entered for a team in the Ploeg Wizard, each
# with a status the organisation follows up on.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AltsienSelectSpecialRequest(Base):
    """One row per special request entered for a team in a season."""

    __tablename__ = "AltsienSelect_special_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_season.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("MasterData_team.id", ondelete="CASCADE"), nullable=False)

    # What the Kernlid is asking for.
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # The follow-up status. No cascade: a status that is still in use
    # can't be deleted.
    status_id: Mapped[int] = mapped_column(Integer, ForeignKey("AltsienSelect_request_status.id"), nullable=False)

    # The organisation's answer/remark, shown back to the Kernlid.
    organisation_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Who entered the request; optional so deleting a user keeps it.
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
