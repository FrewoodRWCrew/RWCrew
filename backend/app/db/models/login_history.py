# This file defines the "Landing_login_history" table, which records
# every login attempt made against the tool — successful or not — so a
# super admin can see who is using it and when on the "Login History"
# admin screen.

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoginHistory(Base):
    """One row per login attempt, successful or not."""

    # Prefixed with "Landing_" since this table belongs to the landing
    # page's own part of the app (auth), not any one module.
    __tablename__ = "Landing_login_history"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which user this attempt matched, if any. Uses SET NULL (not the
    # CASCADE used by Landing_refresh_tokens): this is an audit trail and
    # must survive the referenced user being deleted later. It's also
    # nullable to begin with, to cover attempts against an email that
    # never matched any account.
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )

    # The email address as typed, regardless of whether it matched a real
    # account — so attempts against unknown emails are still visible, and
    # this stays meaningful even after the matched user is deleted.
    email_attempted: Mapped[str] = mapped_column(String(255), nullable=False)

    # Whether this attempt actually resulted in a successful login.
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # The client IP address the attempt came from, if available.
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # When this attempt happened, for sorting/filtering on the admin screen.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
