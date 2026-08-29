# This file defines the "Landing_module_roles" table: which specific
# role (admin / editor / reader) a user holds WITHIN one particular
# module.
#
# This is separate from "Landing_user_module_access" (see that file).
# Whether a user can open a module at all is the super admin's decision;
# which role they then have inside that module is decided by that
# module's own admin(s) — the two are independent.

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModuleRoleName(str, enum.Enum):
    """The three roles a user can hold inside a single module."""

    # Can manage that module's own settings/roles/data fully.
    ADMIN = "admin"
    # Can create and change data inside that module, but not manage roles.
    EDITOR = "editor"
    # Can only view data inside that module.
    READER = "reader"


class ModuleRole(Base):
    """One row means: this user holds this role inside this module."""

    # Prefixed with "Landing_" since this table belongs to the landing
    # page's own part of the app (access rights), not any one module.
    __tablename__ = "Landing_module_roles"

    # A user can only have ONE role per module (they can't be both
    # "editor" and "reader" in the same module at the same time).
    __table_args__ = (UniqueConstraint("user_id", "module_id", name="uq_module_roles_user_module"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which user this role belongs to.
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Landing_users.id", ondelete="CASCADE"), nullable=False)

    # Which module this role applies to.
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Landing_modules.id", ondelete="CASCADE"), nullable=False
    )

    # The role itself: admin, editor, or reader (see ModuleRoleName above).
    role: Mapped[ModuleRoleName] = mapped_column(Enum(ModuleRoleName, name="module_role_name"), nullable=False)

    # When this role was assigned, for auditing purposes.
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
