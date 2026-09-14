# This file defines the "KarTracker_afleverlocaties" table: a delivery
# location, always belonging to exactly one Zone and one Distributiepunt
# (both required FKs), maintained on the Afleverlocatie screen. Altsien
# Kernlid is an optional cross-module reference, same pattern as
# KarTrackerDistributiepunt's own.

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerAfleverlocatie(Base):
    """One row per delivery location."""

    __tablename__ = "KarTracker_afleverlocaties"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The delivery location's name — required and unique.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Free-text description — optional, same convention as
    # Product.description/Team.description.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # A delivery location always belongs to exactly one zone and one
    # distribution point — both required, unlike the optional Altsien
    # Kernlid reference below.
    zone_id: Mapped[int] = mapped_column(ForeignKey("KarTracker_zones.id"), nullable=False)
    distributiepunt_id: Mapped[int] = mapped_column(
        ForeignKey("KarTracker_distributiepunten.id"), nullable=False
    )

    # Location, split into separate numeric columns — same pattern as
    # KarTrackerKar.last_latitude/last_longitude.
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    # Free-text on-site position (e.g. a slot/row code) — optional, no
    # fixed format was specified.
    terrein_positie: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Selected from module-9's existing "Altsien Kernleden" master data —
    # optional, a delivery location need not have one assigned.
    altsien_kernlid_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_altsien_kernlid.id"), nullable=True
    )
