"""belgian time for typed-in date-times + tag header scanner backfill

Revision ID: a7d3e9b2c418
Revises: e5a8c3f1d742
Create Date: 2026-10-04 14:00:00.000000

Data only, no schema change.

1. Date-times typed in a form (or imported from Excel) arrive without a
   timezone. Until now the database session ran in UTC, so 09:51 Belgian time
   was stored as 09:51 UTC. The session now runs in Belgian time (see
   app/core/database.py), so these existing values are reinterpreted as the
   Belgian wall-clock time they really were. Automatic timestamps (created_at,
   submitted_at, recorded_at, ...) were always real UTC and are not touched.
   KarTracker_karren.last_recorded_at is mixed: a kar action writes the real
   moment (equal to that kar's latest action), only other values were typed in
   or imported.

2. Tag header rows logged before the header-level scanner columns existed get
   their scanner/mode/action from their own first lines, and the scanner
   snapshot (name, location, technology) from the Scanners master data.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7d3e9b2c418'
down_revision: Union[str, Sequence[str], None] = 'e5a8c3f1d742'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# A kar's last_recorded_at that does NOT come from one of its kar actions.
KAR_TYPED_IN = """
    last_recorded_at IS NOT NULL
    AND last_recorded_at IS DISTINCT FROM (
        SELECT max(a.recorded_at) FROM "KarTracker_kar_actions" a WHERE a.kar_id = "KarTracker_karren".id
    )
"""


def _shift(from_zone: str, to_zone: str) -> None:
    """Read each typed-in value's wall-clock time as `from_zone` and store it
    as that same wall-clock time in `to_zone`."""
    expression = "({col} AT TIME ZONE '%s') AT TIME ZONE '%s'" % (from_zone, to_zone)
    op.execute(
        'UPDATE "InterventionRequests_request" SET preferred_delivery_at = '
        + expression.format(col="preferred_delivery_at")
        + " WHERE preferred_delivery_at IS NOT NULL"
    )
    op.execute(
        'UPDATE "Tagscan_rfid_tag" SET last_read_at = '
        + expression.format(col="last_read_at")
        + " WHERE last_read_at IS NOT NULL"
    )
    op.execute(
        'UPDATE "KarTracker_karren" SET last_recorded_at = '
        + expression.format(col="last_recorded_at")
        + " WHERE "
        + KAR_TYPED_IN
    )


def upgrade() -> None:
    """Upgrade data."""
    # Postgres only: SQLite (tests) builds its tables from the models.
    if op.get_bind().dialect.name != "postgresql":
        return

    _shift("UTC", "Europe/Brussels")

    # Header scanner/mode/action: the first non-empty value among its lines.
    for field in ("scanner", "mode", "action"):
        op.execute(
            f"""
            UPDATE "Tagscan_header_data" h SET {field} = (
                SELECT l.{field} FROM "Tagscan_line_data" l
                WHERE l.header_data_id = h.id AND coalesce(l.{field}, '') <> ''
                ORDER BY l.line_number LIMIT 1
            )
            WHERE coalesce(h.{field}, '') = ''
            """
        )

    # Scanner snapshot from the Scanners master data, matched by name
    # ignoring case and surrounding spaces (like preload_scanner_lookup).
    op.execute(
        """
        UPDATE "Tagscan_header_data" h
        SET scanner_id = s.id, scanner_name = s.scanner, scanner_location = s.location,
            scanner_technology = s.technology
        FROM "Tagscan_scanners" s
        WHERE h.scanner_id IS NULL AND h.scanner IS NOT NULL
          AND lower(trim(s.scanner)) = lower(trim(h.scanner))
        """
    )


def downgrade() -> None:
    """Downgrade data: only the time shift can be undone; the filled-in
    scanner data is correct either way and stays."""
    if op.get_bind().dialect.name != "postgresql":
        return
    _shift("Europe/Brussels", "UTC")
