# This file defines the "MasterData_product_category" database table: a
# fourth lookup list ("selection criteria") a product can be tagged with on
# the Products screen — alongside Type, Warehouse (Magazijn), and Limit
# (Limiet). Same bare id+unique-name shape as those (see product_type.py);
# this table replaces what used to be a free-text "category" column on
# Product.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductCategory(Base):
    """One row per product category that's been defined."""

    __tablename__ = "MasterData_product_category"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Must be unique so the same category can't accidentally be entered twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
