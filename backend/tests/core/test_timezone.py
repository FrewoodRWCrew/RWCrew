# Tests for the Belgian-time helpers every PDF, mail and dashboard uses
# (app/core/timezone.py): summer and winter time, and naive values (how
# SQLite in tests returns stored UTC moments).

from datetime import date, datetime, timezone

from app.core.timezone import to_belgian


def test_summer_time_is_utc_plus_two_and_can_change_the_date() -> None:
    belgian = to_belgian(datetime(2026, 7, 1, 22, 30, tzinfo=timezone.utc))
    assert belgian.strftime("%Y-%m-%d %H:%M") == "2026-07-02 00:30"
    assert belgian.date() == date(2026, 7, 2)


def test_winter_time_is_utc_plus_one() -> None:
    assert to_belgian(datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)).strftime("%H:%M") == "09:00"


def test_a_naive_value_is_treated_as_utc() -> None:
    assert to_belgian(datetime(2026, 7, 1, 8, 0)).strftime("%H:%M") == "10:00"
