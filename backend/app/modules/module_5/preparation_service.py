# What the atelier has to prepare for a festival (block 2's "Voorbereiden"
# screen and picklist). Nothing is stored: it's worked out from the
# reservations (per team: persons and its package of pieces per person).
# Clothing is returned every evening and each team works every
# festival day, so every day of the festival needs the same pieces.
#
# Sizes are only estimated, on the store totals per article: each size gets
# its share (Atelier_article_size.size_share_pct) of the total, rounded with
# the largest-remainder method so the sizes add up exactly to the total. An
# article whose split isn't complete (not every active size filled in, or
# not adding up to 100%) is split equally. A team's bundle has no sizes:
# those are picked at the counter desk. Each estimated size also carries the
# store's stock of that size (available now, and owned in total), so the
# screen can show shortages.

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_size import FITS, AtelierSize
from app.db.models.festival import Festival
from app.db.models.team import Team
from app.modules.module_5.reservation_service import festival_days, lines_by_reservation, reservations_by_team
from app.modules.module_5.stock_service import AVAILABLE, STATUSES, all_balances
from app.schemas.atelier import (
    ArticleNeedResponse,
    BundleLineResponse,
    FestivalSummaryResponse,
    PreparationResponse,
    SizeEstimateResponse,
    TeamBundleResponse,
)


def festival_summary(festival: Festival) -> FestivalSummaryResponse:
    """A festival with its days, as the screens show it."""
    return FestivalSummaryResponse(
        id=festival.id,
        name=festival.name,
        start_date=festival.start_date,
        end_date=festival.end_date,
        days=festival_days(festival),
    )


def split_by_shares(total: int, weights: list[Decimal]) -> list[int]:
    """Divide `total` pieces over the weights, rounding with the largest-
    remainder method: everyone gets the whole part of their share, and the
    pieces left over go to the largest remainders (first one wins a tie), so
    the result always adds up to `total`."""
    weight_sum = sum(weights)
    if total == 0 or not weights or weight_sum == 0:
        return [0] * len(weights)
    exact = [Decimal(total) * weight / weight_sum for weight in weights]
    result = [int(value) for value in exact]
    leftover = total - sum(result)
    by_remainder = sorted(range(len(weights)), key=lambda index: (-(exact[index] - result[index]), index))
    for index in by_remainder[:leftover]:
        result[index] += 1
    return result


def _size_estimate(
    db: Session,
    article_id: int,
    total: int,
    sizes_by_id: dict[int, AtelierSize],
    balances: dict[tuple[int, str], int],
) -> tuple[list[SizeEstimateResponse], bool]:
    """The estimated pieces per size of one article (next to the store's
    stock of that size), and whether the equal split was used because the
    article's own split isn't complete."""
    rows = [
        row
        for row in db.scalars(select(AtelierArticleSize).where(AtelierArticleSize.article_id == article_id)).all()
        if row.active
    ]
    rows.sort(key=lambda row: (FITS.index(sizes_by_id[row.size_id].fit), sizes_by_id[row.size_id].sort_order))
    if not rows:
        return [], True

    shares = [row.size_share_pct for row in rows]
    complete = all(share is not None for share in shares) and sum(shares) == 100
    weights = shares if complete else [Decimal(1)] * len(rows)
    quantities = split_by_shares(total, weights)
    estimates = [
        SizeEstimateResponse(
            size_id=row.size_id,
            article_size_id=row.id,
            size_name=sizes_by_id[row.size_id].name,
            fit=sizes_by_id[row.size_id].fit,
            quantity=quantity,
            available=balances.get((row.id, AVAILABLE), 0),
            owned=sum(balances.get((row.id, status), 0) for status in STATUSES),
        )
        for row, quantity in zip(rows, quantities)
    ]
    return estimates, not complete


def build_preparation(db: Session, festival: Festival, team_ids: list[int] | None = None) -> PreparationResponse:
    """Per festival day: the store totals per article (with a size
    estimate) and every reserved team's bundle. With `team_ids` (the
    picklist of a few teams), only those teams count."""
    reservations = [
        row
        for row in reservations_by_team(db, festival.id).values()
        if row.persons > 0 and (team_ids is None or row.team_id in team_ids)
    ]
    teams = {team.id: team for team in db.scalars(select(Team)).all()}
    articles = {article.id: article for article in db.scalars(select(AtelierArticle)).all()}
    sizes_by_id = {size.id: size for size in db.scalars(select(AtelierSize)).all()}
    balances = all_balances(db)

    # Each reservation's own package lines.
    packages = lines_by_reservation(db, [reservation.id for reservation in reservations])

    bundles: list[TeamBundleResponse] = []
    totals: dict[int, int] = defaultdict(int)
    teams_without_package: list[str] = []
    for reservation in sorted(reservations, key=lambda row: teams[row.team_id].name.lower()):
        team = teams[reservation.team_id]
        lines = packages.get(reservation.id, [])
        if not lines:
            teams_without_package.append(team.name)
            continue
        bundle_lines = []
        for line in sorted(lines, key=lambda item: articles[item.article_id].name.lower()):
            quantity = reservation.persons * line.quantity_per_person
            totals[line.article_id] += quantity
            bundle_lines.append(
                BundleLineResponse(article_id=line.article_id, article_name=articles[line.article_id].name, quantity=quantity)
            )
        bundles.append(
            TeamBundleResponse(team_id=team.id, team_name=team.name, persons=reservation.persons, lines=bundle_lines)
        )

    needs = []
    for article_id in sorted(totals, key=lambda item: articles[item].name.lower()):
        estimates, equal_split = _size_estimate(db, article_id, totals[article_id], sizes_by_id, balances)
        needs.append(
            ArticleNeedResponse(
                article_id=article_id,
                article_code=articles[article_id].code,
                article_name=articles[article_id].name,
                quantity=totals[article_id],
                sizes=estimates,
                equal_split=equal_split,
            )
        )

    return PreparationResponse(
        festival=festival_summary(festival),
        persons_per_day=sum(bundle.persons for bundle in bundles),
        pieces_per_day=sum(totals.values()),
        articles=needs,
        bundles=bundles,
        teams_without_package=teams_without_package,
    )
