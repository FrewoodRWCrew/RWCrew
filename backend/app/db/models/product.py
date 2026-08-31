# This file defines the "MasterData_product" database table: the second
# piece of master data managed inside the MasterData module (module-9),
# alongside Season. Its columns match the fields on the "Producten"
# edit screen provided as a reference (naam/Type/Magazijn/Magazijn
# locatie/Categorie/Consumeerbaar/Blokkeer/Is logistiek product/Limiet/
# Beschrijving) — everything except image upload, which is a later step.
#
# Type/Magazijn/Categorie/Limiet used to be plain text, but now that those
# four lists are managed as their own lookup screens (ProductType,
# Warehouse, ProductCategory, ProductLimit), they're foreign keys into
# those tables instead.

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    """One row per product that's been defined."""

    __tablename__ = "MasterData_product"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The product's name (naam). Not required to be unique — the
    # reference screen doesn't indicate that rule the way Season's name
    # is required to be unique.
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Selected from the Type/Magazijn lookup screens — optional, since
    # the reference screen doesn't require them.
    type_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_product_type.id"), nullable=True)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_warehouse.id"), nullable=True)
    warehouse_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_product_category.id"), nullable=True)

    # The three checkboxes on the reference screen.
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_logistics_product: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # "Limiet" on the reference screen — selected from the Limiet lookup screen.
    limit_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_product_limit.id"), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
