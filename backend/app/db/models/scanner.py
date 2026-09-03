# This file defines the "Tagscan_scanners" database table: TagScan's
# registry of physical RFID-reader devices (e.g. Raspberry Pi boxes) that
# produce the CSV files scanned by the "Tag Headerdata" screen.
#
# scanner is the device's human-readable name and must be unique: it's
# also the exact value matched against the CSV's own "Scanner" column
# during a scan/Synchro (see app/modules/module_1/tag_line_data.py's
# match_scanner()), so two devices sharing a name would make that
# matching ambiguous.
#
# type_id is required (unlike most optional cross-module lookups in this
# codebase) — every scanner must be classified with a product type from
# MasterData before it can be registered.
#
# technology is a closed, domain-defined set of 4 values ("Raspberry Pi
# 3"/"4"/"5"/"Other") — enforced as a Literal in the Pydantic schemas
# (see app/schemas/tagscan.py), not a separate manageable lookup table,
# the same way RfidTag.status works.

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Scanner(Base):
    """One row per registered physical RFID-reader device."""

    __tablename__ = "Tagscan_scanners"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The device's name — must be unique so it can be matched unambiguously
    # against a CSV's "Scanner" column.
    scanner: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Which product type (from MasterData) this scanner is classified as —
    # required.
    type_id: Mapped[int] = mapped_column(ForeignKey("MasterData_product_type.id"), nullable=False)

    technology: Mapped[str] = mapped_column(String(50), nullable=False)

    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    info1: Mapped[str | None] = mapped_column(Text, nullable=True)
    info2: Mapped[str | None] = mapped_column(Text, nullable=True)
    info3: Mapped[str | None] = mapped_column(Text, nullable=True)
