# This file defines the "Tagscan_header_data" database table: a log of
# every incoming CSV file from TagScan's "Unreaded Tags" intake folder
# that has been scanned/processed by the "Tag Headerdata" screen. Each
# row is created once, permanently, the moment a file is first processed
# — filename carries a unique constraint so the same file can never be
# logged (and hence never re-processed/re-moved) twice, even under a
# concurrent scan — see app/modules/module_1/tag_header_data.py for the
# scan logic itself.
#
# scanner/scanner_id/scanner_name/scanner_location/scanner_technology are
# derived from the first non-empty "Scanner" value found among that file's
# parsed CSV rows (every row in one CSV comes from the same physical
# device), matched against the Scanners registry by name the same way a
# Tag Linedata row is (see app/modules/module_1/tag_line_data.py's
# match_scanner()) — a snapshot, not a live join, refreshed by "Synchro".

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class TagHeaderData(Base):
    """One row per CSV file that has been scanned out of "Unreaded Tags"."""

    __tablename__ = "Tagscan_header_data"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The CSV file's name only (no path) — unique so the same physical
    # file is never logged/processed twice, enforced at the DB level
    # (not just in application code) via a unique index.
    filename: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Server-side timestamp, set automatically the moment the row is
    # created — never supplied by the client.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Number of data lines logged into Tagscan_line_data for this file at
    # scan time (i.e. len(parsed_rows) — the CSV's header row and any
    # skipped blank line are NOT counted), so this always matches how
    # many rows actually show up for this file on the Tag Linedata screen.
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # The raw "Scanner" CSV value for this file (see module docstring
    # above), and — when it matches a registered Scanners device by name —
    # a snapshot of that device's key fields. Null scanner_id means no
    # match was found (soft match — never blocks a scan).
    scanner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scanner_id: Mapped[int | None] = mapped_column(ForeignKey("Tagscan_scanners.id"), nullable=True)
    scanner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scanner_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    scanner_technology: Mapped[str | None] = mapped_column(String(50), nullable=True)
