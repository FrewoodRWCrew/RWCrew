#!/usr/bin/env python3
"""TagScan device-intake watcher.

Polls WATCH_DIR for *.csv files that have stopped growing (their size is
unchanged between two consecutive poll ticks — the producing app should
write "file.csv.tmp" then rename() it to "file.csv" so a finished file
never looks half-written here), POSTs each one to the TagScan backend's
device-intake endpoint with an API key, and on any 2xx response moves it
into SENT_DIR. On failure (network error, non-2xx response), the file is
left in place and retried on the next tick.

Stdlib only, on purpose: the same watcher.py runs unmodified as multiple
systemd-template instances (dev/prod, see tagscan-watcher@.service) on one
Raspberry Pi, each pointed at a different backend/API key/folder purely
through its own environment file — nothing here is environment-specific,
and nothing needs "pip install" on the Pi.

Required environment variables:
  API_URL   - the device-intake endpoint, e.g. https://vps.example.com/api/public/tagscan-intake
  API_KEY   - this device's API key, generated on the backend's Scanners screen
  WATCH_DIR - local folder to watch for finished *.csv files
  SENT_DIR  - local folder finished uploads are moved into

Optional:
  POLL_INTERVAL_SECONDS - how often to check WATCH_DIR (default: 15)
"""

from __future__ import annotations

import logging
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tagscan-watcher")


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        log.error("Missing required environment variable: %s", name)
        sys.exit(1)
    return value


API_URL = _required_env("API_URL")
API_KEY = _required_env("API_KEY")
WATCH_DIR = Path(_required_env("WATCH_DIR"))
SENT_DIR = Path(_required_env("SENT_DIR"))
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "15"))


def _build_multipart_body(filename: str, content: bytes) -> tuple[bytes, str]:
    """A minimal, hand-built multipart/form-data body for one file field
    named "file" — matches what FastAPI's UploadFile expects, without
    needing the "requests" library (or any pip install) on the Pi.
    """
    boundary = uuid.uuid4().hex
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: text/csv\r\n\r\n",
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def _upload(path: Path) -> bool:
    """POST one file to the backend. Returns True on any 2xx response —
    both "received" and "duplicate" are 2xx (see device_router.py), so a
    file the backend already has from an earlier, dropped-response retry
    is still correctly treated as delivered here.
    """
    body, content_type = _build_multipart_body(path.name, path.read_bytes())
    request = urllib.request.Request(
        API_URL, data=body, method="POST", headers={"X-API-Key": API_KEY, "Content-Type": content_type}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            log.info("Uploaded %s -> HTTP %s", path.name, response.status)
            return 200 <= response.status < 300
    except urllib.error.HTTPError as error:
        log.error("Upload of %s failed: HTTP %s %s", path.name, error.code, error.read().decode(errors="replace"))
        return False
    except OSError as error:
        log.error("Upload of %s failed: %s", path.name, error)
        return False


def _move_to_sent(path: Path) -> None:
    SENT_DIR.mkdir(parents=True, exist_ok=True)
    destination = SENT_DIR / path.name
    path.replace(destination)
    log.info("Moved %s -> %s", path.name, destination)


def _stable_csv_files(previous_sizes: dict[str, int]) -> list[Path]:
    """Every *.csv file directly inside WATCH_DIR whose size hasn't
    changed since the previous poll tick. A file seen for the first time
    this tick is never returned yet, even if it's actually already
    finished — it simply waits one extra tick before being considered.
    previous_sizes is updated in place to the current tick's sizes.
    """
    if not WATCH_DIR.is_dir():
        previous_sizes.clear()
        return []

    current_sizes: dict[str, int] = {}
    stable: list[Path] = []
    for entry in sorted(WATCH_DIR.iterdir()):
        if not entry.is_file() or entry.suffix.lower() != ".csv":
            continue
        try:
            size = entry.stat().st_size
        except OSError:
            continue
        current_sizes[entry.name] = size
        if previous_sizes.get(entry.name) == size:
            stable.append(entry)

    previous_sizes.clear()
    previous_sizes.update(current_sizes)
    return stable


def main() -> None:
    log.info("Watching %s, sending to %s every %ss", WATCH_DIR, API_URL, POLL_INTERVAL_SECONDS)
    previous_sizes: dict[str, int] = {}
    while True:
        for path in _stable_csv_files(previous_sizes):
            if _upload(path):
                _move_to_sent(path)
                previous_sizes.pop(path.name, None)
            # On failure the file is left exactly where it is, untouched
            # by previous_sizes bookkeeping, so it's retried next tick.
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
