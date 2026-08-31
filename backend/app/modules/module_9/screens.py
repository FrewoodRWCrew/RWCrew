# This file is the single source of truth for which screens exist inside
# the MasterData module. To add a brand-new screen: add one entry here
# (plus whatever page/endpoints actually implement it) — that's it. The
# next time the backend starts, sync_screens() below notices the new
# entry and adds it to the database, where it automatically shows up as a
# new, unchecked row in every role's permission matrix on the Roles
# screen. Nothing else needs to be touched by hand.

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.masterdata_screen import MasterDataScreen


@dataclass(frozen=True)
class ScreenDefinition:
    """Describes one screen: its stable key, display label, and order."""

    # The stable, code-friendly identifier, e.g. "masterdata.roles". This
    # must never change once set, since it's used as the database key.
    key: str
    # The name shown in the UI, e.g. "Roles".
    label: str
    # The order this screen appears in lists (1 = first).
    sort_order: int


# Every screen MasterData currently has. "Season" and "Products" are its
# actual pieces of master data; "Type"/"Warehouses"/"Product categories"/
# "Product limits" are the four lookup lists ("selection criteria") nested
# under Products; "Roles" and "Users" are the two access-rights screens.
# All are gated independently of one another.
SCREEN_DEFINITIONS: list[ScreenDefinition] = [
    ScreenDefinition(key="masterdata.season", label="Seasons", sort_order=1),
    ScreenDefinition(key="masterdata.products", label="Products", sort_order=2),
    ScreenDefinition(key="masterdata.product-types", label="Type", sort_order=3),
    ScreenDefinition(key="masterdata.warehouses", label="Magazijnen", sort_order=4),
    ScreenDefinition(key="masterdata.product-categories", label="Categorieën", sort_order=5),
    ScreenDefinition(key="masterdata.product-limits", label="Limieten", sort_order=6),
    ScreenDefinition(key="masterdata.roles", label="Roles", sort_order=7),
    ScreenDefinition(key="masterdata.users", label="Users", sort_order=8),
]


def sync_screens(db: Session) -> None:
    """Make sure every screen in SCREEN_DEFINITIONS exists in the database,
    with its label/order matching what's defined here (code is always the
    source of truth for those two fields). Called once every time the
    backend starts up — see the "lifespan" setup in app/main.py.
    """
    existing_screens_by_key = {screen.key: screen for screen in db.scalars(select(MasterDataScreen)).all()}

    for definition in SCREEN_DEFINITIONS:
        existing_screen = existing_screens_by_key.get(definition.key)
        if existing_screen is None:
            # A brand-new screen — add it so it starts appearing in the
            # permission matrix (with no permissions yet, for every role).
            db.add(MasterDataScreen(key=definition.key, label=definition.label, sort_order=definition.sort_order))
        else:
            # Already exists — keep its label/order up to date with the code.
            existing_screen.label = definition.label
            existing_screen.sort_order = definition.sort_order

    db.commit()
