# This file is the single, shared list of the 9 modules that exist in
# RW Crew. Both the database-seeding script and the API routers read this
# same list, so there is only one place to update once real module names
# are decided later.

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleDefinition:
    """Describes one module: its stable key, display name, and tile order."""

    # The stable, code-friendly identifier, e.g. "module-1". This must
    # never change once set, because it is used as the database key.
    key: str
    # The human-readable name shown on its tile, e.g. "Module 1".
    name: str
    # The order this module's tile appears on the landing page (1 = first).
    sort_order: int


# The name each module should seed with. Most are still placeholders
# ("Module 2", "Module 4".."Module 8") — replace them here once real
# names are decided, nothing else needs to change. module-1 (TagScan) and
# module-9 (MasterData) already have real names and their own bespoke
# routers (see app/modules/module_1, app/modules/module_9) instead of the
# shared create_module_router() factory used by the placeholders.
# module-3 (Intervention Requests) also has a bespoke router with multiple
# screens and per-screen permissions, so it belongs with TagScan/MasterData
# rather than with the placeholder modules using the shared factory.
# module-8 (Altsien Select) likewise has its own bespoke router: the Ploeg
# Wizard in which Altsien Kernleden make their per-team choices.
#
# module-10 ("Mobile App") is the web-side download page for the smartphone
# app (install links, latest version, changelog); it contains no phone code.
_MODULE_NAMES = {
    "module-1": "TagScan",
    "module-3": "Intervention Requests",
    "module-8": "Altsien Select",
    "module-9": "MasterData",
    "module-10": "Mobile App",
}

MODULE_DEFINITIONS: list[ModuleDefinition] = [
    ModuleDefinition(
        key=f"module-{number}",
        name=_MODULE_NAMES.get(f"module-{number}", f"Module {number}"),
        sort_order=number,
    )
    for number in range(1, 11)
]
