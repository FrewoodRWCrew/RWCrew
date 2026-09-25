# Schemas describing login attempts, used by the admin "Login History" screen.

from datetime import datetime

from pydantic import BaseModel


class LoginHistoryEntry(BaseModel):
    """One login attempt, shown as a row in the admin "Login History" table."""

    id: int
    user_id: int | None
    email_attempted: str
    # None when the attempt's user_id is null (unknown email, or the
    # matched user has since been deleted).
    display_name: str | None
    success: bool
    ip_address: str | None
    # "web" or "mobile"; None for attempts recorded before this was tracked.
    source: str | None
    created_at: datetime


class LoginHistoryPage(BaseModel):
    """One page of login history, plus the total row count for pagination."""

    items: list[LoginHistoryEntry]
    total: int
