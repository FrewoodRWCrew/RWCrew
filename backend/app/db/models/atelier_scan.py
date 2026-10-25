# This file defines the "Atelier_scan" table: every wristband-scan message
# that reached Atelier — from the wristband company's webhook, or from the
# Test-scan screen — including refused and ignored ones, so it's always
# visible what was sent. A "new" scan shows up live on the desk screen of its
# scanner; once a transaction used it, it becomes "used". Written only by
# module_5/scan_service.py.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtelierScan(Base):
    """One received scan message."""

    __tablename__ = "Atelier_scan"

    id: Mapped[int] = mapped_column(primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    # "webhook" (the wristband company) or "test" (the Test-scan screen).
    source: Mapped[str] = mapped_column(String(20), default="webhook", nullable=False)

    # new / used / dismissed / ignored (other event) / refused (bad token, unreadable).
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    # Why a message was refused or ignored (for the log).
    status_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # The message's fields (all optional: a refused message may have none).
    event: Mapped[str | None] = mapped_column(String(100), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # data.id: the person's wristband number for this festival.
    wristband_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # data.attending_group.name, and our team when that name matched one.
    team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("MasterData_team.id", ondelete="SET NULL"), nullable=True
    )
    profile_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # The message exactly as received (text, since it may not even be JSON).
    raw: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When a desk transaction used it, and for whom.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Atelier_person.id", ondelete="SET NULL"), nullable=True
    )
