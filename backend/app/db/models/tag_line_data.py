# This file defines the "Tagscan_line_data" database table: one row per
# data line found inside a CSV scanned by the "Tag Headerdata" screen's
# Scan action. Each line is linked back to the header row it came from
# (header_data_id), and — when its EPC matches a registered RFID tag —
# enriched with a snapshot of that tag's key fields at scan time (not a
# live join), so a line's history survives the tag being reassigned or
# edited later. status starts out "converted" or "no_match" automatically
# during the scan; "cancelled" is a separate, manual action a user takes
# afterwards on the Tag Linedata screen — see app/modules/module_1/
# tag_line_data.py.
#
# The same snapshot approach is used for the raw "scanner" column: when it
# matches a registered Scanners device by name, scanner_id/scanner_name/
# scanner_location/scanner_technology are populated from that device at
# scan/Synchro time — again not a live join, so a line's history survives
# the Scanners record being renamed or edited later.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class TagLineData(Base):
    """One row per CSV data line processed by a Tag Headerdata scan."""

    __tablename__ = "Tagscan_line_data"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which scanned file this line came from.
    header_data_id: Mapped[int] = mapped_column(
        ForeignKey("Tagscan_header_data.id"), nullable=False, index=True
    )

    # The CSV's own physical row number (the header row is row 1), so a
    # line can be traced back to its exact place in the source file.
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # The raw scanned columns, stored as-is — no datetime reconstruction,
    # since the CSV's "Last Seen" column is only a time-of-day with no date.
    scanner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    epc: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rssi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    antenna: Mapped[int | None] = mapped_column(Integer, nullable=True)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # The "Mode" and "Action" CSV values: the row's own cell, or the file's
    # header-level value (see TagHeaderData) when that cell is empty. Free
    # text, null when neither has a value.
    mode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Which registered tag this EPC matched, if any — null means "no_match".
    rfid_tag_id: Mapped[int | None] = mapped_column(ForeignKey("Tagscan_rfid_tag.id"), nullable=True)

    # A snapshot of the matched tag's key fields at scan time (deliberately
    # NOT a live join to RfidTag/Product — see module docstring above).
    assigned_product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Which registered Scanners device the raw "scanner" text matched, if
    # any — null means no match was found (soft match — never blocks a
    # scan). A snapshot of that device's key fields at scan/Synchro time,
    # same reasoning as assigned_product_name above.
    scanner_id: Mapped[int | None] = mapped_column(ForeignKey("Tagscan_scanners.id"), nullable=True)
    scanner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scanner_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    scanner_technology: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
