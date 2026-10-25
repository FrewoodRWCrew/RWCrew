# KarTracker's (module-2) karcode endpoints: the "Karcode Simulator" screen
# (kar number -> code of the kar's lock) and the "Instellingen" screen where
# admins see, test and change the formula behind it. Its own APIRouter on
# the same /api/modules/module-2 prefix (included in app/main.py) so the
# big router.py doesn't grow even larger.
#
# Formula errors come back as HTTP 400 with detail "code|param" (see
# KarcodeError), translated by the frontend under karTracker.karcode.errors.

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.kartracker_settings import KarTrackerSettings
from app.db.models.user import User
from app.modules.module_2.deps import require_screen_permission
from app.modules.module_2.karcode_formula import (
    DEFAULT_KARCODE_FORMULA,
    FUNCTION_NAMES,
    KarcodeError,
    compute_code,
    validate_formula,
)
from app.schemas.kartracker import (
    KarcodeFormulaUpdateRequest,
    KarcodePreviewRequest,
    KarcodeResponse,
    KarTrackerSettingsResponse,
)

router = APIRouter(prefix="/api/modules/module-2", tags=["KarTracker"])

# The settings table holds exactly one row.
SETTINGS_ROW_ID = 1


def _settings_row(db: Session) -> KarTrackerSettings | None:
    """The settings row (inserted by the migration, so normally present)."""
    return db.get(KarTrackerSettings, SETTINGS_ROW_ID)


def _current_formula(db: Session) -> str:
    """The saved karcode formula, or the default when nothing is saved."""
    row = _settings_row(db)
    return row.karcode_formula if row is not None else DEFAULT_KARCODE_FORMULA


def _karcode_http_error(error: KarcodeError) -> HTTPException:
    """A formula/kar number that gives no code -> 400 "code|param"."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.detail)


def _settings_response(db: Session) -> KarTrackerSettingsResponse:
    """The Instellingen screen's data (defaults when no row exists yet)."""
    row = _settings_row(db)
    return KarTrackerSettingsResponse(
        karcode_formula=row.karcode_formula if row is not None else DEFAULT_KARCODE_FORMULA,
        karcode_updated_by_name=row.karcode_updated_by_name if row is not None else None,
        karcode_updated_at=row.karcode_updated_at if row is not None else None,
        karcode_functions=FUNCTION_NAMES,
    )


@router.get("/karcode", response_model=KarcodeResponse)
def get_karcode(
    kar: str = Query(min_length=1, max_length=50),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.karcodesimulator", "view")),
) -> KarcodeResponse:
    """The lock code of one kar number, with the saved formula. The formula
    itself is not returned: simulator users only see the code.
    """
    try:
        code = compute_code(_current_formula(db), kar)
    except KarcodeError as error:
        raise _karcode_http_error(error) from error
    return KarcodeResponse(kar=kar.strip(), code=code)


@router.get("/settings", response_model=KarTrackerSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("kartracker.settings", "view")),
) -> KarTrackerSettingsResponse:
    """KarTracker's settings: the karcode formula and who last changed it."""
    return _settings_response(db)


@router.post("/settings/karcode/preview", response_model=KarcodeResponse)
def preview_karcode(
    payload: KarcodePreviewRequest,
    _user: User = Depends(require_screen_permission("kartracker.settings", "view")),
) -> KarcodeResponse:
    """Try a (not yet saved) formula on one kar number; nothing is stored."""
    try:
        code = compute_code(payload.formula, payload.kar)
    except KarcodeError as error:
        raise _karcode_http_error(error) from error
    return KarcodeResponse(kar=payload.kar.strip(), code=code)


@router.put("/settings/karcode", response_model=KarTrackerSettingsResponse)
def update_karcode_formula(
    payload: KarcodeFormulaUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_screen_permission("kartracker.settings", "edit")),
) -> KarTrackerSettingsResponse:
    """Save a new karcode formula after checking it; from then on every code
    on the simulator comes from it. The session user is recorded as author.
    """
    try:
        formula = validate_formula(payload.formula)
    except KarcodeError as error:
        raise _karcode_http_error(error) from error

    # Get-or-create the single row, then store the formula + who/when.
    row = _settings_row(db)
    if row is None:
        row = KarTrackerSettings(id=SETTINGS_ROW_ID, karcode_formula=formula)
        db.add(row)
    row.karcode_formula = formula
    row.karcode_updated_by = user.id
    row.karcode_updated_by_name = user.display_name or user.email
    row.karcode_updated_at = datetime.now(timezone.utc)
    db.commit()
    return _settings_response(db)
