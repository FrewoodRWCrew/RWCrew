# The Scans module's (module-1) wristband part, next to its RFID part in
# router.py: the browser over the .json files (a copy of the CSV Source Files
# screen, reusing file_browser.py on the JSON folder), the table of received
# scans, the wristband company's scanners with our labels, the webhook details
# for the Settings screen and sending a test scan. The processing itself is
# shared with the modules that have a counter: see app/modules/wristband.
# Its own APIRouter on the module's /api/modules/module-1 prefix, under the
# same Roles/Users as the RFID part.

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.timezone import BELGIAN_TZ
from app.db.models.user import User
from app.db.models.wristband_scan import WristbandScan
from app.db.models.wristband_scanner import WristbandScanner
from app.modules.module_1.deps import require_screen_permission
from app.modules.module_1.file_browser import (
    build_folder_tree,
    delete_files_under,
    list_files_under,
    read_file_preview,
    resolve_path_under,
)
from app.modules.wristband.json_files import source_root
from app.modules.wristband.test_routes import register_scan_test_routes, scan_log_entries
from app.modules.wristband.webhook_router import WEBHOOK_PATH
from app.modules.wristband.webhook_token import generate_token, revoke_token, token_status
from app.schemas.tagscan import (
    FileContentResponse,
    FileDeleteRequest,
    FileDeleteResponse,
    FileEntryResponse,
    FolderNode,
)
from app.schemas.wristband import (
    ScanLogEntry,
    ScannerLabelRequest,
    ScannerResponse,
    WristbandSettingsResponse,
    WristbandTokenResponse,
)

router = APIRouter(prefix="/api/modules/module-1/wristband", tags=["Scans (wristbands)"])

FILES_SCREEN = "tagscan.wristband-files"
SCANS_SCREEN = "tagscan.wristband-scans"
SCANNERS_SCREEN = "tagscan.wristband-scanners"
TEST_SCREEN = "tagscan.wristband-test"
SETTINGS_SCREEN = "tagscan.settings"

# The table never sends more rows than this; the filters narrow it down.
MAX_SCANS = 1000

# /api/modules/module-1/wristband/wristband-test/...: sending a test scan
# (shared with Atelier and Walkies).
register_scan_test_routes(
    router,
    require_view=require_screen_permission(TEST_SCREEN, "view"),
    require_send=require_screen_permission(TEST_SCREEN, "create"),
)


# --- JSON source files -------------------------------------------------------------------


@router.get("/files/tree", response_model=FolderNode)
def get_folder_tree(
    _user: User = Depends(require_screen_permission(FILES_SCREEN, "view")),
) -> FolderNode:
    """The JSON folder's structure: one folder per day."""
    return build_folder_tree(source_root())


@router.get("/files", response_model=list[FileEntryResponse])
def get_folder_files(
    path: str = "",
    _user: User = Depends(require_screen_permission(FILES_SCREEN, "view")),
) -> list[FileEntryResponse]:
    """The files directly inside one folder."""
    root = source_root()
    folder = resolve_path_under(root, path)
    if not folder.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return list_files_under(root, folder)


@router.get("/files/content", response_model=FileContentResponse)
def get_file_content(
    path: str,
    _user: User = Depends(require_screen_permission(FILES_SCREEN, "view")),
) -> FileContentResponse:
    """One file's text, for the "notepad" preview pane."""
    file = resolve_path_under(source_root(), path)
    if not file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    content, truncated = read_file_preview(file)
    return FileContentResponse(path=path, content=content, truncated=truncated)


@router.post("/files/delete", response_model=FileDeleteResponse)
def delete_source_files(
    payload: FileDeleteRequest,
    _user: User = Depends(require_screen_permission(FILES_SCREEN, "delete")),
) -> FileDeleteResponse:
    """Permanently delete the checked files; their table rows stay."""
    return FileDeleteResponse(deleted=delete_files_under(source_root(), payload.paths))


# --- The scans -----------------------------------------------------------------------------


@router.get("/scans", response_model=list[ScanLogEntry])
def list_scans(
    day: date | None = Query(default=None),
    scan_status: str | None = Query(default=None, alias="status", max_length=20),
    device_id: str | None = Query(default=None, max_length=100),
    team: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SCANS_SCREEN, "view")),
) -> list[ScanLogEntry]:
    """The received messages, newest first, with the filters applied. `day`
    is a Belgian calendar day, `team` a part of the team name as sent."""
    query = select(WristbandScan)
    if day is not None:
        start = datetime(day.year, day.month, day.day, tzinfo=BELGIAN_TZ)
        query = query.where(WristbandScan.received_at >= start, WristbandScan.received_at < start + timedelta(days=1))
    if scan_status:
        query = query.where(WristbandScan.status == scan_status)
    if device_id:
        query = query.where(WristbandScan.device_id == device_id)
    if team:
        query = query.where(func.lower(WristbandScan.team_name).contains(team.strip().lower()))
    scans = db.scalars(query.order_by(WristbandScan.id.desc()).limit(MAX_SCANS)).all()
    return scan_log_entries(db, list(scans))


# --- Scanners ------------------------------------------------------------------------------


@router.get("/scanners", response_model=list[ScannerResponse])
def list_scanners(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SCANNERS_SCREEN, "view")),
) -> list[WristbandScanner]:
    """Every scanner that ever sent a message."""
    return list(db.scalars(select(WristbandScanner).order_by(WristbandScanner.device_id)).all())


@router.put("/scanners/{scanner_id}", response_model=ScannerResponse)
def put_scanner_label(
    scanner_id: int,
    payload: ScannerLabelRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SCANNERS_SCREEN, "edit")),
) -> WristbandScanner:
    """Give a scanner our own name (e.g. "Balie 1")."""
    scanner = db.get(WristbandScanner, scanner_id)
    if scanner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner not found")
    scanner.label = (payload.label or "").strip() or None
    db.commit()
    return scanner


# --- Settings ------------------------------------------------------------------------------


@router.get("/settings", response_model=WristbandSettingsResponse)
def get_wristband_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SETTINGS_SCREEN, "view")),
) -> WristbandSettingsResponse:
    """The webhook address, the token's state (never the token) and the JSON folder."""
    row = token_status(db)
    return WristbandSettingsResponse(
        webhook_path=WEBHOOK_PATH,
        webhook_token_configured=bool(row and row.wristband_token_hash),
        webhook_token_generated_at=row.wristband_token_generated_at if row else None,
        webhook_token_last_used_at=row.wristband_token_last_used_at if row else None,
        source_folder=settings.wristband_source_dir,
    )


@router.post("/settings/token", response_model=WristbandTokenResponse)
def post_wristband_token(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SETTINGS_SCREEN, "edit")),
) -> WristbandTokenResponse:
    """Generate this environment's webhook token, replacing the old one; the
    key is only ever sent in this answer."""
    token = generate_token(db)
    db.commit()
    return WristbandTokenResponse(token=token)


@router.delete("/settings/token", status_code=status.HTTP_204_NO_CONTENT)
def delete_wristband_token(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SETTINGS_SCREEN, "edit")),
) -> None:
    """Revoke the token: every webhook message is refused from now on."""
    revoke_token(db)
    db.commit()
