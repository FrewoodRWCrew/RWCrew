# The one time zone this whole application works in: Belgian time
# (Europe/Brussels — winter and summer time are handled automatically).
#
# The database stores every moment as UTC (timestamptz). These helpers turn
# such a moment into Belgian wall-clock time wherever the backend shows it to
# a person itself (PDFs, mails, dashboards grouped per day, file names), so
# nothing ever depends on the server's own clock setting (UTC in Docker).
# Values returned through the API are already in Belgian time because every
# Postgres connection is switched to this zone (see app/core/database.py).

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

# The IANA name of Belgian time — also used by the database session.
BELGIAN_TZ_NAME = "Europe/Brussels"
BELGIAN_TZ = ZoneInfo(BELGIAN_TZ_NAME)


def to_belgian(moment: datetime) -> datetime:
    """The same moment expressed in Belgian time.

    A naive value (SQLite in tests hands timezone-aware columns back without
    a timezone) is a stored UTC moment, so it is tagged as UTC first.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(BELGIAN_TZ)


def belgian_now() -> datetime:
    """The current moment in Belgian time."""
    return datetime.now(BELGIAN_TZ)


def belgian_today() -> date:
    """Today's date in Belgium (not the server's own date)."""
    return belgian_now().date()
