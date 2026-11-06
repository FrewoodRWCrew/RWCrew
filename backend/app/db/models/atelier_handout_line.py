# This file defines the "Atelier_handout_line" table: one piece of a pick-up
# (an article in the size chosen at the desk). It stays "out" until it is
# returned ("Terugbrengen"), which fills returned_at and the return's stock
# booking (handed out → to wash). Written only by module_5/desk_service.py.
# A piece read by its RFID tag (the Raspberry Pi app) also keeps that tag.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
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

    # The physical piece (its RFID tag) that went out, when the pick-up was
    # booked by reading tags (the Raspberry Pi app); NULL = picked by size only.
    rfid_tag_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Tagscan_rfid_tag.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # That tag's EPC at the moment of the hand-out: the fixed reference for the
    # trace (also when the tag is later deleted or linked to another piece).
    handout_epc: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)

    # The tag read when the piece came back (on the Pi), its EPC, and where the
    # return was booked: "web" or "pi" (NULL while still out).
    return_rfid_tag_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Tagscan_rfid_tag.id", ondelete="SET NULL"), nullable=True
    )
    return_epc: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    return_source: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # What was wrong with it when it came back (NULL = no remark).
    return_status_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Atelier_return_status.id"), nullable=True
    )
