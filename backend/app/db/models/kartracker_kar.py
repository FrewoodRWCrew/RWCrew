# This file defines the "KarTracker_karren" table: the fleet registry
# itself, one row per physical cart ("kar"). Its columns are modeled on the
# Karlijst CSV provided as a reference (KarNummer/KarStatus/Vereniging/
# TransportType/geo location/last-seen time), minus the "Pick &
# Aflevervolgorde" column, which belongs to the future delivery-planning
# phase, and minus a CSV-import feature, which was never requested — this
# is a plain, manually-operated CRUD screen (see KarManagement screen).
#
# The original free-text "Vereniging" (organization) column was replaced
# with team_id — a dropdown sourced from module-9's existing "Teams"
# master data ("Ploeg" in the UI) — once it became clear that's what this
# field should actually track.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KarTrackerKar(Base):
    """One row per physical kar managed by the organization."""

    __tablename__ = "KarTracker_karren"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The kar's own business identifier (e.g. "B001", "K047") — required and
    # unique, independent of the internal autoincrement id.
    kar_nummer: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # Selected from the KarStatussen lookup screen.
    status_id: Mapped[int] = mapped_column(ForeignKey("KarTracker_kar_statuses.id"), nullable=False)

    # Selected from module-9's existing "Teams" master data ("Ploeg" in
    # the UI) — which team currently has this kar. Optional: a kar sitting
    # unassigned in the warehouse has no team.
    team_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_team.id"), nullable=True)

    # Selected from module-9's existing "Producten" master data (chosen by
    # the user in place of a brand-new TransportType table) — a
    # cross-module foreign key, same pattern Scanner uses for its type_id.
    transport_type_id: Mapped[int] = mapped_column(ForeignKey("MasterData_product.id"), nullable=False)

    # Last known location, split into separate numeric columns.
    last_latitude: Mapped[float | None] = mapped_column(nullable=True)
    last_longitude: Mapped[float | None] = mapped_column(nullable=True)

    last_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
