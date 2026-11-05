# Mass test: loads last year's lists (old Excel files in their own layout)
# into an RWCrew environment through the normal API, as a real migration,
# and logs every row that can't be loaded as an issue with a description and
# a proposed solution (an Excel report per run).
#
#   python -m masstest convert <old list.xlsx> --kind atelier-desk --out <load workbook.xlsx>
#   python -m masstest run --env local|test|prod --load <load workbook.xlsx> --out <folder> [--dry-run]
#   python -m masstest screens <screens.json> --env local|test|prod --out <folder>
#
# Two phases: "convert" turns an old list into the standard load workbook
# (reviewed by a person before anything is sent), "run" sends that workbook to
# one environment. A ledger per environment makes a run safe to repeat. The
# source lists and the reports hold personal data: keep them outside the repo.
