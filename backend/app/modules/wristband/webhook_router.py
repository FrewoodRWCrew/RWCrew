# The public entry point of the wristband scans: the wristband company posts
# one JSON message per scan at one of our counters to
#   POST /api/public/wristband-scan
# Outside the normal cookie login (like the RFID device intake,
# module_1/device_router.py); the message's own "token" must be the one
# generated on the Scans module's Settings screen (webhook_token.py). Every
# message is logged — refused ones too — by
# scan_service.process_message, so the Scans module shows what arrived.
#
# Answers: 200 accepted (or ignored: another event), 400 unreadable or
# missing fields, 401 wrong/missing token. The body is read raw (not parsed
# by FastAPI) so even an unreadable message is logged.

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.wristband.scan_service import WEBHOOK, process_message
from app.modules.wristband.webhook_token import token_is_valid

router = APIRouter(prefix="/api/public", tags=["Wristband webhook"])

# Shown on the Scans module's Settings screen.
WEBHOOK_PATH = "/api/public/wristband-scan"

# Larger messages are cut off: a scan message is a few hundred bytes.
MAX_BODY_BYTES = 100_000


@router.post("/wristband-scan")
async def receive_wristband_scan(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    """Log one scan message and hand it to the desk screen of its scanner."""
    body = (await request.body())[:MAX_BODY_BYTES].decode("utf-8", errors="replace")
    result = process_message(db, body, source=WEBHOOK, check_token=lambda token: token_is_valid(db, token))
    db.commit()
    return JSONResponse(
        status_code=result.http_status,
        content={"status": result.scan.status, "detail": result.scan.status_detail, "scan_id": result.scan.id},
    )
