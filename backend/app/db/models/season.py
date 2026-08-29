# This file defines the "landing_md_season" database table: the first
# piece of "master data" managed from the landing page's admin sidebar
# (see the project plan for what master data is and why it's separate
# from the per-module data). A season is just a named entry (e.g. a
# year) that other parts of the app can later refer to.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Season(Base):
    """One row per season the super admin has defined (e.g. "2026")."""

    # Named exactly as requested: lowercase, "landing" (this belongs to
    # the landing page's admin area) + "md" (master data) + "season".
    __tablename__ = "landing_md_season"

    # A unique number identifying this season, assigned automatically —
    # the "unique ID" column.
    id: Mapped[int] = mapped_column(primary_key=True)

    # The season's name, e.g. "2026". Must be unique so the same season
    # can't accidentally be entered twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
