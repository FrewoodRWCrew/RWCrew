# This file defines the "StockMaster_voice_count_line" table: one counted
# product of a voice count (StockMaster_voice_count). A product appears at
# most once per count: saying it twice adds the quantities up.

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMasterVoiceCountLine(Base):
    """How many pieces of one product were counted (by voice) on one kar."""

    __tablename__ = "StockMaster_voice_count_line"

    __table_args__ = (
        UniqueConstraint("voice_count_id", "product_id", name="uq_stockmaster_voice_count_line_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # The count this line belongs to; removing the count removes its lines.
    voice_count_id: Mapped[int] = mapped_column(
        ForeignKey("StockMaster_voice_count.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # The product, plus a copy of its name so the count stays readable if the
    # product is later removed.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("MasterData_product.id", ondelete="SET NULL"), index=True, nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Whole number of pieces counted, at least 1.
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # What was said for this line (e.g. "twintig rollen tape"), for checking
    # the recognition afterwards; empty when the line was added by hand.
    spoken_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
