# This file defines the "Landing_refresh_tokens" table, which keeps
# track of every refresh token we have ever issued (see
# app/core/security.py for what a refresh token is used for).
#
# We store a HASH of each token rather than the token itself, the same way
# we store password hashes: if our database were ever leaked, the stored
# values still couldn't be used to log in as anyone. We also record
# whether a token has been "used up" (revoked), so that if a refresh token
# is somehow used twice, we can detect that something suspicious is
# happening and refuse it.

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshToken(Base):
    """One row per refresh token we have ever issued to a user."""

    # Prefixed with "Landing_" since this table belongs to the landing
    # page's own part of the app (auth), not any one module.
    __tablename__ = "Landing_refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which user this refresh token was issued to.
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Landing_users.id", ondelete="CASCADE"), nullable=False)

    # A hash of the actual token text (never the token itself), so a
    # database leak alone can't be used to impersonate a user.
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # The exact moment this token stops being valid.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Set to True once this token has been used to get a new access token,
    # or when the user logs out. A revoked token can never be used again,
    # even if it hasn't technically expired yet.
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # When this token was first issued, for auditing purposes.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
