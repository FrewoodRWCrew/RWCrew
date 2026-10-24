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


# Every screen MasterData currently has. "Season", "Festivals" and "Teams"
# are its actual pieces of master data ("Team Location"/"Delivery Method"/
# "Team Tasks"/"Ploegverantwoordelijken" are real screens nested one level
# under Teams); "Roles" and "Users" are the two access-rights screens;
# "Data Upload/Download" gates the bulk XLSX import/export tile grid (one
# tile per master-data table) — a single screen key for all tiles, the same
# way KarTracker's own "kartracker.dataupload" gates both of its tiles. All
# are gated independently of one another — a Festivals permission does not
# imply a Season permission, and dataupload access does not imply access to
# any one table's own screen (or vice versa). Products and their four
# lookup lists moved to StockMaster (module-4, see its screens.py); their
# old keys (sort orders 2-6) were removed by a migration.
SCREEN_DEFINITIONS: list[ScreenDefinition] = [
    ScreenDefinition(key="masterdata.season", label="Years", sort_order=1),
    ScreenDefinition(key="masterdata.roles", label="Roles", sort_order=7),
    ScreenDefinition(key="masterdata.users", label="Users", sort_order=8),
    ScreenDefinition(key="masterdata.festival", label="Festivals", sort_order=9),
    ScreenDefinition(key="masterdata.teams", label="Teams", sort_order=10),
    ScreenDefinition(key="masterdata.team-location", label="Team Location", sort_order=11),
    ScreenDefinition(key="masterdata.delivery-method", label="Delivery Method", sort_order=12),
    ScreenDefinition(key="masterdata.team-tasks", label="Team Tasks", sort_order=13),
    ScreenDefinition(key="masterdata.team-responsibles", label="Ploegverantwoordelijken", sort_order=14),
    ScreenDefinition(key="masterdata.dataupload", label="Data Upload/Download", sort_order=15),
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
