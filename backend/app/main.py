# This is the entry point of the FastAPI backend: it creates the actual
# web application, tells it which "routers" (groups of related endpoints)
# exist, and configures cross-cutting settings like CORS.
#
# Start it during development (from the "backend" folder, with the
# virtual environment active) with:
#   uvicorn app.main:app --reload --port 8000

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.landing.admin import router as admin_router
from app.landing.auth import router as auth_router
from app.landing.master_data import router as master_data_router
from app.landing.modules import router as modules_router
from app.modules.module_1.router import router as module_1_router
from app.modules.module_2.router import router as module_2_router
from app.modules.module_3.router import router as module_3_router
from app.modules.module_4.router import router as module_4_router
from app.modules.module_5.router import router as module_5_router
from app.modules.module_6.router import router as module_6_router
from app.modules.module_7.router import router as module_7_router
from app.modules.module_8.router import router as module_8_router
from app.modules.module_9.router import router as module_9_router

# Create the actual FastAPI application object.
app = FastAPI(title="RW Crew API")

# Allow the Next.js frontend (running on a different port during
# development, and a different domain in production) to call this API
# from the browser, and to send/receive our authentication cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register every group of endpoints. Each router already defines its own
# URL prefix (e.g. "/api/auth"), so we don't repeat that here.
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(master_data_router)
app.include_router(modules_router)
app.include_router(module_1_router)
app.include_router(module_2_router)
app.include_router(module_3_router)
app.include_router(module_4_router)
app.include_router(module_5_router)
app.include_router(module_6_router)
app.include_router(module_7_router)
app.include_router(module_8_router)
app.include_router(module_9_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """A tiny endpoint to confirm the API is running, used for basic checks."""
    return {"status": "ok"}
