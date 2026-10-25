# This file defines the "Atelier_stock_document" table: one row per stock
# booking in Atelier (a receipt, clothes washed, a write-off, a stock count,
# or the undoing of one of those). Its lines are the Atelier_stock_movement
# rows. Nothing is ever edited or deleted: "Ongedaan maken" adds a
# "reversal" document. Written only by module_5/stock_service.py.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierStockDocument(Base):
    """One Atelier stock booking (its header)."""

    __tablename__ = "Atelier_stock_document"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The readable number, e.g. "AT-2026-00012".
    doc_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)

    # receipt / washed / write_off / count / reversal (see stock_service.py).
    doc_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    # Free text: where a receipt came from (delivery note, donor, ...).
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Why pieces were written off: damaged / lost / not_returned / other.
    reason: Mapped[str | None] = mapped_column(String(20), nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # posted, or reversed once "Ongedaan maken" was done.
    status: Mapped[str] = mapped_column(String(20), default="posted", nullable=False)

    # On a reversal: the document it undoes.
    reversal_of_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Atelier_stock_document.id"), nullable=True
    )

    # Who booked it — always the session user, with a name snapshot.
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
