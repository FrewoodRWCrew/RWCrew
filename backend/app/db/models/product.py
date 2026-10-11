# This file defines the "MasterData_product" database table: the second
# piece of master data managed inside the MasterData module (module-9),
# alongside Season. Its columns match the fields on the "Producten"
# edit screen provided as a reference (naam/Type/Magazijn/Magazijn
# locatie/Categorie/Consumeerbaar/Blokkeer/Is logistiek product/Limiet/
# Beschrijving) plus one optional picture per product.
#
# Type/Magazijn/Categorie/Limiet used to be plain text, but now that those
# four lists are managed as their own lookup screens (ProductType,
# Warehouse, ProductCategory, ProductLimit), they're foreign keys into
# those tables instead.

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, deferred, mapped_column

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

    # StockMaster (module-4) settings, maintained on this product screen:
    # where returned goods go on "Kar terug" — back into the kar ("kar") or
    # straight to free stock ("free") — and, for consumable products, the
    # minimum stock below which StockMaster warns that it's time to reorder.
    stock_return_to: Mapped[str] = mapped_column(String(10), default="kar", server_default="kar", nullable=False)
    min_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # The product's optional picture, stored as bytes in Postgres like
    # KarTracker's ground plans (there is no file storage in this app).
    # The bytes are deferred, so loading products for a list never pulls
    # them in — only the image endpoint reads them.
    image_data: Mapped[bytes | None] = deferred(mapped_column(LargeBinary, nullable=True))
    image_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # When the picture last changed, used as a cache-busting "?v=" on its URL.
    image_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def has_image(self) -> bool:
        """Whether a picture has been uploaded (checked without loading its bytes)."""
        return self.image_content_type is not None
