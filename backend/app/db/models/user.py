# This file defines the "Landing_users" database table: every person who
# can log in to RW Crew, including the super admin.

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """One row per person who can log in to RW Crew."""

    # The actual name of the table in the PostgreSQL database. Prefixed
    # with "Landing_" since this table belongs to the landing page's own
    # part of the app (auth/access), as opposed to a specific module.
    __tablename__ = "Landing_users"

    # A unique number identifying this user, assigned automatically.
    id: Mapped[int] = mapped_column(primary_key=True)

    # The user's email address, used to log in. Must be unique — two users
    # can't share the same email address.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # The user's password, already run through our one-way hashing
    # function (see app/core/security.py). We never store the real
    # password anywhere.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # The user's full name, shown in the interface (e.g. in the sidebar).
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Whether this user is the site-wide "super admin". A super admin can
    # decide which of the 9 modules each user is allowed to open, from the
    # landing page's admin menu. This is the ONLY thing the super-admin
    # flag controls — it does not grant any role inside a specific module.
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Whether this account can currently log in at all. Admins can disable
    # an account (e.g. someone who left) without deleting their history.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Which language this user prefers the interface in: "nl" (Dutch,
    # the site-wide default) or "en" (English).
    language_preference: Mapped[str] = mapped_column(String(5), default="nl", nullable=False)

    # The exact moment this account was created, recorded automatically.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
