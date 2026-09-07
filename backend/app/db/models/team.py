# This file defines the "MasterData_team" database table: the real piece
# of master data behind MasterData's "Teams" screen (previously a
# placeholder). name must be unique; location/delivery method are single
# nullable FKs into their own lookup screens (Team Location, Delivery
# Method); tasks (Taken) and core members (Kernleden) are many-to-many via
# MasterData_team_team_task / MasterData_team_kernlid instead of columns
# on this table — see those two models.

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Team(Base):
    """One row per team that's been defined."""

    __tablename__ = "MasterData_team"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Selected from the Team Location / Delivery Method lookup screens — optional.
    location_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_team_location.id"), nullable=True)
    delivery_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_delivery_method.id"), nullable=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
