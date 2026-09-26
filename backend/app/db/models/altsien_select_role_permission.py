# This file defines the "AltsienSelect_role_permissions" table:
# what one Altsien Select role is allowed to do on one
# Altsien Select screen.
#
# Each row covers exactly one (role, screen) pair, with four separate
# yes/no switches — a role might be allowed to VIEW the Ploeg Wizard
# screen but not EDIT anything on it, for example. If a role has
# no row at all for a given screen, that means "no access whatsoever" for
# that screen — see app/modules/module_8/deps.py for how this is checked.

from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AltsienSelectRolePermission(Base):
    """One row means: this role has these specific permissions on this screen."""

    __tablename__ = "AltsienSelect_role_permissions"

    # A role can only have ONE permissions row per screen.
    __table_args__ = (
        UniqueConstraint("role_id", "screen_id", name="uq_altsienselect_role_permissions_role_screen"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("AltsienSelect_roles.id", ondelete="CASCADE"), nullable=False
    )
    screen_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("AltsienSelect_screens.id", ondelete="CASCADE"), nullable=False
    )

    # Can a user with this role even open this screen?
    can_view: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Can they create new records on this screen?
    can_create: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Can they edit existing records on this screen?
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Can they delete records on this screen?
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
