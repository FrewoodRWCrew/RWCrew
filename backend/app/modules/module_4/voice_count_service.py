# Reads and writes StockMaster's voice counts (StockMaster_voice_count +
# its lines): a kar counted by voice on the phone, saved for Ophalen or
# Terugbrengen. This is the single entry point for those two tables. Like
# stock_service it never commits: the router does.
#
# Phase 1 only stores the counts; they don't change stock. Booking a count
# into StockMaster (status "booked" + document_id) is a later phase.

import csv
import io
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import to_belgian
from app.db.models.season import Season
from app.db.models.stockmaster_voice_count import StockMasterVoiceCount
from app.db.models.stockmaster_voice_count_line import StockMasterVoiceCountLine
from app.db.models.user import User
from app.modules.module_4.stock_service import StockError, get_kar, get_product


def lines_of(db: Session, voice_count_ids: list[int]) -> dict[int, list[StockMasterVoiceCountLine]]:
    """{voice_count_id: its lines, by product name} for several counts at once."""
    result: dict[int, list[StockMasterVoiceCountLine]] = {voice_count_id: [] for voice_count_id in voice_count_ids}
    if not voice_count_ids:
        return result
    rows = db.scalars(
        select(StockMasterVoiceCountLine)
        .where(StockMasterVoiceCountLine.voice_count_id.in_(voice_count_ids))
        .order_by(StockMasterVoiceCountLine.product_name)
    ).all()
    for line in rows:
        result[line.voice_count_id].append(line)
    return result


def list_voice_counts(db: Session, season_id: int) -> list[StockMasterVoiceCount]:
    """Every voice count of a season, newest first."""
    return list(
        db.scalars(
            select(StockMasterVoiceCount)
            .where(StockMasterVoiceCount.season_id == season_id)
            .order_by(StockMasterVoiceCount.created_at.desc(), StockMasterVoiceCount.id.desc())
        ).all()
    )


def get_voice_count(db: Session, voice_count_id: int) -> StockMasterVoiceCount:
    """Load one voice count, or refuse with "voice_count_not_found"."""
    voice_count = db.get(StockMasterVoiceCount, voice_count_id)
    if voice_count is None:
        raise StockError("voice_count_not_found", voice_count_id, status_code=404)
    return voice_count


def create_voice_count(
    db: Session,
    user: User,
    season: Season,
    kar_id: int,
    direction: str,
    lines: list[tuple[int, int, str | None]],
) -> StockMasterVoiceCount:
    """Save a voice count of a kar. `lines` = (product_id, quantity,
    spoken_text); the same product twice is added up into one line (its
    spoken texts joined), so the phone may send what was said as it came.
    """
    kar = get_kar(db, kar_id)
    if not lines:
        raise StockError("voice_count_empty")

    # Merge the lines per product, checking every product and quantity.
    merged: dict[int, StockMasterVoiceCountLine] = {}
    for product_id, quantity, spoken_text in lines:
        if quantity < 1:
            raise StockError("invalid_quantity")
        product = get_product(db, product_id)
        spoken = (spoken_text or "").strip() or None
        line = merged.get(product_id)
        if line is None:
            merged[product_id] = StockMasterVoiceCountLine(
                product_id=product.id, product_name=product.name, quantity=quantity, spoken_text=spoken
            )
            continue
        line.quantity += quantity
        if spoken:
            line.spoken_text = f"{line.spoken_text} · {spoken}"[:500] if line.spoken_text else spoken

    voice_count = StockMasterVoiceCount(
        season_id=season.id,
        kar_id=kar.id,
        kar_nummer=kar.kar_nummer,
        direction=direction,
        status="new",
        created_by=user.id,
        created_by_name=user.display_name,
    )
    db.add(voice_count)
    db.flush()
    for line in merged.values():
        line.voice_count_id = voice_count.id
        db.add(line)
    db.flush()
    return voice_count


def cancel_voice_count(db: Session, user: User, voice_count: StockMasterVoiceCount) -> StockMasterVoiceCount:
    """Throw a saved count away (it stays visible as "cancelled"). Only a
    count that is still "new" can be cancelled.
    """
    if voice_count.status != "new":
        raise StockError("voice_count_not_new", voice_count.id)
    voice_count.status = "cancelled"
    voice_count.cancelled_by_name = user.display_name
    voice_count.cancelled_at = datetime.now(timezone.utc)
    db.flush()
    return voice_count


def voice_count_csv(voice_count: StockMasterVoiceCount, lines: list[StockMasterVoiceCountLine]) -> str:
    """The count as a CSV text file (one row per product, ";" separated so
    Excel in Belgium opens it in columns), times in Belgian time.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["kar", "direction", "counted_at", "counted_by", "product_id", "product", "quantity", "spoken_text"])
    counted_at = to_belgian(voice_count.created_at).strftime("%Y-%m-%d %H:%M")
    for line in lines:
        writer.writerow(
            [
                voice_count.kar_nummer,
                voice_count.direction,
                counted_at,
                voice_count.created_by_name or "",
                line.product_id or "",
                line.product_name,
                line.quantity,
                line.spoken_text or "",
            ]
        )
    return buffer.getvalue()
