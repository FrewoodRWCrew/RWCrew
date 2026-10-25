# Atelier's (module-5) master data — the sidebar's "Masterdata" group:
# Artikelen (the clothing catalogue, each article with the sizes it comes
# in and an optional picture), Maten (the size list: name + fit) and the
# bulk XLSX import/export ("Data Upload/Download", which also holds the
# Reservaties and Pakketlijnen tiles). What each team gets is part of its
# reservation per festival (reservation_router.py). Its own
# APIRouter on the module's /api/modules/module-5 prefix (included in
# app/main.py), so router.py keeps only the access-rights screens.
#
# Every endpoint is gated by Atelier's custom roles per screen. The article
# picture's GET lives in router.py (plain module access, so every later
# screen can show it); only changing it needs the Artikelen screen.

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_reservation_line import AtelierReservationLine
from app.db.models.atelier_size import FITS, AtelierSize
from app.db.models.atelier_stock_movement import AtelierStockMovement
from app.db.models.user import User
from app.modules.module_5 import xlsx_imports
from app.modules.module_5.deps import (
    require_module_access,
    require_screen_permission,
    require_view_on_any,
    user_can,
)
from app.schemas.atelier import (
    ArticleRequest,
    ArticleResponse,
    ArticleSizeResponse,
    AtelierImportResponse,
    MasterdataStatsResponse,
    SizeRequest,
    SizeResponse,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

KPI_SCREEN = "atelier.kpi"
ARTICLES_SCREEN = "atelier.articles"
SIZES_SCREEN = "atelier.sizes"
RESERVATIONS_SCREEN = "atelier.reservations"
DATA_UPLOAD_SCREEN = "atelier.dataupload"

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# --- KPI page ---------------------------------------------------------------


@router.get("/masterdata-stats", response_model=MasterdataStatsResponse)
def get_masterdata_stats(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KPI_SCREEN, "view")),
) -> MasterdataStatsResponse:
    """The catalogue counts on the KPI page."""
    articles_active = db.scalar(select(func.count(AtelierArticle.id)).where(AtelierArticle.active.is_(True))) or 0
    articles_total = db.scalar(select(func.count(AtelierArticle.id))) or 0
    # Article sizes that can be handed out: both the size line and its article active.
    article_sizes_active = (
        db.scalar(
            select(func.count(AtelierArticleSize.id))
            .join(AtelierArticle, AtelierArticle.id == AtelierArticleSize.article_id)
            .where(AtelierArticleSize.active.is_(True), AtelierArticle.active.is_(True))
        )
        or 0
    )
    return MasterdataStatsResponse(
        articles_active=articles_active,
        articles_inactive=articles_total - articles_active,
        sizes_active=db.scalar(select(func.count(AtelierSize.id)).where(AtelierSize.active.is_(True))) or 0,
        article_sizes_active=article_sizes_active,
    )


# --- Sizes (Maten) ------------------------------------------------------------


def _sorted_sizes(sizes: list[AtelierSize]) -> list[AtelierSize]:
    """Sizes grouped by fit (Women, Men, Unisex), then in their own order."""
    return sorted(sizes, key=lambda size: (FITS.index(size.fit), size.sort_order, size.name.lower()))


@router.get("/sizes", response_model=list[SizeResponse])
def list_sizes(
    db: Session = Depends(get_db),
    _user: User = Depends(require_view_on_any(SIZES_SCREEN, ARTICLES_SCREEN)),
) -> list[AtelierSize]:
    """Every size, active and inactive (the article form only offers active ones)."""
    return _sorted_sizes(list(db.scalars(select(AtelierSize)).all()))


def _check_size_unique(db: Session, payload: SizeRequest, size_id: int | None = None) -> None:
    """A name may exist once per fit: refuse a second "M · Men"."""
    clash = db.scalar(
        select(AtelierSize).where(
            func.lower(AtelierSize.name) == payload.name.strip().lower(), AtelierSize.fit == payload.fit
        )
    )
    if clash is not None and clash.id != size_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This size already exists for this fit")


@router.post("/sizes", response_model=SizeResponse, status_code=status.HTTP_201_CREATED)
def create_size(
    payload: SizeRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SIZES_SCREEN, "create")),
) -> AtelierSize:
    """Add a size."""
    _check_size_unique(db, payload)
    size = AtelierSize(**{**payload.model_dump(), "name": payload.name.strip()})
    db.add(size)
    db.commit()
    db.refresh(size)
    return size


