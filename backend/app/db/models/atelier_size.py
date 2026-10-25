# This file defines the "Atelier_size" table: the clothing sizes Atelier's
# articles come in (Masterdata > Artikelen > Maten). A size is a name plus a
# fit — "M · Women" and "M · Men" are two different sizes, because a women's
# M is cut differently from a men's M. "OneSize" (Unisex) is for articles
# that come in one size only (a cap, a bandana, ...).

from sqlalchemy import Boolean, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# The fixed list of fits, in the order the screens group them (the
# frontend translates the codes). Not a table: these never change.
FITS: tuple[str, ...] = ("women", "men", "unisex")


class AtelierSize(Base):
    """One row per size (name + fit), e.g. "M · Women"."""

    __tablename__ = "Atelier_size"

    # The same name can exist once per fit ("M" for Women, Men and Unisex).
    __table_args__ = (UniqueConstraint("name", "fit", name="uq_atelier_size_name_fit"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # The size itself, e.g. "XS", "M", "XXL", "OneSize".
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Who the size is cut for: one of FITS.
    fit: Mapped[str] = mapped_column(String(10), nullable=False)

    # Order within its fit (XS before S before M ...), lowest first.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

    # An inactive size can't be added to an article any more; articles that
    # already have it keep it.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
