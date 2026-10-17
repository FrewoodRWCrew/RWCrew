# Reads and writes a kar's manual requests (StockMaster_kar_manual_request):
# products added with "Manueel product toevoegen" on Kar laden, per season and
# kar, on top of the kar needs. This is the single entry point for that table.
# Like stock_service it never commits: the router does.

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.season import Season
from app.db.models.stockmaster_kar_manual_request import StockMasterKarManualRequest
from app.db.models.user import User
from app.modules.module_4.stock_service import StockError, get_kar, get_product


def list_manual_requests(db: Session, season_id: int, kar_id: int) -> list[StockMasterKarManualRequest]:
    """A kar's manual requests for one season."""
    return list(
        db.scalars(
            select(StockMasterKarManualRequest).where(
                StockMasterKarManualRequest.season_id == season_id, StockMasterKarManualRequest.kar_id == kar_id
            )
        ).all()
    )


def manual_requests_by_kar(db: Session, season_id: int) -> dict[int, dict[int, int]]:
    """{kar_id: {product_id: quantity}} of every kar's manual requests in a season."""
    result: dict[int, dict[int, int]] = {}
    rows = db.execute(
        select(
            StockMasterKarManualRequest.kar_id,
            StockMasterKarManualRequest.product_id,
            StockMasterKarManualRequest.quantity,
        ).where(StockMasterKarManualRequest.season_id == season_id)
    ).all()
    for kar_id, product_id, quantity in rows:
        result.setdefault(kar_id, {})[product_id] = quantity
    return result


def add_manual_request(
    db: Session, user: User, season: Season, kar_id: int, product_id: int, quantity: int
) -> StockMasterKarManualRequest:
    """Ask for `quantity` more pieces of a product for a kar: added to the
    product's existing manual request, or a new one. A blocked product can't
    be asked for (it couldn't be loaded either).
    """
    get_kar(db, kar_id)
    product = get_product(db, product_id)
    if product.is_blocked:
        raise StockError("product_blocked", product.name)

    request = db.scalar(
        select(StockMasterKarManualRequest).where(
            StockMasterKarManualRequest.season_id == season.id,
            StockMasterKarManualRequest.kar_id == kar_id,
            StockMasterKarManualRequest.product_id == product_id,
        )
    )
    now = datetime.now(timezone.utc)
    if request is None:
        request = StockMasterKarManualRequest(
            season_id=season.id,
            kar_id=kar_id,
            product_id=product_id,
            quantity=quantity,
            created_by=user.id,
            created_by_name=user.display_name,
            created_at=now,
            updated_at=now,
        )
        db.add(request)
    else:
        request.quantity += quantity
        request.updated_at = now
    db.flush()
    return request


def get_manual_request(db: Session, kar_id: int, request_id: int) -> StockMasterKarManualRequest:
    """One manual request of a kar, or refuse."""
    request = db.get(StockMasterKarManualRequest, request_id)
    if request is None or request.kar_id != kar_id:
        raise StockError("manual_request_not_found", request_id, status_code=404)
    return request


def delete_manual_request(db: Session, request: StockMasterKarManualRequest) -> None:
    """Remove one manual request of a kar (its Manueel row on Kar laden)."""
    db.delete(request)
    db.flush()
