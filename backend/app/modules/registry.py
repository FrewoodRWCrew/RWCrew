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


# The 9 placeholder modules. Replace "Module 1".."Module 9" with real
# names here once they're decided — nothing else needs to change.
MODULE_DEFINITIONS: list[ModuleDefinition] = [
    ModuleDefinition(key=f"module-{number}", name=f"Module {number}", sort_order=number) for number in range(1, 10)
]
