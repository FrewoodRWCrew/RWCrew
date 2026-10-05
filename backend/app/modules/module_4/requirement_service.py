# Reads and writes the kar needs ("Benodigdheden"): what each kar needs per
# season (StockMaster_kar_requirement). This is the single entry point for
# that table, so Altsien Select's future Products wizard step can reuse it
# the same way it reuses module_2/plan_kar_service.py — no separate copy of
# the data in module-8.

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.season import Season
from app.db.models.stockmaster_kar_requirement import StockMasterKarRequirement
from app.db.models.user import User
from app.modules.module_4.stock_service import StockError, get_kar, get_product
from app.modules.module_8.previous_season import previous_season_of


@dataclass
class RequirementLine:
    """One product a kar needs, as sent by the Benodigdheden screen."""

    product_id: int
    quantity: int
    comment: str | None = None


@dataclass
class RequirementChanges:
    """What saving a kar's list would add, change and remove — so the
    router can check the matching create/edit/delete rights first.
    """

    added: list[RequirementLine]
    changed: list[RequirementLine]
    removed: list[StockMasterKarRequirement]


def list_requirements(db: Session, season_id: int, kar_id: int) -> list[StockMasterKarRequirement]:
    """A kar's needs for one season."""
    return list(
        db.scalars(
            select(StockMasterKarRequirement).where(
                StockMasterKarRequirement.season_id == season_id, StockMasterKarRequirement.kar_id == kar_id
            )
        ).all()
    )


def requirements_by_kar(db: Session, season_id: int) -> dict[int, dict[int, int]]:
    """{kar_id: {product_id: quantity}} for every kar with needs in a season."""
    result: dict[int, dict[int, int]] = {}
    rows = db.execute(
        select(
            StockMasterKarRequirement.kar_id, StockMasterKarRequirement.product_id, StockMasterKarRequirement.quantity
        ).where(StockMasterKarRequirement.season_id == season_id)
    ).all()
    for kar_id, product_id, quantity in rows:
        result.setdefault(kar_id, {})[product_id] = quantity
    return result


def needs_per_product(db: Session, season_id: int) -> dict[int, int]:
    """{product_id: total needed over all kars} for one season."""
    rows = db.execute(
        select(StockMasterKarRequirement.product_id, func.sum(StockMasterKarRequirement.quantity))
        .where(StockMasterKarRequirement.season_id == season_id)
        .group_by(StockMasterKarRequirement.product_id)
    ).all()
    return {product_id: int(total) for product_id, total in rows}


def plan_changes(db: Session, season_id: int, kar_id: int, lines: Iterable[RequirementLine]) -> RequirementChanges:
    """Compare the list sent by the screen with what's stored: new products
    are "added", other quantities/comments are "changed", products no longer
    listed are "removed".
    """
    wanted: dict[int, RequirementLine] = {}
    for line in lines:
        if line.quantity < 1:
            raise StockError("invalid_quantity")
        if line.product_id in wanted:
            raise StockError("duplicate_product")
        get_product(db, line.product_id)
        wanted[line.product_id] = line

    existing = {row.product_id: row for row in list_requirements(db, season_id, kar_id)}
    added = [line for product_id, line in wanted.items() if product_id not in existing]
    changed = [
        line
        for product_id, line in wanted.items()
        if product_id in existing
        and (existing[product_id].quantity != line.quantity or (existing[product_id].comment or None) != (line.comment or None))
    ]
    removed = [row for product_id, row in existing.items() if product_id not in wanted]
    return RequirementChanges(added, changed, removed)


def apply_changes(
    db: Session, user: User, season: Season, kar_id: int, changes: RequirementChanges
) -> list[StockMasterKarRequirement]:
    """Store the planned changes under the logged-in user (not committed)."""
    get_kar(db, kar_id)
    now = datetime.now(timezone.utc)
    existing = {row.product_id: row for row in list_requirements(db, season.id, kar_id)}

    for line in changes.added:
        db.add(
            StockMasterKarRequirement(
                season_id=season.id,
                kar_id=kar_id,
                product_id=line.product_id,
                quantity=line.quantity,
                comment=line.comment or None,
                updated_by=user.id,
                updated_by_name=user.display_name,
                updated_at=now,
            )
        )
    for line in changes.changed:
        row = existing[line.product_id]
        row.quantity = line.quantity
        row.comment = line.comment or None
        row.updated_by = user.id
        row.updated_by_name = user.display_name
        row.updated_at = now
    for row in changes.removed:
        db.delete(row)

    db.flush()
    return list_requirements(db, season.id, kar_id)


def previous_season_requirements(
    db: Session, season: Season, kar_id: int
) -> tuple[Season | None, list[StockMasterKarRequirement]]:
    """Last season's needs of the same kar, for "Kopieer van vorig seizoen"
    ("last season" = the season whose name sorts right before this one,
    the same rule as Altsien Select's copy panel).
    """
    previous = previous_season_of(db, season)
    if previous is None:
        return None, []
    return previous, list_requirements(db, previous.id, kar_id)
