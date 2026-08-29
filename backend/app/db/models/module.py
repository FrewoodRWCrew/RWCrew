# This file defines the "Landing_modules" database table: the 9 tiles
# shown on the landing page. For now they are simply named "Module 1"
# through "Module 9" — their real names and functionality will be added
# later.

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Module(Base):
    """One row per module/tile on the landing page (module-1 .. module-9)."""

    # Prefixed with "Landing_" since this table belongs to the landing
    # page's own part of the app (it's the registry of all 9 modules).
    __tablename__ = "Landing_modules"

    # A unique number identifying this module, assigned automatically.
    id: Mapped[int] = mapped_column(primary_key=True)

    # A short, unique, code-friendly identifier, e.g. "module-1". This is
    # what the rest of the code uses to refer to a specific module, since
    # it never changes even if the display name later does.
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # The name shown to users on the tile, e.g. "Module 1". Will be
    # replaced with the module's real name once it's decided.
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Controls the left-to-right, top-to-bottom order the tiles are shown
    # in on the landing page.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # A site-wide on/off switch for this module, separate from any single
    # user's access. If a module is switched off here, nobody can open it
    # — even a user who was individually granted access, and even the
    # super admin's own tile view would show it as unavailable. Useful for
    # temporarily hiding a module while it's still being built.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
