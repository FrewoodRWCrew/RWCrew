# Aggregate KPI stats for TagScan's landing dashboard. Kept free of
# FastAPI/routing concerns (mirrors file_browser.py/tag_import.py), so
# it's easy to unit test on its own.
#
# All the simple counts/breakdowns are computed in Python from one full
# fetch of (status, assigned_product_id, date_registered) rather than
# several separate COUNT/WHERE queries — this sidesteps any
# Postgres-vs-SQLite dialect differences around timezone-aware datetime
# comparisons (this repo's tests run against SQLite, production against
# Postgres — see backend/tests/conftest.py). Tag counts for an RFID
# registry are expected to stay small-to-moderate, so one fetch is cheap.
# Only "top products" stays a real SQL aggregate (COUNT + JOIN + GROUP BY
# + ORDER BY + LIMIT) since that's portable across both dialects as-is.

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from app.modules.module_1.file_browser import get_source_root
from app.modules.module_1.tag_header_data import UNREADED_SUBFOLDER
from app.schemas.tagscan import (
    TagDashboardResponse,
    TagStatusBreakdownItem,
    TagTopProductItem,
    TagWeeklyRegistrationItem,
)

STATUS_ORDER = ["active", "inactive", "lost", "damaged", "retired"]
WEEKS_OF_HISTORY = 12


def _week_start(day: date) -> date:
    """The Monday of the ISO week containing "day"."""
    return day - timedelta(days=day.weekday())


def _count_unreaded_files() -> int:
    """How many CSV files are currently sitting in "Unreaded Tags",
    waiting for the "Tag Headerdata" screen's scan to pick them up — the
    same non-recursive, .csv-only filter that scan actually uses.
    """
    unreaded_dir = get_source_root() / UNREADED_SUBFOLDER
    if not unreaded_dir.is_dir():
        return 0
    return sum(1 for entry in unreaded_dir.iterdir() if entry.is_file() and entry.suffix.lower() == ".csv")


def build_dashboard_stats(db: Session) -> TagDashboardResponse:
    rows = db.execute(select(RfidTag.status, RfidTag.assigned_product_id, RfidTag.date_registered)).all()

    total_tags = len(rows)
    unreaded_tags_count = _count_unreaded_files()
    assigned_tags = sum(1 for row in rows if row.assigned_product_id is not None)
    unassigned_tags = total_tags - assigned_tags
    lost_or_damaged_tags = sum(1 for row in rows if row.status in ("lost", "damaged"))

    today = date.today()
    registered_this_month = sum(
        1
        for row in rows
        if row.date_registered is not None
        and row.date_registered.year == today.year
        and row.date_registered.month == today.month
    )

    status_counts = {status: 0 for status in STATUS_ORDER}
    for row in rows:
        if row.status in status_counts:
            status_counts[row.status] += 1
    status_breakdown = [TagStatusBreakdownItem(status=status, count=count) for status, count in status_counts.items()]

    # Weekly registrations, oldest first, always WEEKS_OF_HISTORY entries
    # (zero-filled) so the chart's x-axis never skips a week.
    current_week_start = _week_start(today)
    week_starts = [current_week_start - timedelta(weeks=offset) for offset in range(WEEKS_OF_HISTORY - 1, -1, -1)]
    counts_by_week_start = dict.fromkeys(week_starts, 0)
    for row in rows:
        if row.date_registered is None:
            continue
        registered_date = row.date_registered.date() if isinstance(row.date_registered, datetime) else row.date_registered
        bucket = _week_start(registered_date)
        if bucket in counts_by_week_start:
            counts_by_week_start[bucket] += 1
    registrations_by_week = [
        TagWeeklyRegistrationItem(week_start=week_start, count=counts_by_week_start[week_start])
        for week_start in week_starts
    ]

    top_products_rows = db.execute(
        select(Product.name, func.count(RfidTag.id).label("tag_count"))
        .join(RfidTag, RfidTag.assigned_product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.count(RfidTag.id).desc())
        .limit(5)
    ).all()
    top_products = [TagTopProductItem(product_name=row.name, tag_count=row.tag_count) for row in top_products_rows]

    return TagDashboardResponse(
        total_tags=total_tags,
        unreaded_tags_count=unreaded_tags_count,
        assigned_tags=assigned_tags,
        unassigned_tags=unassigned_tags,
        lost_or_damaged_tags=lost_or_damaged_tags,
        registered_this_month=registered_this_month,
        status_breakdown=status_breakdown,
        registrations_by_week=registrations_by_week,
        top_products=top_products,
    )
