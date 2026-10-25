# Atelier's (module-5) stock — block 3, the sidebar's "Stock" group: the stock
# overview, the bookings that change it (Ontvangst, Wassen, Afboeken,
# Telling), their history with "Ongedaan maken" and a booking slip PDF, the
# "Te bestellen" list (+PDF) and the minimum-stock warnings. Its own
# APIRouter on the module's /api/modules/module-5 prefix (included in
# app/main.py).
#
# Every change goes through stock_service.py; a StockError becomes HTTP
# detail "code|param|…", translated by the frontend under
# atelier.stock.errors.<code>. The booker is always the session user.

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_size import AtelierSize
from app.db.models.atelier_stock_balance import AtelierStockBalance
from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.atelier_stock_movement import AtelierStockMovement
from app.db.models.season import Season
from app.db.models.user import User
from app.modules.module_5.deps import require_module_access, require_screen_permission, require_view_on_any
from app.modules.module_5.stock_needs import min_stock_alerts, order_needs, stock_overview
from app.modules.module_5.stock_pdfs import build_booking_pdf, build_order_list_pdf
from app.modules.module_5.stock_service import (
    AVAILABLE,
    DOC_TYPES,
    HANDED_OUT,
    TO_WASH,
    CountLine,
    StockError,
    StockLine,
    count_stock,
    receive,
    reverse_document,
    wash,
    write_off,
)
from app.schemas.atelier import (
    CountRequest,
    MinStockLine,
    OrderNeedLine,
    ReceiptRequest,
    ReverseRequest,
    StockArticleRow,
    StockDocumentResponse,
    StockMovementResponse,
    StockTotalsResponse,
    WashRequest,
    WriteOffRequest,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

STOCK_SCREEN = "atelier.stock"
RECEIPT_SCREEN = "atelier.receipt"
WASH_SCREEN = "atelier.wash"
WRITE_OFF_SCREEN = "atelier.writeoff"
COUNT_SCREEN = "atelier.count"
BOOKINGS_SCREEN = "atelier.bookings"
ORDER_NEEDS_SCREEN = "atelier.orderneeds"
KPI_SCREEN = "atelier.kpi"

Locale = Literal["nl", "en"]


def _pdf_response(content: bytes, filename: str) -> Response:
    """A PDF opened inline in a new browser tab."""
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace('"', "_")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"},
    )


