# This file defines the "Atelier_scanner" table: the wristband company's
# scanners that sent scans to Atelier. A scanner is registered automatically
# by its first message (data.device.id); the atelier can give it a label such
# as "Balie 1", and every desk screen picks the scanner standing at its
# counter. Written only by module_5/scan_service.py and the settings screen.

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierScanner(Base):
    """One scanner (device) of the wristband company."""

    __tablename__ = "Atelier_scanner"

    id: Mapped[int] = mapped_column(primary_key=True)

    # data.device.id of the messages (stored as text).
    device_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    # data.device.name as last sent, e.g. "SUN0410".
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Our own name for it, e.g. "Balie 1" (empty = the device name is shown).
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
