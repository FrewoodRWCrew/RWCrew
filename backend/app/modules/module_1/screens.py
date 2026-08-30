# This file is the single source of truth for which screens exist inside
# the Tagscan module. To add a brand-new screen: add one entry here (plus
# whatever page/endpoints actually implement it) — that's it. The next
# time the backend starts, sync_screens() below notices the new entry and
# adds it to the database, where it automatically shows up as a new,
# unchecked row in every role's permission matrix on the Roles screen.
# Nothing else needs to be touched by hand.

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.tagscan_screen import TagscanScreen


@dataclass(frozen=True)
class ScreenDefinition:
    """Describes one screen: its stable key, display label, and order."""

    # The stable, code-friendly identifier, e.g. "tagscan.roles". This
    # must never change once set, since it's used as the database key.
    key: str
    # The name shown in the UI, e.g. "Roles".
    label: str
    # The order this screen appears in lists (1 = first).
    sort_order: int


# Every screen Tagscan currently has. "Dashboard" is where the eventual
# CSV-import functionality will live; "Roles" and "Users" are the two
# access-rights screens, gated independently of one another.
SCREEN_DEFINITIONS: list[ScreenDefinition] = [
    ScreenDefinition(key="tagscan.dashboard", label="Dashboard", sort_order=1),
    ScreenDefinition(key="tagscan.roles", label="Roles", sort_order=2),
    ScreenDefinition(key="tagscan.users", label="Users", sort_order=3),
]


def sync_screens(db: Session) -> None:
    """Make sure every screen in SCREEN_DEFINITIONS exists in the database,
    with its label/order matching what's defined here (code is always the
    source of truth for those two fields). Called once every time the
    backend starts up — see the "lifespan" setup in app/main.py.
    """
    existing_screens_by_key = {screen.key: screen for screen in db.scalars(select(TagscanScreen)).all()}

    for definition in SCREEN_DEFINITIONS:
        existing_screen = existing_screens_by_key.get(definition.key)
        if existing_screen is None:
            # A brand-new screen — add it so it starts appearing in the
            # permission matrix (with no permissions yet, for every role).
            db.add(TagscanScreen(key=definition.key, label=definition.label, sort_order=definition.sort_order))
        else:
            # Already exists — keep its label/order up to date with the code.
            existing_screen.label = definition.label
            existing_screen.sort_order = definition.sort_order

    db.commit()