def _stock_error(error: StockError) -> HTTPException:
    """A refused booking as an HTTP error with detail "code|param|…"."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _document_response(db: Session, document: AtelierStockDocument, *, with_lines: bool) -> StockDocumentResponse:
    """A booking for the screens, optionally with its lines."""
    movements = db.scalars(
        select(AtelierStockMovement).where(AtelierStockMovement.document_id == document.id).order_by(AtelierStockMovement.id)
    ).all()
    reversal_of = db.get(AtelierStockDocument, document.reversal_of_id) if document.reversal_of_id else None
    reversed_by = db.scalar(select(AtelierStockDocument).where(AtelierStockDocument.reversal_of_id == document.id))
    lines: list[StockMovementResponse] = []
    if with_lines:
        for move in movements:
            row = db.get(AtelierArticleSize, move.article_size_id)
            article = db.get(AtelierArticle, row.article_id)
            size = db.get(AtelierSize, row.size_id)
            lines.append(
                StockMovementResponse(
                    article_size_id=row.id,
                    article_id=article.id,
                    article_name=article.name,
                    size_name=size.name,
                    fit=size.fit,
                    from_status=move.from_status,
                    to_status=move.to_status,
                    quantity=move.quantity,
                )
            )
    return StockDocumentResponse(
        id=document.id,
        doc_number=document.doc_number,
        doc_type=document.doc_type,
        reference=document.reference,
        reason=document.reason,
        note=document.note,
        status=document.status,
        reversal_of_number=reversal_of.doc_number if reversal_of else None,
        reversed_by_number=reversed_by.doc_number if reversed_by else None,
        created_by_name=document.created_by_name,
        created_at=document.created_at,
        total_quantity=sum(move.quantity for move in movements),
        movements=lines,
    )


def _get_document_or_404(db: Session, document_id: int) -> AtelierStockDocument:
    """Load one booking or answer 404."""
    document = db.get(AtelierStockDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return document


# --- Overview and warnings ------------------------------------------------------


@router.get("/stock", response_model=list[StockArticleRow])
def get_stock(
    db: Session = Depends(get_db),
    _user: User = Depends(
        require_view_on_any(STOCK_SCREEN, RECEIPT_SCREEN, WASH_SCREEN, WRITE_OFF_SCREEN, COUNT_SCREEN)
    ),
) -> list[StockArticleRow]:
    """Every article with its sizes and the pieces per status — the Stock
    screen, and the pickers of the booking screens."""
    return stock_overview(db)


@router.get("/stock/min-stock", response_model=list[MinStockLine])
def get_min_stock(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[MinStockLine]:
    """Article sizes below their minimum stock — the orange banner on every
    Atelier screen, so plain module access."""
    return min_stock_alerts(db)


# --- Bookings ----------------------------------------------------------------------


@router.post("/stock/receipt", response_model=StockDocumentResponse, status_code=status.HTTP_201_CREATED)
def book_receipt(
    payload: ReceiptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(RECEIPT_SCREEN, "create")),
) -> StockDocumentResponse:
    """Ontvangst: received pieces become available."""
    try:
        document = receive(
            db,
            current_user,
            [StockLine(line.article_size_id, line.quantity) for line in payload.lines],
            reference=payload.reference,
            note=payload.note,
        )
    except StockError as error:
        db.rollback()
        raise _stock_error(error) from error
    db.commit()
    return _document_response(db, document, with_lines=True)


@router.post("/stock/wash", response_model=StockDocumentResponse, status_code=status.HTTP_201_CREATED)
def book_wash(
    payload: WashRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WASH_SCREEN, "create")),
) -> StockDocumentResponse:
    """Gewassen: pieces to wash become available."""
    try:
        document = wash(
            db, current_user, [StockLine(line.article_size_id, line.quantity) for line in payload.lines], note=payload.note
        )
    except StockError as error:
        db.rollback()
        raise _stock_error(error) from error
    db.commit()
    return _document_response(db, document, with_lines=True)


@router.post("/stock/write-off", response_model=StockDocumentResponse, status_code=status.HTTP_201_CREATED)
def book_write_off(
    payload: WriteOffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(WRITE_OFF_SCREEN, "create")),
) -> StockDocumentResponse:
    """Afboeken: pieces leave the store, with a reason."""
    try:
        document = write_off(
            db,
            current_user,
            [StockLine(line.article_size_id, line.quantity, line.from_status) for line in payload.lines],
            reason=payload.reason,
            note=payload.note,
        )
    except StockError as error:
        db.rollback()
        raise _stock_error(error) from error
    db.commit()
    return _document_response(db, document, with_lines=True)


@router.post("/stock/count", response_model=StockDocumentResponse, status_code=status.HTTP_201_CREATED)
def book_count(
    payload: CountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(COUNT_SCREEN, "create")),
) -> StockDocumentResponse:
    """Telling: only the differences with the booked stock are booked."""
    try:
        document = count_stock(
            db,
            current_user,
            [CountLine(line.article_size_id, line.status, line.counted) for line in payload.lines],
            note=payload.note,
        )
    except StockError as error:
        db.rollback()
        raise _stock_error(error) from error
    db.commit()
    return _document_response(db, document, with_lines=True)


# --- History -------------------------------------------------------------------------


@router.get("/stock/documents", response_model=list[StockDocumentResponse])
def list_documents(
    doc_type: str | None = Query(default=None),
    article_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(BOOKINGS_SCREEN, "view")),
) -> list[StockDocumentResponse]:
    """The bookings, newest first (without their lines), optionally of one
    type or touching one article."""
    query = select(AtelierStockDocument).order_by(AtelierStockDocument.id.desc()).limit(limit)
    if doc_type in DOC_TYPES:
        query = query.where(AtelierStockDocument.doc_type == doc_type)
    if article_id is not None:
        query = query.where(
            AtelierStockDocument.id.in_(
                select(AtelierStockMovement.document_id)
                .join(AtelierArticleSize, AtelierArticleSize.id == AtelierStockMovement.article_size_id)
                .where(AtelierArticleSize.article_id == article_id)
            )
        )
    return [_document_response(db, document, with_lines=False) for document in db.scalars(query).all()]


@router.get("/stock/documents/{document_id}", response_model=StockDocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(BOOKINGS_SCREEN, "view")),
) -> StockDocumentResponse:
    """One booking with its lines."""
    return _document_response(db, _get_document_or_404(db, document_id), with_lines=True)


@router.post("/stock/documents/{document_id}/reverse", response_model=StockDocumentResponse)
def reverse(
    document_id: int,
    payload: ReverseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(BOOKINGS_SCREEN, "edit")),
) -> StockDocumentResponse:
    """Ongedaan maken: book the opposite; returns the reversal."""
    document = _get_document_or_404(db, document_id)
    try:
        reversal = reverse_document(db, current_user, document, note=payload.note)
    except StockError as error:
        db.rollback()
        raise _stock_error(error) from error
    db.commit()
    return _document_response(db, reversal, with_lines=True)


@router.get("/stock/documents/{document_id}/pdf")
def get_document_pdf(
    document_id: int,
    locale: Locale = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(BOOKINGS_SCREEN, "view")),
) -> Response:
    """The booking slip of one booking."""
    document = _document_response(db, _get_document_or_404(db, document_id), with_lines=True)
    return _pdf_response(build_booking_pdf(document, locale, current_user.display_name), f"Boekingsbon {document.doc_number}.pdf")


# --- Te bestellen -----------------------------------------------------------------------


def _get_season_or_404(db: Session, season_id: int) -> Season:
    """Load one season or answer 404."""
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    return season


@router.get("/stock/order-needs", response_model=list[OrderNeedLine])
def get_order_needs(
    season_id: int = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ORDER_NEEDS_SCREEN, "view")),
) -> list[OrderNeedLine]:
    """What to order: the season's highest day need per size minus what's owned."""
    _get_season_or_404(db, season_id)
    return order_needs(db, season_id)


@router.get("/stock/order-needs/pdf")
def get_order_needs_pdf(
    season_id: int = Query(...),
    locale: Locale = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(ORDER_NEEDS_SCREEN, "view")),
) -> Response:
    """The Te bestellen list as a PDF."""
    season = _get_season_or_404(db, season_id)
    content = build_order_list_pdf(order_needs(db, season_id), season.name, locale, current_user.display_name)
    return _pdf_response(content, f"Bestellijst kledij {season.name}.pdf")


# --- KPI --------------------------------------------------------------------------------


@router.get("/stock/totals", response_model=StockTotalsResponse)
def get_stock_totals(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KPI_SCREEN, "view")),
) -> StockTotalsResponse:
    """The KPI page's stock tiles: pieces per status, and the number of
    article sizes below their minimum."""
    totals = dict(
        db.execute(
            select(AtelierStockBalance.status, func.sum(AtelierStockBalance.quantity)).group_by(AtelierStockBalance.status)
        ).all()
    )
    return StockTotalsResponse(
        available=int(totals.get(AVAILABLE, 0)),
        to_wash=int(totals.get(TO_WASH, 0)),
        handed_out=int(totals.get(HANDED_OUT, 0)),
        below_min_stock=len(min_stock_alerts(db)),
    )
