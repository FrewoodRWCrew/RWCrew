# This file is the single source of truth for which screens exist inside
# the StockMaster module. To add a brand-new screen: add one entry here
# (plus whatever page/endpoints actually implement it) — that's it. The
# next time the backend starts, sync_screens() below notices the new entry
# and adds it to the database, where it automatically shows up as a new,
# unchecked row in every role's permission matrix on the Roles screen.

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.stockmaster_screen import StockMasterScreen


@dataclass(frozen=True)
class ScreenDefinition:
    """Describes one screen: its stable key, display label, and order."""

    # The stable, code-friendly identifier, e.g. "stockmaster.roles".
    # This must never change once set, since it's used as the database key.
    key: str
    # The name shown in the UI, e.g. "Roles".
    label: str
    # The order this screen appears in lists (1 = first).
    sort_order: int


# Every screen StockMaster currently has. Each is gated independently:
# - kpi: the module's main page;
# - stock: the stock overview; "create" = Inboeken / Uitboeken;
# - kars: the kar overview; "create" = Kar laden / uitladen / vertrekt / terug;
# - count: Telling; "create" = book a count;
# - requirements: what each kar needs per season (create/edit/delete lines);
# - orderneeds: needs versus stock; "create" = Inboeken from that list;
# - bookings: the booking history; "delete" = undo (reverse) a booking;
# - reasons: the reasons master data (Instellingen);
# - closedseason: not a page but a switch — "edit" allows booking in a
#   season whose period is closed;
# - roles / users: the access-rights screens.
SCREEN_DEFINITIONS: list[ScreenDefinition] = [
    ScreenDefinition(key="stockmaster.kpi", label="KPI", sort_order=1),
    ScreenDefinition(key="stockmaster.stock", label="Stock overview", sort_order=2),
    ScreenDefinition(key="stockmaster.kars", label="Kars", sort_order=3),
    ScreenDefinition(key="stockmaster.count", label="Stock count", sort_order=4),
    ScreenDefinition(key="stockmaster.requirements", label="Kar needs", sort_order=5),
    ScreenDefinition(key="stockmaster.orderneeds", label="To order", sort_order=6),
    ScreenDefinition(key="stockmaster.bookings", label="Bookings", sort_order=7),
    ScreenDefinition(key="stockmaster.reasons", label="Reasons", sort_order=8),
    ScreenDefinition(key="stockmaster.closedseason", label="Book in a closed season", sort_order=9),
    ScreenDefinition(key="stockmaster.roles", label="Roles", sort_order=10),
    ScreenDefinition(key="stockmaster.users", label="Users", sort_order=11),
]


def sync_screens(db: Session) -> None:
    """Make sure every screen in SCREEN_DEFINITIONS exists in the database,
    with its label/order matching what's defined here (code is always the
    source of truth for those two fields). Called once every time the
    backend starts up — see the "lifespan" setup in app/main.py.
    """
    existing_screens_by_key = {screen.key: screen for screen in db.scalars(select(StockMasterScreen)).all()}

    for definition in SCREEN_DEFINITIONS:
        existing_screen = existing_screens_by_key.get(definition.key)
        if existing_screen is None:
            # A brand-new screen — add it so it starts appearing in the
            # permission matrix (with no permissions yet, for every role).
            db.add(StockMasterScreen(key=definition.key, label=definition.label, sort_order=definition.sort_order))
        else:
            # Already exists — keep its label/order up to date with the code.
            existing_screen.label = definition.label
            existing_screen.sort_order = definition.sort_order

    db.commit()
