# This file defines the "MasterData_delivery_method" database table: a
# way a team's delivery can be carried out, managed on MasterData's
# Delivery Method screen (nested under "Teams").

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DeliveryMethod(Base):
    """One row per delivery method that's been defined."""

    __tablename__ = "MasterData_delivery_method"

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_method: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