@router.put("/sizes/{size_id}", response_model=SizeResponse)
def update_size(
    size_id: int,
    payload: SizeRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SIZES_SCREEN, "edit")),
) -> AtelierSize:
    """Change a size (rename, other fit, order, (de)activate)."""
    size = db.get(AtelierSize, size_id)
    if size is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Size not found")
    _check_size_unique(db, payload, size_id)
    for field, value in {**payload.model_dump(), "name": payload.name.strip()}.items():
        setattr(size, field, value)
    db.commit()
    db.refresh(size)
    return size


@router.delete("/sizes/{size_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_size(
    size_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(SIZES_SCREEN, "delete")),
) -> None:
    """Delete a size no article uses; a used one can only be deactivated."""
    size = db.get(AtelierSize, size_id)
    if size is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Size not found")
    used_by = db.scalar(select(func.count(AtelierArticleSize.id)).where(AtelierArticleSize.size_id == size_id))
    if used_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This size is used by {used_by} article(s) and can't be deleted (deactivate it instead)",
        )
    db.delete(size)
    db.commit()


# --- Articles (Artikelen) -------------------------------------------------------


def _article_response(db: Session, article: AtelierArticle) -> ArticleResponse:
    """One article with its sizes, in the size list's order."""
    sizes_by_id = {size.id: size for size in db.scalars(select(AtelierSize)).all()}
    article_sizes = db.scalars(select(AtelierArticleSize).where(AtelierArticleSize.article_id == article.id)).all()
    ordered = sorted(
        article_sizes,
        key=lambda row: (FITS.index(sizes_by_id[row.size_id].fit), sizes_by_id[row.size_id].sort_order),
    )
    return ArticleResponse(
        id=article.id,
        code=article.code,
        name=article.name,
        description=article.description,
        colour=article.colour,
        cost=article.cost,
        is_tag_managed=article.is_tag_managed,
        active=article.active,
        has_image=article.has_image,
        image_updated_at=article.image_updated_at,
        sizes=[ArticleSizeResponse.model_validate(row) for row in ordered],
    )


@router.get("/articles", response_model=list[ArticleResponse])
def list_articles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_view_on_any(ARTICLES_SCREEN, RESERVATIONS_SCREEN)),
) -> list[ArticleResponse]:
    """Every article with its sizes, by name."""
    articles = db.scalars(select(AtelierArticle).order_by(AtelierArticle.name)).all()
    return [_article_response(db, article) for article in articles]


def _has_stock_history(db: Session, article_size_ids: list[int]) -> bool:
    """Whether any of these article sizes was ever booked in stock."""
    if not article_size_ids:
        return False
    return (
        db.scalar(
            select(AtelierStockMovement.id).where(AtelierStockMovement.article_size_id.in_(article_size_ids)).limit(1)
        )
        is not None
    )


def _apply_article(db: Session, article: AtelierArticle, payload: ArticleRequest) -> None:
    """Write the form's fields and its size list onto an article (new or
    existing). Sizes left out are removed; a newly ticked size must exist
    and be active."""
    code = payload.code.strip()
    clash = db.scalar(select(AtelierArticle).where(func.lower(AtelierArticle.code) == code.lower()))
    if clash is not None and clash is not article:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An article with this code already exists")

    size_ids = [line.size_id for line in payload.sizes]
    if len(size_ids) != len(set(size_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A size can only be ticked once")
    # The size split is all-or-nothing: once a share is filled in, the shares
    # of the article's sizes must add up to 100%.
    shares = [line.size_share_pct for line in payload.sizes]
    if any(share is not None for share in shares) and sum(share or 0 for share in shares) != 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The size split must add up to 100%"
        )

    article.code = code
    article.name = payload.name.strip()
    article.description = payload.description or None
    article.colour = (payload.colour or "").strip() or None
    article.cost = payload.cost
    article.is_tag_managed = payload.is_tag_managed
    article.active = payload.active
    if article.id is None:
        db.add(article)
    db.flush()

    existing = {
        row.size_id: row
        for row in db.scalars(select(AtelierArticleSize).where(AtelierArticleSize.article_id == article.id)).all()
    }
    # Sizes no longer ticked are removed — unless they have stock bookings,
    # which must never lose their article size: deactivate those instead.
    for size_id, row in existing.items():
        if size_id not in size_ids:
            if _has_stock_history(db, [row.id]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A size with stock bookings can't be removed from the article (deactivate it instead)",
                )
            db.delete(row)
    for line in payload.sizes:
        row = existing.get(line.size_id)
        if row is None:
            size = db.get(AtelierSize, line.size_id)
            if size is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Size {line.size_id} not found")
            if not size.active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Size "{size.name} · {size.fit}" is inactive and can\'t be added',
                )
            db.add(
                AtelierArticleSize(
                    article_id=article.id,
                    size_id=line.size_id,
                    min_stock=line.min_stock,
                    size_share_pct=line.size_share_pct,
                    active=line.active,
                )
            )
        else:
            row.min_stock = line.min_stock
            row.size_share_pct = line.size_share_pct
            row.active = line.active


