# This file defines the "Landing_user_module_access" table: a simple
# yes/no record of which modules a given user is allowed to open at all.
#
# This is deliberately separate from "Landing_module_roles" (see
# module_role.py).
# Access here is a plain switch controlled ONLY by the super admin, from
# the landing page's admin menu. Once a user has access to a module, that
# module's own admin(s) decide the user's specific role inside it.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserModuleAccess(Base):
    """One row means: this user is allowed to open this module."""

    # Prefixed with "Landing_" since this table belongs to the landing
    # page's own part of the app (access rights), not any one module.
    __tablename__ = "Landing_user_module_access"

    # Make sure the same user can't be granted access to the same module
    # twice (that would just be a duplicate, meaningless row).
    __table_args__ = (UniqueConstraint("user_id", "module_id", name="uq_user_module_access_user_module"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which user this access grant belongs to.
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Landing_users.id", ondelete="CASCADE"), nullable=False)

    # Which module this user was granted access to.
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Landing_modules.id", ondelete="CASCADE"), nullable=False
    )

    # When the super admin granted this access, for auditing purposes.
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
