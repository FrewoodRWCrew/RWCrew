# This file defines the "Atelier_return_status" table: why a piece came back
# with a problem (Masterdata > Retourstatussen), e.g. "Beschadigd" or "Zeer
# vuil". The desk picks one per piece on Terugbrengen; it is only a remark and
# doesn't change the stock booking.

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierReturnStatus(Base):
    """One row per return status."""

    __tablename__ = "Atelier_return_status"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The status as shown in the desk's dropdown.
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # An inactive status can't be picked any more; returned pieces keep it.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
