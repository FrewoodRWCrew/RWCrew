# This file defines the "Atelier_stock_balance" table: the current number of
# pieces per article size per stock status (available, to_wash,
# handed_out). Kept in step with the movements by module_5/stock_service.py
# in the same transaction (rows locked first), so it never goes negative. A
# row at 0 is deleted: a row always means "there are pieces here".

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierStockBalance(Base):
    """N pieces of one article size in one status."""

    __tablename__ = "Atelier_stock_balance"

    __table_args__ = (UniqueConstraint("article_size_id", "status", name="uq_atelier_stock_balance"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    article_size_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Atelier_article_size.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
