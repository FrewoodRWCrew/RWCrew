# This file defines the "Atelier_handout" table: one pick-up at the Atelier
# counter ("Ophalen") — a person of a team, at a festival, on a day — with its
# pieces in Atelier_handout_line and its stock booking (available → handed
# out) in Atelier_stock_document. Written only by module_5/desk_service.py.

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierHandout(Base):
    """One pick-up of clothing by one person."""

    __tablename__ = "Atelier_handout"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("Atelier_person.id"), index=True, nullable=False)
    festival_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_festival.id"), index=True, nullable=False
    )
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("MasterData_team.id"), index=True, nullable=False)

    # The festival day the clothing was picked up for.
    day: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    # The stock booking of the pick-up (available → handed out).
    stock_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("Atelier_stock_document.id"), nullable=False)

    # open (pieces still out) / returned (all back) / cancelled (undone at the desk).
    status: Mapped[str] = mapped_column(String(20), default="open", index=True, nullable=False)

    # Who handed it out — always the session user, with a name snapshot.
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
