# This file defines the "Atelier_handout_line" table: one piece of a pick-up
# (an article in the size chosen at the desk). It stays "out" until it is
# returned ("Terugbrengen"), which fills returned_at and the return's stock
# booking (handed out → to wash). Written only by module_5/desk_service.py.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierHandoutLine(Base):
    """One piece handed out (1 per package article)."""

    __tablename__ = "Atelier_handout_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    handout_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Atelier_handout.id", ondelete="CASCADE"), index=True, nullable=False
    )
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("Atelier_article.id"), nullable=False)
    article_size_id: Mapped[int] = mapped_column(Integer, ForeignKey("Atelier_article_size.id"), nullable=False)

    # When it came back, and the stock booking of that return (NULL = still out).
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    return_document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Atelier_stock_document.id"), nullable=True
    )
