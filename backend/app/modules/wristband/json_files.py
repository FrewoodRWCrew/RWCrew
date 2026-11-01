# Every wristband message is also kept as a .json file, the wristband
# counterpart of the RFID module's CSV files: one subfolder per Belgian day
# under settings.wristband_source_dir, browsed on the Scans module's "JSON
# source files" screen. The database row (Wristband_scan) is made straight
# away by scan_service, since a counter can't wait for a file scan, so the
# file is the record of what arrived and not a step in the processing:
# failing to write one is logged and never loses a scan. Deleting a file later
# leaves its row untouched, as with the CSV files.

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.timezone import to_belgian
from app.db.models.wristband_scan import WristbandScan

logger = logging.getLogger(__name__)


def source_root() -> Path:
    """The folder holding the day folders (created when missing)."""
    root = Path(settings.wristband_source_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def file_path_for(scan: WristbandScan) -> Path:
    """Where this scan's file goes: <day>/<time>_<scan id>.json, marked when
    it's a test, so a folder sorts by time and test messages stand out."""
    received = to_belgian(scan.received_at or datetime.now(timezone.utc))
    suffix = "_test" if scan.source == "test" else ""
    return source_root() / received.strftime("%Y-%m-%d") / f"{received.strftime('%H%M%S')}_{scan.id}{suffix}.json"


def save_message_file(scan: WristbandScan) -> None:
    """Write the message exactly as received. Never raises."""
    try:
        path = file_path_for(scan)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(scan.raw or "", encoding="utf-8")
    except OSError:
        logger.exception("Could not save wristband scan %s as a file", scan.id)
