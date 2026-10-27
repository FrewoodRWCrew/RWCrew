# Atelier's wash statistics for the KPI page: how many pieces were washed per
# day, grouped per festival, with the season total. Nothing is stored for it:
# it's worked out from the posted "Gewassen" bookings (a wash that was undone
# has status "reversed" and is left out, as is its reversal document).
#
# A wash has no festival on it, so it's linked by its Belgian booking date:
#   - the season is the one of the latest (active) festival that started on or
#     before that day — so washing done in the days after a festival still
#     counts for its season; washes before any festival are in no season;
#   - the festival is the one of that season running on that day
#     (start_date ≤ day ≤ end_date, the earliest one if two overlap), else
#     the day is in the "no festival" group (festival_id None).

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timezone import to_belgian
from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.atelier_stock_movement import AtelierStockMovement
from app.db.models.festival import Festival
from app.modules.module_5.stock_service import POSTED, WASHED


@dataclass
class WashDay:
    """The pieces washed on one day."""

    day: date
    pieces: int


@dataclass
class WashFestival:
    """One festival's washed days (festival None = days outside every festival)."""

    festival_id: int | None
    festival_name: str | None
    pieces: int = 0
    days: list[WashDay] = field(default_factory=list)


@dataclass
class WashStats:
    """A season's wash statistics."""

    total: int
    festivals: list[WashFestival]


def pieces_washed_per_day(db: Session) -> dict[date, int]:
    """Every posted wash's pieces, added up per Belgian booking date."""
    rows = db.execute(
        select(AtelierStockDocument.created_at, func.sum(AtelierStockMovement.quantity))
        .join(AtelierStockMovement, AtelierStockMovement.document_id == AtelierStockDocument.id)
        .where(AtelierStockDocument.doc_type == WASHED, AtelierStockDocument.status == POSTED)
        .group_by(AtelierStockDocument.id, AtelierStockDocument.created_at)
    ).all()
    per_day: dict[date, int] = defaultdict(int)
    for created_at, pieces in rows:
        per_day[to_belgian(created_at).date()] += int(pieces or 0)
    return per_day


def wash_stats(db: Session, season_id: int) -> WashStats:
    """The season's washed pieces per day, grouped per festival (in date
    order, the "no festival" days last), and their total."""
    # Every active festival, oldest first: needed across seasons to tell
    # which season a day after a festival belongs to.
    festivals = db.scalars(
        select(Festival).where(Festival.active.is_(True)).order_by(Festival.start_date, Festival.name)
    ).all()

    groups: dict[int | None, WashFestival] = {}
    for day, pieces in sorted(pieces_washed_per_day(db).items()):
        started = [festival for festival in festivals if festival.start_date <= day]
        # Before any festival, or after a festival of another season: not in this view.
        if not started or started[-1].season_id != season_id:
            continue
        running = next(
            (f for f in started if f.season_id == season_id and f.start_date <= day <= f.end_date), None
        )
        key = running.id if running else None
        group = groups.get(key)
        if group is None:
            group = groups[key] = WashFestival(running.id if running else None, running.name if running else None)
        group.days.append(WashDay(day, pieces))
        group.pieces += pieces

    # Festivals in the order of their first washed day, the "no festival" group last.
    ordered = [group for key, group in groups.items() if key is not None]
    if None in groups:
        ordered.append(groups[None])
    return WashStats(total=sum(group.pieces for group in ordered), festivals=ordered)
