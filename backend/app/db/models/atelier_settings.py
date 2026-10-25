# This file defines the "Atelier_settings" table: Atelier-wide settings, one
# row (id 1), edited on Atelier's Instellingen screen. For now only whether a
# wristband number is required at Ophalen.

from sqlalchemy import Boolean, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierSettings(Base):
    """The single row of Atelier settings."""

    __tablename__ = "Atelier_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # When on, a pick-up at the counter needs a wristband number.
    wristband_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
