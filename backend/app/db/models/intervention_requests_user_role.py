# This file defines the "InterventionRequests_user_roles" table: which
# single custom Intervention Requests role (if any) a given user currently
# holds.
#
# This is separate from — and only meaningful alongside — the normal
# site-wide "user_module_access" grant: a user must already have plain
# access to Intervention Requests (granted by the super admin, or by an
# Intervention Requests admin via the module-scoped "create user" action)
# before their role here means anything.

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InterventionRequestsUserRole(Base):
    """One row means: this user holds this role inside the Intervention Requests module."""

    __tablename__ = "InterventionRequests_user_roles"

    id: Mapped[int] = mapped_column(primary_key=True)

    # A user can only hold ONE Intervention Requests role at a time, so
    # this column is unique — assigning a new role always replaces the old
    # one rather than adding a second row.
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("InterventionRequests_roles.id", ondelete="CASCADE"), nullable=False
    )
