# The single entry point of the smartphone app's API. app/main.py registers
# only this router; every phone endpoint group is added to it here, so the
# web side never needs to know what the phone API contains (see CLAUDE.md,
# "Mobile app (mobile/)").

from fastapi import APIRouter

from app.mobile.auth_router import router as auth_router
from app.mobile.module_3_router import router as module_3_router
from app.mobile.modules_router import router as modules_router

router = APIRouter()

# Login / refresh / logout / me for the phone: /api/mobile/v1/auth/*
router.include_router(auth_router)

# The landing page's tiles: /api/mobile/v1/modules
router.include_router(modules_router)

# Intervention Requests (KPI overzicht + Akties only): /api/mobile/v1/module-3/*
router.include_router(module_3_router)

# More phone modules are added the same way (see app/mobile/registry.py):
# each under /api/mobile/v1/<module>/..., reusing that module's own
# permission checks so rights stay identical to the web app.
