# The device-facing entry point for TagScan's CSV push feature: a
# Raspberry Pi's watcher script (see scripts/pi-watcher/) POSTs a finished
# CSV file here instead of it needing to already sit on the VPS's own
# filesystem. Modeled on app/modules/module_3/public_router.py — the
# codebase's existing pattern for an endpoint deliberately outside the
# normal get_current_user/cookie auth, here authenticated by a per-Scanner
# API key (see Scanner.api_key_hash) instead of "no auth at all".
#
# Deliberately does NOT parse the uploaded file into TagHeaderData/
# TagLineData — it only has to land the file safely into "Unreaded Tags",
# exactly like a file dropped there by any other means. The existing
# manual "Scan" button (scan_unreaded_tags(), see tag_header_data.py) is
# what actually ingests it, unchanged.

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password
from app.db.models.scanner import Scanner
from app.db.models.tag_header_data import TagHeaderData
from app.modules.module_1.file_browser import get_source_root
from app.modules.module_1.tag_header_data import READED_SUBFOLDER, UNREADED_SUBFOLDER
from app.schemas.tagscan import IntakeUploadResponse

router = APIRouter(prefix="/api/public/tagscan-intake", tags=["Tagscan (Device Intake)"])

# The non-secret prefix every generated API key starts with — see
# app/modules/module_1/router.py's generate_scanner_api_key. Lets this
# dependency find the right Scanner row with a single db.get() instead of
# hashing the candidate key against every scanner's stored hash.
API_KEY_PREFIX = "module1_"


def authenticate_scanner(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> Scanner:
    """Resolve the caller's API key to the Scanner it belongs to, or 401.

    The 401 detail is deliberately generic (never "no such scanner" vs
    "wrong key") so this endpoint can't be used to enumerate valid scanner
    ids.
    """
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if not x_api_key.startswith(API_KEY_PREFIX):
        raise invalid

    id_part, separator, _secret_part = x_api_key[len(API_KEY_PREFIX) :].partition("_")
    if not separator or not id_part.isdigit():
        raise invalid

    scanner = db.get(Scanner, int(id_part))
    if scanner is None or not scanner.api_key_hash or not verify_password(x_api_key, scanner.api_key_hash):
        raise invalid

    return scanner


@router.post("", response_model=IntakeUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_csv(
    file: UploadFile = File(...),
    scanner: Scanner = Depends(authenticate_scanner),
    db: Session = Depends(get_db),
) -> IntakeUploadResponse:
    """Receive one CSV file from a device's watcher script.

    Idempotent, so it is safe for the watcher to retry a POST whose
    response it never saw:
      - the same filename with the same bytes already in Unreaded Tags or
        Read Tags is a "duplicate" and nothing is re-written;
      - a filename already logged as TagHeaderData whose file is gone
        (so its bytes can't be compared) is also treated as a "duplicate";
      - the same filename but DIFFERENT bytes is NOT dropped — that would
        silently lose scan data — it is stored under a content-hash suffix
        (see _content_hash_name) and reported back under that stored name.
    """
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .csv files are accepted")

    max_bytes = settings.tagscan_intake_max_file_mb * 1024 * 1024
    # Read one byte past the limit so an oversized file is detected
    # without ever buffering an unbounded upload into memory.
    contents = file.file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.tagscan_intake_max_file_mb} MB limit",
        )

    root = get_source_root(db)
    unreaded_dir = root / UNREADED_SUBFOLDER
    readed_dir = root / READED_SUBFOLDER

    # Where a file of this name could already be sitting, if we have seen it.
    existing_paths = [unreaded_dir / filename, readed_dir / filename]
    name_taken = any(path.exists() for path in existing_paths)

    stored_name = filename
    already_received = False

    if name_taken:
        if any(path.exists() and path.read_bytes() == contents for path in existing_paths):
            # Identical bytes under the same name: a retried upload.
            already_received = True
        else:
            # Same name, different bytes: keep both by storing this one
            # under a name derived from its own content. Uploading it again
            # lands on that same derived name, so the retry is still safe.
            stored_name = _content_hash_name(filename, contents)
            already_received = (unreaded_dir / stored_name).exists() or (readed_dir / stored_name).exists()
    elif db.scalar(select(TagHeaderData).where(TagHeaderData.filename == filename)) is not None:
        # Already ingested and its file is no longer on disk to compare
        # against — the same trust-the-filename rule as before.
        already_received = True

    if not already_received:
        # Write under a temporary name first, then atomically rename into
        # place, so a file the "Scan" button might read concurrently is
        # never visible half-written.
        unreaded_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = unreaded_dir / f"{stored_name}.uploading"
        tmp_path.write_bytes(contents)
        tmp_path.replace(unreaded_dir / stored_name)

    scanner.api_key_last_used_at = datetime.now(timezone.utc)
    db.commit()

    return IntakeUploadResponse(status="duplicate" if already_received else "received", filename=stored_name)


def _content_hash_name(filename: str, contents: bytes) -> str:
    """Derive a collision-free filename from the file's own bytes.

    "scan.csv" becomes "scan__<12 hex chars of sha256>.csv" — the same
    content always maps to the same name, different content to a different
    one.
    """
    path = Path(filename)
    digest = hashlib.sha256(contents).hexdigest()[:12]
    return f"{path.stem}__{digest}{path.suffix}"
