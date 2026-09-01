# This file defines the "Tagscan_rfid_tag" database table: TagScan's
# registry of physical RFID tags used in the inventory project.
#
# status is a closed, domain-defined set of 5 values (active/inactive/
# lost/damaged/retired) — enforced as a Literal in the Pydantic schemas
# (see app/schemas/tagscan.py), not a separate manageable lookup table,
# since these aren't values an admin should be adding/renaming/deleting.
#
# assigned_serial_number is plain text for now rather than a real foreign
# key — there's no serial-numbers table anywhere in this codebase yet, so
# this keeps the door open to upgrade it later once that concept exists.

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class RfidTag(Base):
    """One row per physical RFID tag that's been registered."""

    __tablename__ = "Tagscan_rfid_tag"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The real-world identifier encoded on the chip itself. Must be
    # unique so the same physical tag can't accidentally be registered
    # twice.
    epc_uid: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Which product (from MasterData) this tag is currently attached to —
    # optional, since a tag can be registered before being assigned.
    assigned_product_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_product.id"), nullable=True)
    assigned_serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Set automatically the moment the row is created.
    date_registered: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_assigned: Mapped[date | None] = mapped_column(Date, nullable=True)

    # No RFID-reader integration exists yet to populate these
    # automatically — they're plain editable fields for now, the same way
    # Product's own fields started out as plain text before any fixed
    # rules existed for them.
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reader_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    notes_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_3: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_4: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_5: Mapped[str | None] = mapped_column(Text, nullable=True)