@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ARTICLES_SCREEN, "create")),
) -> ArticleResponse:
    """Add an article with its sizes."""
    article = AtelierArticle()
    _apply_article(db, article, payload)
    db.commit()
    db.refresh(article)
    return _article_response(db, article)


@router.put("/articles/{article_id}", response_model=ArticleResponse)
def update_article(
    article_id: int,
    payload: ArticleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ARTICLES_SCREEN, "edit")),
) -> ArticleResponse:
    """Change every field of an article and its size list."""
    article = _get_article_or_404(db, article_id)
    _apply_article(db, article, payload)
    db.commit()
    db.refresh(article)
    return _article_response(db, article)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ARTICLES_SCREEN, "delete")),
) -> None:
    """Delete an article (and its sizes) that no reservation's package uses
    and that never had stock bookings."""
    article = _get_article_or_404(db, article_id)
    size_row_ids = list(
        db.scalars(select(AtelierArticleSize.id).where(AtelierArticleSize.article_id == article_id)).all()
    )
    if _has_stock_history(db, size_row_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This article has stock bookings and can't be deleted (deactivate it instead)",
        )
    used_by = db.scalar(
        select(func.count(AtelierReservationLine.id)).where(AtelierReservationLine.article_id == article_id)
    )
    if used_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This article is in {used_by} reservation package line(s) and can't be deleted (deactivate it instead)",
        )
    db.delete(article)
    db.commit()


# ---- Article picture ---------------------------------------------------------
# One optional picture per article, uploaded separately from the JSON
# create/update above (the screen saves the fields first, then the picture).

ALLOWED_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB — plenty for a photo of a T-shirt.


def _get_article_or_404(db: Session, article_id: int) -> AtelierArticle:
    """Load one article or answer 404."""
    article = db.get(AtelierArticle, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


def _require_image_change(db: Session = Depends(get_db), current_user: User = Depends(require_module_access)) -> User:
    """Changing a picture needs "edit" or "create" on Artikelen — so a role
    that may only add articles can still attach a picture to a new one."""
    if not (user_can(db, current_user, ARTICLES_SCREEN, "edit") or user_can(db, current_user, ARTICLES_SCREEN, "create")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not allowed to edit on {ARTICLES_SCREEN}")
    return current_user


@router.put("/articles/{article_id}/image", response_model=ArticleResponse)
def upload_article_image(
    article_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(_require_image_change),
) -> ArticleResponse:
    """Set or replace an article's picture (PNG, JPEG or WebP, up to 5 MB)."""
    article = _get_article_or_404(db, article_id)
    if image.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be PNG, JPEG or WebP")
    # Read one byte past the limit so an oversized picture is detected
    # without buffering an unbounded upload.
    contents = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be smaller than 5 MB")

    article.image_data = contents
    article.image_content_type = image.content_type
    article.image_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return _article_response(db, article)


@router.delete("/articles/{article_id}/image", response_model=ArticleResponse)
def delete_article_image(
    article_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ARTICLES_SCREEN, "edit")),
) -> ArticleResponse:
    """Remove an article's picture; the article itself stays."""
    article = _get_article_or_404(db, article_id)
    article.image_data = None
    article.image_content_type = None
    article.image_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return _article_response(db, article)


# --- Data Upload/Download: bulk XLSX import/export, one tile per table, all
# gated by the same "atelier.dataupload" screen key (like StockMaster's).


def _xlsx(content: bytes, filename: str) -> Response:
    """An XLSX download response."""
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _register_xlsx_routes(table: xlsx_imports.XlsxTable) -> None:
    """The three endpoints of one table: template, upload and export."""

    @router.get(f"/{table.path}-import/template", name=f"atelier_{table.path}_template")
    def download_template(
        _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
    ) -> Response:
        return _xlsx(table.template(), f"atelier-{table.path}-import-template.xlsx")

    @router.post(f"/{table.path}-import", response_model=AtelierImportResponse, name=f"atelier_{table.path}_import")
    def upload(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "create")),
    ) -> AtelierImportResponse:
        return AtelierImportResponse(results=table.import_rows(db, file.file.read(), current_user))

    @router.get(f"/{table.path}/export", name=f"atelier_{table.path}_export")
    def export(
        db: Session = Depends(get_db),
        _user: User = Depends(require_screen_permission(DATA_UPLOAD_SCREEN, "view")),
    ) -> Response:
        return _xlsx(table.export(db), f"atelier-{table.path}-export.xlsx")


for _table in xlsx_imports.TABLES:
    _register_xlsx_routes(_table)
