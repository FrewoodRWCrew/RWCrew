# The list of modules the smartphone app can open. The web app has 9
# modules (see app/modules/registry.py), but the phone deliberately only
# supports the ones designed for it. The landing-page endpoint
# (app/mobile/modules_router.py) only ever returns modules from this list,
# so the app never shows a tile that leads nowhere.
#
# To bring another module to the phone: add its key here, add its own
# /api/mobile/v1/<module> router (see module_3_router.py), and add its tile
# colour/icon to mobile/src/lib/module-theme.ts.

PHONE_MODULE_KEYS: list[str] = [
    # Intervention Requests: only its "KPI overzicht" and "Akties" (the
    # requests screen). MasterData and Access Rights stay web-only.
    "module-3",
]
