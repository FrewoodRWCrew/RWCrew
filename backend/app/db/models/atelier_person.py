# This file defines the "Atelier_person" table: the workers who picked up
# clothing at the Atelier counter. They aren't RWCrew users: the desk types a
# first name, a family name and an email address. The **combination of first
# name and family name** is the person's key (compared without case and extra
# spaces, kept in `name_key`), so typing the same name finds the same person
# again next time; the email is optional and not unique. Their wristband
# number differs per festival: see Atelier_person_bracelet.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierPerson(Base):
    """One worker known at the counter."""

    __tablename__ = "Atelier_person"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # "first|last" in lowercase with single spaces: unique, how the desk
    # recognises a returning worker (see desk_service.name_key).
    name_key: Mapped[str] = mapped_column(String(511), unique=True, index=True, nullable=False)

    # Optional and not unique (the latest one typed or scanned wins).
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)

    # The team of their latest pick-up (a convenience default at the desk).
    last_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("MasterData_team.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def full_name(self) -> str:
        """"First Last", as the screens and PDFs show it."""
        return f"{self.first_name} {self.last_name}"
