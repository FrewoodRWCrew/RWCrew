# This file is the single source of truth for which screens exist inside
# the Atelier module. To add a brand-new screen: add one entry here
# (plus whatever page/endpoints actually implement it) — that's it. The
# next time the backend starts, sync_screens() below notices the new entry
# and adds it to the database, where it automatically shows up as a new,
# unchecked row in every role's permission matrix on the Roles screen.

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.atelier_screen import AtelierScreen


@dataclass(frozen=True)
class ScreenDefinition:
    """Describes one screen: its stable key, display label, and order."""

    # The stable, code-friendly identifier, e.g. "atelier.roles".
    # This must never change once set, since it's used as the database key.
    key: str
    # The name shown in the UI, e.g. "Roles".
    label: str
    # The order this screen appears in lists (1 = first).
    sort_order: int


# Every screen Atelier currently has. Each is gated independently:
# - kpi: the module's main page;
# - desk / open: the "Balie" group (Ophalen / Terugbrengen — "edit" also
#   allows "Uitgifte annuleren" — and the pieces not returned yet);
# - reservations / preparation: the "Reservaties" group (persons per team per
#   festival, and what to prepare each day + the picklist);
# - stock / receipt / wash / writeoff / count / bookings / orderneeds: the
#   "Stock" group (overview, the bookings that change stock, their history
#   with undo — "edit" on bookings — and the Te bestellen list);
# - articles / sizes / dataupload: the "Masterdata" group (the clothing
#   catalogue, its sizes, and the bulk XLSX import/export); what each team
#   gets is part of its reservation (the old "teampackages" screen is gone);
# - settings / scantest / mailtemplates: the "Instellingen" group (the
#   wristband switch, scanners, webhook log; sending a test wristband scan;
#   the texts of the mails sent after Ophalen / Terugbrengen);
# - roles / users: the access-rights screens.
SCREEN_DEFINITIONS: list[ScreenDefinition] = [
    ScreenDefinition(key="atelier.kpi", label="KPI", sort_order=1),
    ScreenDefinition(key="atelier.desk", label="Uitgifte & inname", sort_order=3),
    ScreenDefinition(key="atelier.open", label="Openstaand", sort_order=4),
    ScreenDefinition(key="atelier.reservations", label="Reservaties", sort_order=5),
    ScreenDefinition(key="atelier.preparation", label="Voorbereiden", sort_order=6),
    ScreenDefinition(key="atelier.stock", label="Stock", sort_order=7),
    ScreenDefinition(key="atelier.receipt", label="Ontvangst", sort_order=8),
    ScreenDefinition(key="atelier.wash", label="Wassen", sort_order=9),
    ScreenDefinition(key="atelier.writeoff", label="Afboeken", sort_order=10),
    ScreenDefinition(key="atelier.count", label="Telling", sort_order=11),
    ScreenDefinition(key="atelier.bookings", label="Boekingen", sort_order=12),
    ScreenDefinition(key="atelier.orderneeds", label="Te bestellen", sort_order=13),
    ScreenDefinition(key="atelier.articles", label="Artikelen", sort_order=20),
    ScreenDefinition(key="atelier.sizes", label="Maten", sort_order=21),
    ScreenDefinition(key="atelier.dataupload", label="Data Upload/Download", sort_order=22),
    ScreenDefinition(key="atelier.settings", label="Instellingen", sort_order=30),
    ScreenDefinition(key="atelier.scantest", label="Test-scan", sort_order=31),
    ScreenDefinition(key="atelier.mailtemplates", label="E-mails", sort_order=32),
    ScreenDefinition(key="atelier.roles", label="Roles", sort_order=90),
    ScreenDefinition(key="atelier.users", label="Users", sort_order=91),
]


def sync_screens(db: Session) -> None:
    """Make sure every screen in SCREEN_DEFINITIONS exists in the database,
    with its label/order matching what's defined here (code is always the
    source of truth for those two fields). Called once every time the
    backend starts up — see the "lifespan" setup in app/main.py.
    """
    existing_screens_by_key = {screen.key: screen for screen in db.scalars(select(AtelierScreen)).all()}

    for definition in SCREEN_DEFINITIONS:
        existing_screen = existing_screens_by_key.get(definition.key)
        if existing_screen is None:
            # A brand-new screen — add it so it starts appearing in the
            # permission matrix (with no permissions yet, for every role).
            db.add(AtelierScreen(key=definition.key, label=definition.label, sort_order=definition.sort_order))
        else:
            # Already exists — keep its label/order up to date with the code.
            existing_screen.label = definition.label
            existing_screen.sort_order = definition.sort_order

    db.commit()
