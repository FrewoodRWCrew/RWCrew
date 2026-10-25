# This file defines the "Atelier_person_bracelet" table: a person's wristband
# number at one festival (every festival hands out new wristbands). The
# number is unique within its festival, and a person has one per festival.
# Written only by module_5/desk_service.py.

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierPersonBracelet(Base):
    """The wristband number of a person at a festival."""

    __tablename__ = "Atelier_person_bracelet"

    __table_args__ = (
        UniqueConstraint("festival_id", "number", name="uq_atelier_bracelet_number"),
        UniqueConstraint("person_id", "festival_id", name="uq_atelier_bracelet_person"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Atelier_person.id", ondelete="CASCADE"), index=True, nullable=False
    )
    festival_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MasterData_festival.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
