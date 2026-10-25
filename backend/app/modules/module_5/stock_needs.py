# What Atelier's stock means (block 3), worked out on the fly — nothing is
# stored here:
#   - the stock overview: per article its sizes with the pieces per status;
#   - "Te bestellen": per article size the highest festival-day need of the
#     season (the size estimate of preparation_service) minus everything the
#     atelier owns (available + to wash + handed out);
#   - the minimum-stock warnings: available below the article size's minimum.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_size import FITS, AtelierSize
from app.db.models.festival import Festival
from app.modules.module_5.preparation_service import build_preparation
from app.modules.module_5.stock_service import AVAILABLE, HANDED_OUT, STATUSES, TO_WASH, all_balances
from app.schemas.atelier import MinStockLine, OrderNeedLine, StockArticleRow, StockSizeRow


def _sizes_in_order(rows: list[AtelierArticleSize], sizes: dict[int, AtelierSize]) -> list[AtelierArticleSize]:
    """An article's sizes grouped by fit, then in the size list's order."""
    return sorted(rows, key=lambda row: (FITS.index(sizes[row.size_id].fit), sizes[row.size_id].sort_order))


def stock_overview(db: Session) -> list[StockArticleRow]:
    """Every article (inactive ones only while they still hold stock) with
    its sizes and the pieces per status."""
    balances = all_balances(db)
    sizes = {size.id: size for size in db.scalars(select(AtelierSize)).all()}
    rows_by_article: dict[int, list[AtelierArticleSize]] = {}
    for row in db.scalars(select(AtelierArticleSize)).all():
        rows_by_article.setdefault(row.article_id, []).append(row)

    result = []
    for article in db.scalars(select(AtelierArticle).order_by(AtelierArticle.name)).all():
        size_rows = [
            StockSizeRow(
                article_size_id=row.id,
                size_id=row.size_id,
                size_name=sizes[row.size_id].name,
                fit=sizes[row.size_id].fit,
                active=row.active,
                min_stock=row.min_stock,
                available=balances.get((row.id, AVAILABLE), 0),
                to_wash=balances.get((row.id, TO_WASH), 0),
                handed_out=balances.get((row.id, HANDED_OUT), 0),
            )
            for row in _sizes_in_order(rows_by_article.get(article.id, []), sizes)
        ]
        holds_stock = any(row.available or row.to_wash or row.handed_out for row in size_rows)
        if not article.active and not holds_stock:
            continue
        result.append(
            StockArticleRow(
                article_id=article.id,
                code=article.code,
                name=article.name,
                active=article.active,
                has_image=article.has_image,
                image_updated_at=article.image_updated_at,
                sizes=size_rows,
            )
        )
    return result


def order_needs(db: Session, season_id: int) -> list[OrderNeedLine]:
    """Te bestellen: per article size the highest estimated need on one
    festival day of the season, minus what the atelier owns. Only lines
    with something to order, by article name and size order."""
    balances = all_balances(db)
    highest: dict[int, tuple[int, str]] = {}  # article size id -> (need, festival name)
    labels: dict[int, tuple[int, str, str, str, str]] = {}  # -> (article id, code, name, size, fit)
    festivals = db.scalars(
        select(Festival)
        .where(Festival.season_id == season_id, Festival.active.is_(True))
        .order_by(Festival.start_date, Festival.name)
    ).all()
    for festival in festivals:
        for need in build_preparation(db, festival).articles:
            for size in need.sizes:
                labels[size.article_size_id] = (need.article_id, need.article_code, need.article_name, size.size_name, size.fit)
                if size.quantity > highest.get(size.article_size_id, (0, ""))[0]:
                    highest[size.article_size_id] = (size.quantity, festival.name)

    sizes = {size.id: size for size in db.scalars(select(AtelierSize)).all()}
    order_of = {
        row.id: (FITS.index(sizes[row.size_id].fit), sizes[row.size_id].sort_order)
        for row in db.scalars(select(AtelierArticleSize)).all()
    }
    lines = []
    for article_size_id, (needed, festival_name) in highest.items():
        owned = sum(balances.get((article_size_id, status), 0) for status in STATUSES)
        if needed <= owned:
            continue
        article_id, code, name, size_name, fit = labels[article_size_id]
        lines.append(
            OrderNeedLine(
                article_id=article_id,
                article_code=code,
                article_name=name,
                article_size_id=article_size_id,
                size_name=size_name,
                fit=fit,
                needed=needed,
                festival_name=festival_name,
                owned=owned,
                to_order=needed - owned,
            )
        )
    return sorted(lines, key=lambda line: (line.article_name.lower(), order_of[line.article_size_id]))


def min_stock_alerts(db: Session) -> list[MinStockLine]:
    """Active article sizes (of active articles) whose available stock is
    below their minimum."""
    balances = all_balances(db)
    sizes = {size.id: size for size in db.scalars(select(AtelierSize)).all()}
    articles = {article.id: article for article in db.scalars(select(AtelierArticle)).all()}
    rows = db.scalars(
        select(AtelierArticleSize).where(AtelierArticleSize.min_stock.is_not(None), AtelierArticleSize.active.is_(True))
    ).all()
    alerts: list[tuple[tuple[int, int], MinStockLine]] = []
    for row in rows:
        article = articles[row.article_id]
        available = balances.get((row.id, AVAILABLE), 0)
        if not article.active or available >= row.min_stock:
            continue
        size = sizes[row.size_id]
        alerts.append((
            (FITS.index(size.fit), size.sort_order),
            MinStockLine(
                article_size_id=row.id,
                article_id=article.id,
                article_name=article.name,
                size_name=sizes[row.size_id].name,
                fit=sizes[row.size_id].fit,
                min_stock=row.min_stock,
                available=available,
            ),
        ))
    # By article name, then the size order within the article.
    return [line for _order, line in sorted(alerts, key=lambda item: (item[1].article_name.lower(), item[0]))]
