# Atelier's (module-5) "Instellingen" group (block 5): the settings screen
# (the switch "Polsband verplicht bij Ophalen", the scanners with their own
# labels, the webhook address and the log of every received scan message)
# and the Test-scan screen, which sends a message through exactly the same
# processing as the wristband company's webhook — without its token — so the
# whole flow can be tried before the company is connected (May 2027). Its own
# APIRouter on the module's /api/modules/module-5 prefix.

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.db.models.atelier_scan import AtelierScan
from app.db.models.atelier_scanner import AtelierScanner
from app.db.models.atelier_settings import AtelierSettings
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.module_5.deps import require_screen_permission, require_view_on_any
from app.modules.module_5.scan_service import TEST, process_message
from app.schemas.atelier import (
    AtelierSettingsRequest,
    AtelierSettingsResponse,
    ScanLogEntry,
    ScannerLabelRequest,
    ScannerResponse,
    ScanResponse,
    TeamSummaryResponse,
    TestScanRequest,
    TestScanResponse,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

SETTINGS_SCREEN = "atelier.settings"
SCAN_TEST_SCREEN = "atelier.scantest"

# Where the wristband company posts (shown on the settings screen).
WEBHOOK_PATH = "/api/public/atelier/wristband-scan"


def _settings_row(db: Session) -> AtelierSettings:
    """The single settings row (created when missing)."""
    row = db.get(AtelierSettings, 1)
    if row is None:
        row = AtelierSettings(id=1, wristband_required=False)
        db.add(row)
        db.flush()
    return row


def _settings_response(row: AtelierSettings) -> AtelierSettingsResponse:
    """The settings plus the webhook address and whether its token is set."""
    return AtelierSettingsResponse(
        wristband_required=row.wristband_required,
        webhook_path=WEBHOOK_PATH,
        webhook_token_configured=bool(settings.atelier_webhook_token),
    )


@router.get("/settings", response_model=AtelierSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SETTINGS_SCREEN, "view")),
) -> AtelierSettingsResponse:
    """Atelier's settings."""
    return _settings_response(_settings_row(db))


@router.put("/settings", response_model=AtelierSettingsResponse)
def put_settings(
    payload: AtelierSettingsRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SETTINGS_SCREEN, "edit")),
) -> AtelierSettingsResponse:
    """Change Atelier's settings."""
    row = _settings_row(db)
    row.wristband_required = payload.wristband_required
    db.commit()
    return _settings_response(row)


@router.get("/scanners", response_model=list[ScannerResponse])
def list_scanners(
    db: Session = Depends(get_db),
    _user: User = Depends(require_view_on_any(SETTINGS_SCREEN, SCAN_TEST_SCREEN)),
) -> list[AtelierScanner]:
    """Every scanner that ever sent a message."""
    return list(db.scalars(select(AtelierScanner).order_by(AtelierScanner.device_id)).all())


@router.put("/scanners/{scanner_id}", response_model=ScannerResponse)
def put_scanner_label(
    scanner_id: int,
    payload: ScannerLabelRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SETTINGS_SCREEN, "edit")),
) -> AtelierScanner:
    """Give a scanner our own name (e.g. "Balie 1")."""
    scanner = db.get(AtelierScanner, scanner_id)
    if scanner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner not found")
    scanner.label = (payload.label or "").strip() or None
    db.commit()
    return scanner


@router.get("/scans", response_model=list[ScanLogEntry])
def list_scan_log(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_view_on_any(SETTINGS_SCREEN, SCAN_TEST_SCREEN)),
) -> list[AtelierScan]:
    """The latest received messages (all statuses), newest first, with the raw message."""
    return list(db.scalars(select(AtelierScan).order_by(AtelierScan.id.desc()).limit(limit)).all())


@router.get("/scan-test/teams", response_model=list[TeamSummaryResponse])
def list_test_teams(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SCAN_TEST_SCREEN, "view")),
) -> list[Team]:
    """The MasterData teams, for the Test-scan form's team dropdown."""
    return list(db.scalars(select(Team).where(Team.active.is_(True)).order_by(Team.name)).all())


@router.post("/scans/test", response_model=TestScanResponse)
def post_test_scan(
    payload: TestScanRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SCAN_TEST_SCREEN, "create")),
) -> TestScanResponse:
    """Send a message through the webhook's processing (no token check),
    marked as a test; it appears live on the desk screen of its scanner."""
    result = process_message(db, payload.raw, source=TEST, expected_token=None)
    db.commit()
    team = db.get(Team, result.scan.team_id) if result.scan.team_id else None
    return TestScanResponse(
        scan=ScanResponse.model_validate(result.scan),
        http_status=result.http_status,
        team_name_matched=team.name if team else None,
    )
