# This file defines the "MasterData_altsien_kernlid" database table:
# a contact in the "Altsien Kernleden" list, managed on MasterData's
# Altsien Kernleden screen.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AltsienKernlid(Base):
    """One row per Altsien Kernleden contact."""

    __tablename__ = "MasterData_altsien_kernlid"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone_number: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
