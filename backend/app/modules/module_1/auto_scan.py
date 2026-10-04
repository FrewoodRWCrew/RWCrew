# TagScan's automatic background Scan: does what the "Scan" button on the
# Tag Headerdata screen does (scan_unreaded_tags — log every new CSV in
# "Unreaded Tags" and move it to "Read Tags"), without anyone clicking.
#
# On/off and the interval are user settings (Tagscan_settings, edited on
# TagScan's Settings screen); no settings row yet = on, every 60 seconds.
# The loop wakes up every TICK_SECONDS and re-reads the settings, so a
# changed interval or toggle applies within seconds, without a restart.
#
# Runs inside the backend process (started from main.py's lifespan). The
# backend runs as ONE uvicorn process per environment (see backend/
# Dockerfile), so the job runs exactly once per environment. SCAN_LOCK keeps
# the background run and a manual Scan click from moving the same files at
# the same time.

import asyncio
import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.db.models.tagscan_settings import TagscanSettings
from app.modules.module_1.file_browser import SETTINGS_ROW_ID
from app.modules.module_1.tag_header_data import scan_unreaded_tags

logger = logging.getLogger(__name__)

# Shared by the manual Scan endpoint and the background job.
SCAN_LOCK = threading.Lock()

# How often the loop wakes up to check whether a scan is due.
TICK_SECONDS = 5

# Used when no settings row exists yet.
DEFAULT_ENABLED = True
DEFAULT_INTERVAL_SECONDS = 60


def run_auto_scan_once(
    session_factory: Callable[[], Session] = SessionLocal,
    now: datetime | None = None,
) -> bool:
    """Run one background Scan if it's switched on and due. Returns True
    when a scan actually ran. Never raises: any failure is logged, so one
    bad run can't stop the loop.
    """
    now = now or datetime.now(timezone.utc)
    try:
        with session_factory() as db:
            row = db.get(TagscanSettings, SETTINGS_ROW_ID)
            enabled = row.auto_scan_enabled if row is not None else DEFAULT_ENABLED
            interval = row.auto_scan_interval_seconds if row is not None else DEFAULT_INTERVAL_SECONDS
            if not enabled:
                return False

            # Not due yet: the last run was less than one interval ago.
            last_run = row.last_auto_scan_at if row is not None else None
            if last_run is not None:
                if last_run.tzinfo is None:
                    last_run = last_run.replace(tzinfo=timezone.utc)
                if now - last_run < timedelta(seconds=interval):
                    return False

            # A manual Scan is busy right now: try again on the next tick.
            if not SCAN_LOCK.acquire(blocking=False):
                return False
            try:
                results, _entries = scan_unreaded_tags(db)
            finally:
                SCAN_LOCK.release()

            logged = sum(1 for result in results if result.outcome == "logged")
            skipped = sum(1 for result in results if result.outcome == "skipped_duplicate")
            errors = sum(1 for result in results if result.outcome == "error")
            summary = f"{logged} logged, {skipped} skipped, {errors} errors"
            if logged or errors:
                logger.info("TagScan automatic scan: %s", summary)
            for result in results:
                if result.outcome == "error":
                    logger.warning("TagScan automatic scan: %s — %s", result.filename, result.detail)

            # Remember the run (creating the settings row on first use; its
            # receive_folder_path stays NULL = the .env default).
            row = db.get(TagscanSettings, SETTINGS_ROW_ID)
            if row is None:
                row = TagscanSettings(id=SETTINGS_ROW_ID)
                db.add(row)
            row.last_auto_scan_at = now
            row.last_auto_scan_summary = summary
            db.commit()
            return True
    except Exception:
        logger.exception("TagScan automatic scan failed")
        return False


async def auto_scan_loop() -> None:
    """Forever: run a scan when due (in a worker thread — the scan does
    blocking file and database work), then sleep one tick. Ends when the
    task is cancelled at shutdown.
    """
    logger.info("TagScan automatic scan worker started")
    while True:
        await asyncio.to_thread(run_auto_scan_once)
        await asyncio.sleep(TICK_SECONDS)
