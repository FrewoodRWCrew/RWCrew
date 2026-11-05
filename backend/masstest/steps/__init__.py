# The runner's steps: one per sheet of the load workbook, run in this order.
# A step has a preflight (look up everything it needs, log what's missing,
# nothing written) and a run (send its rows). Adding a module = adding steps
# (and a converter); the runner stays the same. Shared helpers: common.py.

from masstest.steps.atelier import AtelierDeskStep

# Every step, in the order the runner runs them.
STEPS: list[type] = [AtelierDeskStep]
