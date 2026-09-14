# This file defines the "Tagscan_settings" table: a single-row (id=1)
# settings record for TagScan, currently holding just the VPS-side CSV
# intake "receive folder" path. When receive_folder_path is NULL, the app
# falls back to the .env-configured settings.tagscan_source_dir default —
# see get_source_root() in app/modules/module_1/file_browser.py, the one
# place this table is actually read. Editable from the module's own
# Settings screen ("tagscan.settings"), gated the same custom-roles way
# as every other TagScan screen.

from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class TagscanSettings(Base):
    """A single row (id=1) of TagScan-wide settings."""

    __tablename__ = "Tagscan_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # NULL means "no override saved yet — use the .env default".
    receive_folder_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
