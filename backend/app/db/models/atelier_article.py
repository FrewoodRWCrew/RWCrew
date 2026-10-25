# This file defines the "Atelier_article" table: Atelier's own catalogue of
# work clothing (Masterdata > Artikelen), e.g. "T-shirt crew zwart" or
# "Hoodie VIP". Separate from StockMaster's products: clothing comes in
# sizes (see Atelier_article_size) and is always handed out and taken back.

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, LargeBinary, Numeric, String, Text, false, text
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.core.database import Base


class AtelierArticle(Base):
    """One row per clothing article (all its sizes together)."""

    __tablename__ = "Atelier_article"

    id: Mapped[int] = mapped_column(primary_key=True)

    # A short unique code, e.g. "TS-CREW-ZW" — what the XLSX imports and,
    # later, the purchase orders refer to.
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # The name shown everywhere, e.g. "T-shirt crew zwart".
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free text, e.g. "Zwart" or "Navy met wit logo".
    colour: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Purchase price per piece (optional), for the value of the stock later.
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Whether each piece carries an RFID tag (TagScan) — prepared for the
    # per-piece tracing phase, nothing uses it yet.
    is_tag_managed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)

    # An inactive article can't be added to a team package any more.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    # The optional picture, stored as bytes the same way as StockMaster's
    # product pictures; deferred so listing articles never loads it.
    image_data: Mapped[bytes | None] = deferred(mapped_column(LargeBinary, nullable=True))
    image_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # When the picture last changed (the frontend adds it to the URL so a
    # replaced picture isn't served from the browser's cache).
    image_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def has_image(self) -> bool:
        """Whether a picture has been uploaded (checked without loading its bytes)."""
        return self.image_content_type is not None
