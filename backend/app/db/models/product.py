# This file defines the "MasterData_product" database table: the second
# piece of master data managed inside the MasterData module (module-9),
# alongside Season. Its columns match the fields on the "Producten"
# edit screen provided as a reference (naam/Type/Magazijn/Magazijn
# locatie/Categorie/Consumeerbaar/Blokkeer/Is logistiek product/Limiet/
# Beschrijving) — everything except image upload, which is a later step.
#
# Type/Magazijn/Limiet are plain text for now rather than a fixed list or
# a separate lookup table — there's no defined set of allowed values yet,
# so this keeps the door open to upgrade them later once that's decided.

from sqlalchemy import Boolean, String, Text
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

    # Plain text for now (see module docstring above) — no fixed list of
    # allowed values is enforced yet.
    type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warehouse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warehouse_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # The three checkboxes on the reference screen.
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_logistics_product: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # "Limiet" on the reference screen, e.g. "Automatisch" — plain text
    # for the same reason as type/warehouse above.
    limit_mode: Mapped[str | None] = mapped_column(String(255), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
