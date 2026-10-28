# StockMaster's (module-4) voice counts: the phone's "Spraaktelling" (scan a
# kar's QR code, choose Ophalen/Terugbrengen, say what is there, save) and
# the desktop "Spraaktellingen" list. Its own APIRouter on the same
# /api/modules/module-4 prefix (included in app/main.py), like
# product_masterdata_router.py.
#
# Every endpoint is gated by the "stockmaster.voicecount" screen only, so a
# counter needs no other StockMaster rights (its lookups bring the kars and
# products along). Phase 1 only stores the counts; they don't change stock.

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.stockmaster_voice_count import StockMasterVoiceCount
from app.db.models.stockmaster_voice_count_line import StockMasterVoiceCountLine
from app.db.models.user import User
from app.modules.module_4.deps import ensure_season_editable, get_season_or_404, require_screen_permission
from app.modules.module_4.stock_service import StockError
from app.modules.module_4.voice_count_service import (
    cancel_voice_count,
    create_voice_count,
    get_voice_count,
    lines_of,
    list_voice_counts,
    voice_count_csv,
)
from app.schemas.stockmaster import (
    NamedItem,
    VoiceCountCreateRequest,
    VoiceCountKarOption,
    VoiceCountLineResponse,
    VoiceCountLookupsResponse,
    VoiceCountResponse,
)

router = APIRouter(prefix="/api/modules/module-4", tags=["StockMaster"])

VOICE_COUNT_SCREEN = "stockmaster.voicecount"


def _stock_error(db: Session, error: StockError) -> HTTPException:
    """Undo what the failed request already wrote, and answer with the
    broken rule ("code|param|..." — translated by the frontend).
    """
    db.rollback()
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _to_response(voice_count: StockMasterVoiceCount, lines: list[StockMasterVoiceCountLine]) -> VoiceCountResponse:
    """A voice count with its lines and total number of pieces."""
    return VoiceCountResponse(
        id=voice_count.id,
        season_id=voice_count.season_id,
        kar_id=voice_count.kar_id,
        kar_nummer=voice_count.kar_nummer,
        direction=voice_count.direction,
        status=voice_count.status,
        document_id=voice_count.document_id,
        created_by_name=voice_count.created_by_name,
        created_at=voice_count.created_at,
        cancelled_by_name=voice_count.cancelled_by_name,
        cancelled_at=voice_count.cancelled_at,
        total_quantity=sum(line.quantity for line in lines),
        lines=[VoiceCountLineResponse.model_validate(line) for line in lines],
    )


def _load(db: Session, voice_count_id: int) -> StockMasterVoiceCount:
    """Load one voice count, or answer 404."""
    try:
        return get_voice_count(db, voice_count_id)
    except StockError as error:
        raise _stock_error(db, error) from error


@router.get("/voice-count/lookups", response_model=VoiceCountLookupsResponse)
def get_voice_count_lookups(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(VOICE_COUNT_SCREEN, "create")),
) -> VoiceCountLookupsResponse:
    """The kars (recognised from their QR code) and the products the spoken
    words are matched against (blocked products left out).
    """
    kars = db.scalars(select(KarTrackerKar).order_by(KarTrackerKar.kar_nummer)).all()
    products = db.scalars(select(Product).where(Product.is_blocked.is_(False)).order_by(Product.name)).all()
    return VoiceCountLookupsResponse(
        kars=[VoiceCountKarOption(id=kar.id, kar_nummer=kar.kar_nummer) for kar in kars],
        products=[NamedItem(id=product.id, name=product.name) for product in products],
    )


@router.post("/voice-counts", response_model=VoiceCountResponse, status_code=201)
def create_voice_count_endpoint(
    payload: VoiceCountCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(VOICE_COUNT_SCREEN, "create")),
) -> VoiceCountResponse:
    """Save a kar's voice count (the phone's "Opslaan"); counted by the session user."""
    season = get_season_or_404(db, payload.season_id)
    ensure_season_editable(db, current_user, season)
    try:
        voice_count = create_voice_count(
            db,
            current_user,
            season,
            payload.kar_id,
            payload.direction,
            [(line.product_id, line.quantity, line.spoken_text) for line in payload.lines],
        )
    except StockError as error:
        raise _stock_error(db, error) from error
    db.commit()
    return _to_response(voice_count, lines_of(db, [voice_count.id])[voice_count.id])


@router.get("/voice-counts", response_model=list[VoiceCountResponse])
def list_voice_counts_endpoint(
    season_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(VOICE_COUNT_SCREEN, "view")),
) -> list[VoiceCountResponse]:
    """Every voice count of a season, newest first (desktop "Spraaktellingen")."""
    get_season_or_404(db, season_id)
    voice_counts = list_voice_counts(db, season_id)
    lines = lines_of(db, [voice_count.id for voice_count in voice_counts])
    return [_to_response(voice_count, lines[voice_count.id]) for voice_count in voice_counts]


@router.get("/voice-counts/{voice_count_id}", response_model=VoiceCountResponse)
def get_voice_count_endpoint(
    voice_count_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(VOICE_COUNT_SCREEN, "view")),
) -> VoiceCountResponse:
    """One voice count with its lines."""
    voice_count = _load(db, voice_count_id)
    return _to_response(voice_count, lines_of(db, [voice_count.id])[voice_count.id])


@router.post("/voice-counts/{voice_count_id}/cancel", response_model=VoiceCountResponse)
def cancel_voice_count_endpoint(
    voice_count_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(VOICE_COUNT_SCREEN, "edit")),
) -> VoiceCountResponse:
    """Throw a saved count away (only while it is still "new")."""
    voice_count = _load(db, voice_count_id)
    try:
        cancel_voice_count(db, current_user, voice_count)
    except StockError as error:
        raise _stock_error(db, error) from error
    db.commit()
    return _to_response(voice_count, lines_of(db, [voice_count.id])[voice_count.id])


@router.get("/voice-counts/{voice_count_id}/csv")
def download_voice_count_csv(
    voice_count_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(VOICE_COUNT_SCREEN, "view")),
) -> Response:
    """The count as a CSV text file (download)."""
    voice_count = _load(db, voice_count_id)
    content = voice_count_csv(voice_count, lines_of(db, [voice_count.id])[voice_count.id])
    filename = f"Spraaktelling {voice_count.kar_nummer} {voice_count.id}.csv"
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace('"', "_")
    # UTF-8 with a byte-order mark, so Excel shows accents correctly.
    return Response(
        content="﻿" + content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"},
    )
