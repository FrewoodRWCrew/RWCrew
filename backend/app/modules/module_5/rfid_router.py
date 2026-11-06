# Atelier's (module-5) RFID pieces, for the Raspberry Pi app: what read tags
# are (resolve, used by Ophalen and Terugbrengen on the Pi) and "Tags
# koppelen" (link read tags to an article size), and the Tag-historiek (the trace
# of a piece by its EPC, on the website). Its own APIRouter on the
# module's /api/modules/module-5 prefix (included in app/main.py). Bookings
# themselves go through the desk's existing endpoints (desk_router.py).
#
# All writes go through rfid_service.py; a StockError becomes HTTP detail
# "code|param|…", translated by the Pi app.

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_size import FITS, AtelierSize
from app.db.models.rfid_tag import RfidTag
from app.db.models.user import User
from app.modules.module_5.deps import require_screen_permission, require_view_on_any
from app.modules.module_5.rfid_service import Reader, assign, history, resolve
from app.modules.module_5.stock_service import StockError
from app.schemas.atelier import (
    RfidArticleOption,
    RfidArticleSizeOption,
    RfidAssignRequest,
    RfidEpcsRequest,
    RfidResolvedTag,
    TagHistoryResponse,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

DESK_SCREEN = "atelier.desk"
TAGS_SCREEN = "atelier.tags"
TAG_HISTORY_SCREEN = "atelier.taghistory"


def _error(error: StockError) -> HTTPException:
    """A refused action as an HTTP error with detail "code|param|…"."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.post("/rfid/resolve", response_model=list[RfidResolvedTag])
def post_resolve(
    payload: RfidEpcsRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_view_on_any(DESK_SCREEN, TAGS_SCREEN)),
) -> list[RfidResolvedTag]:
    """What each read EPC is: unknown, not an Atelier piece, an inactive
    piece, or a piece (with who has it, when it is out)."""
    try:
        return [RfidResolvedTag(**vars(tag)) for tag in resolve(db, payload.epcs)]
    except StockError as error:
        raise _error(error) from error


@router.get("/rfid/articles", response_model=list[RfidArticleOption])
def list_rfid_articles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(TAGS_SCREEN, "view")),
) -> list[RfidArticleOption]:
    """Tags koppelen's choice: every active article (tag-managed ones first,
    then by name) with its active sizes and how many pieces carry a tag."""
    sizes = {size.id: size for size in db.scalars(select(AtelierSize)).all()}
    tagged = dict(
        db.execute(
            select(RfidTag.atelier_article_size_id, func.count())
            .where(RfidTag.atelier_article_size_id.is_not(None))
            .group_by(RfidTag.atelier_article_size_id)
        ).all()
    )
    result = []
    for article in db.scalars(select(AtelierArticle).where(AtelierArticle.active.is_(True))).all():
        rows = [
            row
            for row in db.scalars(select(AtelierArticleSize).where(AtelierArticleSize.article_id == article.id)).all()
            if row.active
        ]
        # The size list's order: fit, then the size's own order.
        rows.sort(key=lambda row: (FITS.index(sizes[row.size_id].fit), sizes[row.size_id].sort_order))
        result.append(
            RfidArticleOption(
                article_id=article.id,
                code=article.code,
                name=article.name,
                is_tag_managed=article.is_tag_managed,
                sizes=[
                    RfidArticleSizeOption(
                        article_size_id=row.id,
                        size_name=sizes[row.size_id].name,
                        fit=sizes[row.size_id].fit,
                        tagged=tagged.get(row.id, 0),
                    )
                    for row in rows
                ],
            )
        )
    return sorted(result, key=lambda option: (not option.is_tag_managed, option.name.lower()))


@router.post("/rfid/assign", response_model=list[RfidResolvedTag])
def post_assign(
    payload: RfidAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(TAGS_SCREEN, "create")),
) -> list[RfidResolvedTag]:
    """Tags koppelen: the read tags become pieces of this article size; gives
    them back as resolved, so the Pi shows the result."""
    try:
        reader = Reader(name=payload.reader.name, location=payload.reader.location) if payload.reader else None
        tags = assign(db, current_user, payload.epcs, payload.article_size_id, payload.replace, reader)
        db.commit()
    except StockError as error:
        db.rollback()
        raise _error(error) from error
    return [RfidResolvedTag(**vars(tag)) for tag in resolve(db, [tag.epc_uid for tag in tags])]


@router.get("/rfid/history", response_model=TagHistoryResponse)
def get_tag_history(
    epc: str = Query(..., min_length=1, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(TAG_HISTORY_SCREEN, "view")),
) -> TagHistoryResponse:
    """Tag-historiek: the tag as TagScan's register knows it now, and every
    hand-out and return of a piece with this EPC (newest first)."""
    try:
        return TagHistoryResponse(**asdict(history(db, epc)))
    except StockError as error:
        raise _error(error) from error
