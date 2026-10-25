# The public entry point of Atelier's wristband scans (block 5): the
# wristband company posts one JSON message per scan at our counter to
#   POST /api/public/atelier/wristband-scan
# Outside the normal cookie login (like TagScan's device intake,
# module_1/device_router.py); the message's own "token" is checked against
# settings.atelier_webhook_token (ATELIER_WEBHOOK_TOKEN in the server's .env).
# Every message is logged — refused ones too — by
# scan_service.process_message, so Atelier > Instellingen shows what arrived.
#
# Answers: 200 accepted (or ignored: another event), 400 unreadable or
# missing fields, 401 wrong/missing token. The body is read raw (not parsed
# by FastAPI) so even an unreadable message is logged.

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.module_5.scan_service import WEBHOOK, process_message

router = APIRouter(prefix="/api/public/atelier", tags=["Atelier (wristband webhook)"])

# Larger messages are cut off: a scan message is a few hundred bytes.
MAX_BODY_BYTES = 100_000


@router.post("/wristband-scan")
async def receive_wristband_scan(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    """Log one scan message and hand it to the desk screen of its scanner."""
    body = (await request.body())[:MAX_BODY_BYTES].decode("utf-8", errors="replace")
    result = process_message(db, body, source=WEBHOOK, expected_token=settings.atelier_webhook_token)
    db.commit()
    return JSONResponse(
        status_code=result.http_status,
        content={"status": result.scan.status, "detail": result.scan.status_detail, "scan_id": result.scan.id},
    )
