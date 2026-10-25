# This file defines the "Atelier_stock_movement" table: the lines of an
# Atelier stock booking — a quantity of one article size moving from one
# stock status to another (NULL = outside the store, e.g. a receipt comes
# from outside, a write-off goes outside). Written only by
# module_5/stock_service.py.

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierStockMovement(Base):
    """One booked line: N pieces of an article size, from → to."""

    __tablename__ = "Atelier_stock_movement"

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Atelier_stock_document.id", ondelete="CASCADE"), index=True, nullable=False
    )
    article_size_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Atelier_article_size.id"), index=True, nullable=False
    )

    # available / to_wash / handed_out, or NULL for outside the store.
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
