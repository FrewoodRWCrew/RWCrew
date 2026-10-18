# This file defines the "Atelier_roles" table: the custom
# roles that exist inside the Atelier module (e.g. "Admin",
# "Atelierverantwoordelijke", "Medewerker").
#
# Unlike the fixed admin/editor/reader roles most other modules share
# (see app/db/models/module_role.py), Atelier's roles are
# fully custom — created, renamed, and deleted freely through the Roles
# screen, with their actual permissions controlled separately per screen
# (see atelier_role_permission.py).

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierRole(Base):
    """One row per custom role that exists inside the Atelier module."""

    __tablename__ = "Atelier_roles"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The role's name, e.g. "Admin". Must be unique so two roles can't
    # accidentally be created with the exact same name.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
