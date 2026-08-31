# This file defines the "MasterData_warehouse" database table: one of
# three lookup lists ("selection criteria") a product can be tagged with on
# the Products screen — Type, Warehouse (Magazijn), and Limit (Limiet).
# Same bare id+unique-name shape as Season (see season.py); this table
# replaces what used to be a free-text "warehouse" column on Product.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Warehouse(Base):
    """One row per warehouse (Magazijn) that's been defined."""

    __tablename__ = "MasterData_warehouse"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Must be unique so the same warehouse can't accidentally be entered twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
