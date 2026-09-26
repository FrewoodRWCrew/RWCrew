# This file is the single source of truth for which screens exist inside
# the KarTracker module. To add a brand-new screen: add one entry here
# (plus whatever page/endpoints actually implement it) — that's it. The
# next time the backend starts, sync_screens() below notices the new entry
# and adds it to the database, where it automatically shows up as a new,
# unchecked row in every role's permission matrix on the Roles screen.
# Nothing else needs to be touched by hand.

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_screen import KarTrackerScreen


@dataclass(frozen=True)
class ScreenDefinition:
    """Describes one screen: its stable key, display label, and order."""

    # The stable, code-friendly identifier, e.g. "kartracker.roles". This
    # must never change once set, since it's used as the database key.
    key: str
    # The name shown in the UI, e.g. "Roles".
    label: str
    # The order this screen appears in lists (1 = first).
    sort_order: int


# KarTracker's screens: the two access-rights screens, plus the cart
# registry ("Karlijst") phase — KarManagement (the fleet itself),
# Distributiepunten, Zone, Afleverlocatie (three master-data screens
# added alongside KarManagement — Afleverlocatie references both Zone and
# Distributiepunt, so those two must exist first) and KarStatussen (the
# lookup of statuses a kar can have). "Data Upload/Download" is its own
# screen (own permission row) rather than folded into each entity's own
# permissions, since bulk import/export access is meant to be grantable
# independently of ordinary CRUD access. Delivery planning screens are
# designed and added here in a later phase.
SCREEN_DEFINITIONS: list[ScreenDefinition] = [
    ScreenDefinition(key="kartracker.roles", label="Roles", sort_order=1),
    ScreenDefinition(key="kartracker.users", label="Users", sort_order=2),
    ScreenDefinition(key="kartracker.karmanagement", label="KarManagement", sort_order=3),
    ScreenDefinition(key="kartracker.karstatuses", label="KarStatussen", sort_order=4),
    ScreenDefinition(key="kartracker.distributiepunten", label="Distributiepunten", sort_order=5),
    ScreenDefinition(key="kartracker.zones", label="Zone", sort_order=6),
    ScreenDefinition(key="kartracker.afleverlocaties", label="Afleverlocatie", sort_order=7),
    ScreenDefinition(key="kartracker.actions", label="Actions", sort_order=8),
    ScreenDefinition(key="kartracker.dataupload", label="Data Upload/Download", sort_order=9),
    # Read-only report screen living under the "Actions" sidebar group,
    # gated by its own permission so it can be granted independently of
    # the "Actions" placeholder screen above. Step 1 of a planned report
    # that joins KarManagement with its lookups; more source tables get
    # folded into the same query in a later phase.
    ScreenDefinition(key="kartracker.karplanning", label="Kar Planning", sort_order=10),
    # Read-only map screen living under the same "Actions" sidebar group as
    # Kar Planning, gated by its own permission so it can be granted
    # independently of both "Actions" and "Kar Planning". Plots every
    # Kar/Afleverlocatie/Distributiepunt row that has coordinates; rows
    # without coordinates still show up in the accompanying side list.
    ScreenDefinition(key="kartracker.karmap", label="Kar Map", sort_order=11),
    # The event site's ground-plan image + its geographic corner
    # coordinates, overlaid on Kar Map as a toggleable layer. Its own
    # permission gates editing it; viewing it is shared with Kar Map's own
    # viewers via require_screen_view_or_create (see router.py), since Kar
    # Map needs to read it to render the overlay.
    ScreenDefinition(key="kartracker.groundplan", label="Grondplan", sort_order=12),
    # "Plan a kar": per team, pick the afleverlocatie for every active
    # festival of the selected season. Lives under the "Actions" sidebar
    # group, right below Kar Map.
    ScreenDefinition(key="kartracker.plankar", label="Plan a kar", sort_order=13),
    # Masterdata screen: per active festival of the selected season, its
    # delivery date and pick-up date (table "Festivals_leverdatum").
    ScreenDefinition(key="kartracker.leverdata", label="Delivery Dates", sort_order=14),
]


def sync_screens(db: Session) -> None:
    """Make sure every screen in SCREEN_DEFINITIONS exists in the database,
    with its label/order matching what's defined here (code is always the
    source of truth for those two fields). Called once every time the
    backend starts up — see the "lifespan" setup in app/main.py.
    """
    existing_screens_by_key = {screen.key: screen for screen in db.scalars(select(KarTrackerScreen)).all()}

    for definition in SCREEN_DEFINITIONS:
        existing_screen = existing_screens_by_key.get(definition.key)
        if existing_screen is None:
            # A brand-new screen — add it so it starts appearing in the
            # permission matrix (with no permissions yet, for every role).
            db.add(KarTrackerScreen(key=definition.key, label=definition.label, sort_order=definition.sort_order))
        else:
            # Already exists — keep its label/order up to date with the code.
            existing_screen.label = definition.label
            existing_screen.sort_order = definition.sort_order

    db.commit()
