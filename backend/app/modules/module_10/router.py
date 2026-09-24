# Module 10 ("Mobile App") is the web-side download page for the smartphone
# app. It reuses the shared module endpoints (status + role management, see
# app/modules/common.py) and adds one endpoint: the install links and release
# info the page shows. Nothing here contains phone app code (see mobile/).

from fastapi import Depends
from pydantic import BaseModel

from app.core.config import settings
from app.landing.deps import get_current_user
from app.db.models.user import User
from app.modules.common import create_module_router

router = create_module_router(module_key="module-10", module_label="Mobile App")


class MobileAppInfo(BaseModel):
    """What the download page needs: install links, latest version, changelog."""

    ios_testflight_url: str | None
    android_download_url: str | None
    latest_version: str | None
    # One entry per changelog line, blank lines dropped.
    changelog: list[str]


@router.get("/app-info", response_model=MobileAppInfo)
def get_app_info(_current_user: User = Depends(get_current_user)) -> MobileAppInfo:
    """Return the phone app's install links and release info.

    Any logged-in user may read this (the page itself is only reachable for
    users granted module-10 access; the links are not secret, just unlisted).
    Empty settings come back as null so the page can hide that button.
    """
    return MobileAppInfo(
        ios_testflight_url=settings.mobile_ios_testflight_url or None,
        android_download_url=settings.mobile_android_download_url or None,
        latest_version=settings.mobile_latest_version or None,
        changelog=[line.strip() for line in settings.mobile_changelog.splitlines() if line.strip()],
    )
