# The public, no-login side of StockMaster's "Kar inventaris": a team scans
# the QR code on its karblad, picks the "Kar inventaris" tile on the public kar
# page, types the kar's lock code and counts what is in the kar.
#
# Like module_3/public_router.py, nothing here uses get_current_user or any
# module right: the lock code (only the team knows it) is the key. A correct
# code gives a short-lived token for that one kar (header X-Kar-Inventory-Token,
# or ?token= for product pictures in <img>); the code is never sent again.
# Guessing is slowed down per IP and per kar (4-digit codes). Rules live in
# kar_inventory_service.py; nothing here changes stock.

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.team import Team
from app.modules.module_4.kar_inventory_service import (
    HISTORY_LIMIT,
    TOKEN_LIFETIME,
    code_matches,
    create_inventory,
    create_token,
    expected_contents,
    find_kar,
    kar_from_token,
    list_inventories,
    normalize_kar_nummer,
    products_by_id,
    search_products,
    season_name,
    season_of,
    to_responses,
)
from app.modules.module_4.stock_service import StockError
from app.schemas.stockmaster import (
    KarInventoryContextResponse,
    KarInventoryCreateRequest,
    KarInventoryProductLine,
    KarInventoryProductOption,
    KarInventoryResponse,
    KarInventoryUnlockRequest,
    KarInventoryUnlockResponse,
)
from app.shared.rate_limit import SlidingWindowLimiter, client_ip

router = APIRouter(prefix="/api/public/stockmaster/kar-inventory", tags=["StockMaster (Public kar inventory)"])

# Code tries per IP per minute, and wrong codes per kar before it is locked for 15 minutes.
UNLOCK_TRIES_PER_IP = 10
WRONG_CODES_PER_KAR = 5
KAR_LOCK_SECONDS = 15 * 60
_unlock_ip_limiter = SlidingWindowLimiter(UNLOCK_TRIES_PER_IP, 60.0)
_wrong_code_limiter = SlidingWindowLimiter(WRONG_CODES_PER_KAR, KAR_LOCK_SECONDS)
# Saves and product searches per IP per minute.
_save_limiter = SlidingWindowLimiter(10, 60.0)
_search_limiter = SlidingWindowLimiter(60, 60.0)


def reset_limiters() -> None:
    """Forget every counted try (tests)."""
    for limiter in (_unlock_ip_limiter, _wrong_code_limiter, _save_limiter, _search_limiter):
        limiter.reset()


def _error(db: Session, error: StockError) -> HTTPException:
    """Undo what the request wrote and answer "code|param" (translated by the page)."""
    db.rollback()
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _too_many(seconds: int) -> HTTPException:
    """429 with how many seconds the page should wait."""
    return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"too_many_tries|{seconds}")


def _kar_of_request(
    db: Session = Depends(get_db),
    token: str | None = Header(default=None, alias="X-Kar-Inventory-Token"),
) -> KarTrackerKar:
    """The kar opened by the request's token (401 without a valid one)."""
    try:
        return kar_from_token(db, token)
    except StockError as error:
        raise _error(db, error) from error


@router.post("/unlock", response_model=KarInventoryUnlockResponse)
def unlock_kar(payload: KarInventoryUnlockRequest, request: Request, db: Session = Depends(get_db)) -> KarInventoryUnlockResponse:
    """Check the lock code of the kar on the QR code. An unknown kar and a
    wrong code give the same answer, so kar numbers can't be probed."""
    if not _unlock_ip_limiter.hit(client_ip(request)):
        raise _too_many(_unlock_ip_limiter.seconds_left(client_ip(request)))
    kar_key = normalize_kar_nummer(payload.kar_nummer)
    if _wrong_code_limiter.is_blocked(kar_key):
        raise _too_many(_wrong_code_limiter.seconds_left(kar_key))

    kar = find_kar(db, payload.kar_nummer)
    # A kar without a lock code can never be opened: say so, the team must contact StockMaster.
    if kar is not None and not (kar.kar_code or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_code")
    if kar is None or not code_matches(kar, payload.code):
        _wrong_code_limiter.hit(kar_key)
        if _wrong_code_limiter.is_blocked(kar_key):
            raise _too_many(_wrong_code_limiter.seconds_left(kar_key))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wrong_code")

    _wrong_code_limiter.clear(kar_key)
    return KarInventoryUnlockResponse(
        token=create_token(kar), kar_nummer=kar.kar_nummer, expires_in=int(TOKEN_LIFETIME.total_seconds())
    )


@router.get("", response_model=KarInventoryContextResponse)
def get_kar_inventory_context(
    db: Session = Depends(get_db), kar: KarTrackerKar = Depends(_kar_of_request)
) -> KarInventoryContextResponse:
    """The opened kar: what should be in it, and its earlier inventories."""
    expectation = expected_contents(db, kar)
    products = products_by_id(db, set(expectation.quantities))
    lines = sorted(
        (
            KarInventoryProductLine(
                product_id=product_id,
                name=products[product_id].name if product_id in products else f"#{product_id}",
                has_image=bool(products.get(product_id) and products[product_id].image_content_type),
                expected=quantity,
            )
            for product_id, quantity in expectation.quantities.items()
        ),
        key=lambda line: line.name.lower(),
    )
    team = db.get(Team, kar.team_id) if kar.team_id else None
    return KarInventoryContextResponse(
        kar_nummer=kar.kar_nummer,
        team_name=team.name if team else None,
        season_name=season_name(db, season_of(db, expectation)),
        kar_is_out=expectation.trip is not None,
        dispatched_at=expectation.trip.dispatched_at if expectation.trip else None,
        lines=lines,
        history=to_responses(db, list_inventories(db, kar_id=kar.id, limit=HISTORY_LIMIT)),
    )


@router.get("/products", response_model=list[KarInventoryProductOption])
def search_kar_inventory_products(
    request: Request,
    q: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _kar: KarTrackerKar = Depends(_kar_of_request),
) -> list[KarInventoryProductOption]:
    """Products to add as an extra line: every unblocked one, or those whose
    name contains `q`."""
    _search_limiter.enforce(request)
    return [
        KarInventoryProductOption(id=product.id, name=product.name, has_image=bool(product.image_content_type))
        for product in search_products(db, q)
    ]


@router.get("/products/{product_id}/image")
def get_kar_inventory_product_image(
    product_id: int,
    token: str = Query(default=""),
    db: Session = Depends(get_db),
) -> Response:
    """A product's picture for the cards (the token comes as ?token= because an
    <img> can't send headers)."""
    try:
        kar_from_token(db, token)
    except StockError as error:
        raise _error(db, error) from error
    product = db.get(Product, product_id)
    if product is None or product.image_data is None or product.image_content_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product has no image")
    return Response(
        content=product.image_data,
        media_type=product.image_content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.post("", response_model=KarInventoryResponse, status_code=status.HTTP_201_CREATED)
def save_kar_inventory(
    payload: KarInventoryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    kar: KarTrackerKar = Depends(_kar_of_request),
) -> KarInventoryResponse:
    """Store the team's count (a new log line; never changes stock)."""
    _save_limiter.enforce(request)
    try:
        inventory = create_inventory(db, kar, payload, client_ip(request))
    except StockError as error:
        raise _error(db, error) from error
    db.commit()
    return to_responses(db, [inventory])[0]
