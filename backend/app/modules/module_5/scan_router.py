# Atelier's (module-5) "Instellingen" group: the switch "Polsband verplicht bij
# Ophalen" and the Test-scan screen, which sends a message through exactly the
# same processing as the wristband company's webhook — without its token — so
# the whole flow can be tried before the company is connected (May 2027). The
# scans, scanners and webhook itself are in the Scans module (modules/wristband,
# module_1/wristband_router.py). Its own APIRouter on the module's
# /api/modules/module-5 prefix.

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.atelier_settings import AtelierSettings
from app.db.models.user import User
from app.modules.module_5.deps import require_screen_permission
from app.modules.wristband.test_routes import register_scan_test_routes
from app.schemas.atelier import AtelierSettingsRequest, AtelierSettingsResponse

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

SETTINGS_SCREEN = "atelier.settings"
SCAN_TEST_SCREEN = "atelier.scantest"

# /wristband-test/...: sending a test wristband scan (shared with Scans and Walkies).
register_scan_test_routes(
    router,
    require_view=require_screen_permission(SCAN_TEST_SCREEN, "view"),
    require_send=require_screen_permission(SCAN_TEST_SCREEN, "create"),
)


def _settings_row(db: Session) -> AtelierSettings:
    """The single settings row (created when missing)."""
    row = db.get(AtelierSettings, 1)
    if row is None:
        row = AtelierSettings(id=1, wristband_required=False)
        db.add(row)
        db.flush()
    return row


@router.get("/settings", response_model=AtelierSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SETTINGS_SCREEN, "view")),
) -> AtelierSettingsResponse:
    """Atelier's settings."""
    return AtelierSettingsResponse(wristband_required=_settings_row(db).wristband_required)


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
    return AtelierSettingsResponse(wristband_required=row.wristband_required)
