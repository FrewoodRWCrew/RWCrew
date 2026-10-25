# This file defines the "Atelier_article_size" table: which sizes an article
# comes in — the piece that is actually stocked, reserved and handed out
# (e.g. "T-shirt crew zwart · M · Men"). Managed from the article's form on
# the Artikelen screen (a checklist of sizes).

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierArticleSize(Base):
    """One row means: this article exists in this size."""

    __tablename__ = "Atelier_article_size"

    # An article has each size at most once.
    __table_args__ = (UniqueConstraint("article_id", "size_id", name="uq_atelier_article_size"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Atelier_article.id", ondelete="CASCADE"), index=True, nullable=False
    )
    size_id: Mapped[int] = mapped_column(Integer, ForeignKey("Atelier_size.id"), nullable=False)

    # The stock below which the atelier wants a warning (optional; used once
    # the stock exists).
    min_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # The article's standard size split: which share (%) of the pieces to
    # prepare in this size (e.g. M 30). Used to estimate sizes on the
    # Voorbereiden screen; empty on every size = an equal split.
    size_share_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # An inactive size of an article is no longer handed out or ordered.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
