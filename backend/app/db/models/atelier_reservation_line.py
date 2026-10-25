# This file defines the "Atelier_reservation_line" table: a reservation's
# package — which articles every member of the team gets at that festival,
# and how many pieces per person (e.g. 2 T-shirts + 1 hoodie). The size is
# not part of it: it's chosen at the counter desk. Edited together with the
# number of persons on the Reservaties screen; written only by
# module_5/reservation_service.py.

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierReservationLine(Base):
    """One package line: each person of the reservation's team gets N of this article."""

    __tablename__ = "Atelier_reservation_line"

    # An article appears once in a reservation's package.
    __table_args__ = (UniqueConstraint("reservation_id", "article_id", name="uq_atelier_reservation_line"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    reservation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Atelier_reservation.id", ondelete="CASCADE"), index=True, nullable=False
    )
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("Atelier_article.id"), nullable=False)

    # How many pieces of the article each person gets (≥ 1).
    quantity_per_person: Mapped[int] = mapped_column(Integer, nullable=False)
