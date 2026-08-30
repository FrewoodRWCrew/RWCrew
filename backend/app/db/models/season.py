# This file defines the "MasterData_season" database table: the first
# piece of "master data" managed inside the MasterData module (module-9).
# A season is just a named entry (e.g. a year) that other parts of the
# app can later refer to.
#
# This table used to be called "landing_md_season" back when Season was a
# super-admin-only screen under the landing page's own admin area; it was
# renamed (data preserved, see the migration that moved Season into
# MasterData) once Season became a MasterData screen like any other, with
# its own per-role view/create/edit/delete permissions instead of a flat
# "super admin only" check.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Season(Base):
    """One row per season that's been defined (e.g. "2026")."""

    __tablename__ = "MasterData_season"

    # A unique number identifying this season, assigned automatically —
    # the "unique ID" column.
    id: Mapped[int] = mapped_column(primary_key=True)

    # The season's name, e.g. "2026". Must be unique so the same season
    # can't accidentally be entered twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
