# StockMaster's (module-4) RFID endpoints for the RWCrew Pi app: what read
# tags are (resolve), the product list of its pickers, the tags last known in
# a place, "Tags koppelen", bookings with the read tags, and the Tag-historiek.
# Its own APIRouter on the module's /api/modules/module-4 prefix (included in
# app/main.py), next to the website's router.py.
#
# All writes go through tag_service.py / tag_booking.py (which use
# stock_service.py); a StockError becomes HTTP detail "code|param|…",
# translated by the Pi app (and the website for the trace).

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.product import Product
from app.db.models.user import User
from app.modules.module_1.tag_trace import Reader
from app.modules.module_4 import tag_service
from app.modules.module_4.deps import (
    ensure_booking_right,
    ensure_season_editable,
    get_season_or_404,
    require_any_screen_permission,
    require_module_access,
    require_screen_permission,
)
from app.modules.module_4.stock_queries import build_document_responses, build_product_stock
from app.modules.module_4.stock_service import StockError
from app.modules.module_4.tag_booking import ManualLine, MissingLine, TagBookingCommand, post_tag_booking
from app.schemas.stockmaster import (
    StockPlaceTag,
    StockRfidAssignRequest,
    StockRfidEpcsRequest,
    StockRfidProductOption,
    StockRfidResolvedTag,
    StockTagHistoryResponse,
    TagBookingRequest,
    TagBookingResponse,
)
from app.schemas.tagscan import RfidReaderInput

router = APIRouter(prefix="/api/modules/module-4", tags=["StockMaster RFID"])

TAGS_SCREEN = "stockmaster.tags"
TAG_HISTORY_SCREEN = "stockmaster.taghistory"

# Every Pi StockMaster screen reads tags: any of these opens resolve.
require_rfid_view = require_any_screen_permission(
    ("stockmaster.stock", "view"),
    ("stockmaster.kars", "view"),
    ("stockmaster.count", "view"),
    (TAGS_SCREEN, "view"),
)


def _error(db: Session, error: StockError) -> HTTPException:
    """Undo what the refused action wrote; answer "code|param|…"."""
    db.rollback()
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _reader(payload: RfidReaderInput | None) -> Reader | None:
    """The Pi's scanner name + location, noted on the tags it read."""
    return Reader(name=payload.name, location=payload.location) if payload else None


@router.post("/rfid/resolve", response_model=list[StockRfidResolvedTag])
def post_resolve(
    payload: StockRfidEpcsRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_rfid_view),
) -> list[StockRfidResolvedTag]:
    """What each read EPC is: unknown, an Atelier piece, a kar's tag, not
    linked yet, an inactive tag, or a product piece with its last known place."""
    try:
        return [StockRfidResolvedTag(**asdict(tag)) for tag in tag_service.resolve(db, payload.epcs)]
    except StockError as error:
        raise _error(db, error) from error


@router.get("/rfid/products", response_model=list[StockRfidProductOption])
def list_rfid_products(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[StockRfidProductOption]:
    """Every product for the Pi's pickers: tag-managed ones first, then by
    name, with its free stock and how many pieces carry a tag."""
    tagged = tag_service.tagged_counts(db)
    tag_managed = set(db.scalars(select(Product.id).where(Product.is_tag_managed.is_(True))).all())
    options = [
        StockRfidProductOption(
            product_id=row.product_id,
            name=row.name,
            type_name=row.type_name,
            bin_label=row.bin_label,
            is_blocked=row.is_blocked,
            is_consumable=row.is_consumable,
            is_tag_managed=row.product_id in tag_managed,
            stock_return_to=row.stock_return_to,
            free=row.free,
            tagged=tagged.get(row.product_id, 0),
        )
        for row in build_product_stock(db)
    ]
    return sorted(options, key=lambda option: (not option.is_tag_managed, option.name.lower()))


@router.get("/rfid/place-tags", response_model=list[StockPlaceTag])
def list_place_tags(
    kar_id: int | None = None,
    free: bool = False,
    product_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_rfid_view),
) -> list[StockPlaceTag]:
    """The tags last known in one place (a kar, or free stock with
    free=true): the pieces a Pi screen expects to read."""
    tags = tag_service.tags_at(db, kar_id=kar_id, free=free and kar_id is None, product_ids=product_ids)
    return [StockPlaceTag(epc=tag.epc_uid, rfid_tag_id=tag.id, product_id=tag.assigned_product_id) for tag in tags]


@router.post("/rfid/assign", response_model=list[StockRfidResolvedTag])
def post_assign(
    payload: StockRfidAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(TAGS_SCREEN, "create")),
) -> list[StockRfidResolvedTag]:
    """Tags koppelen: the read tags become pieces of this product; gives them
    back as resolved, so the Pi shows the result."""
    try:
        tags = tag_service.assign(
            db, current_user, payload.epcs, payload.product_id, payload.replace, _reader(payload.reader)
        )
        db.commit()
    except StockError as error:
        raise _error(db, error) from error
    return [StockRfidResolvedTag(**asdict(tag)) for tag in tag_service.resolve(db, [tag.epc_uid for tag in tags])]


@router.post("/rfid/bookings", response_model=TagBookingResponse, status_code=status.HTTP_201_CREATED)
def post_tag_booking_endpoint(
    payload: TagBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> TagBookingResponse:
    """One booking made on the Pi with the read tags (and untagged pieces
    added by hand). Same rights and season lock as the website's booking
    panels; always stored under the logged-in user."""
    ensure_booking_right(db, current_user, payload.action)
    season = get_season_or_404(db, payload.season_id)
    ensure_season_editable(db, current_user, season)
    command = TagBookingCommand(
        action=payload.action,
        season=season,
        epcs=payload.epcs,
        lines=[ManualLine(line.product_id, line.quantity, line.destination) for line in payload.lines],
        missing=[MissingLine(line.product_id, line.quantity, line.destination) for line in payload.missing],
        kar_id=payload.kar_id,
        reason_id=payload.reason_id,
        team_id=payload.team_id,
        festival_id=payload.festival_id,
        reference=payload.reference,
        comment=payload.comment,
        reader=_reader(payload.reader),
    )
    try:
        result = post_tag_booking(db, current_user, command)
        db.commit()
    except StockError as error:
        raise _error(db, error) from error
    except IntegrityError as error:
        # Two people booked the very first piece of a product at once.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="concurrent_booking") from error

    documents = build_document_responses(db, [result.document, *result.corrections], with_lines=True)
    return TagBookingResponse(document=documents[0], corrections=documents[1:], pieces=result.pieces, tags=result.tags)


@router.get("/rfid/history", response_model=StockTagHistoryResponse)
def get_tag_history(
    epc: str = Query(..., min_length=1, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(TAG_HISTORY_SCREEN, "view")),
) -> StockTagHistoryResponse:
    """Tag-historiek: the tag now, and every Pi booking that moved it."""
    try:
        return StockTagHistoryResponse(**asdict(tag_service.history(db, epc)))
    except StockError as error:
        raise _error(db, error) from error
