# This file defines the "MasterData_product_type" database table: one of
# three lookup lists ("selection criteria") a product can be tagged with on
# the Products screen — Type, Warehouse (Magazijn), and Limit (Limiet).
# Same bare id+unique-name shape as Season (see season.py); this table
# replaces what used to be a free-text "type" column on Product.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductType(Base):
    """One row per product type that's been defined (e.g. "Consumable")."""

    __tablename__ = "MasterData_product_type"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Must be unique so the same type can't accidentally be entered twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
