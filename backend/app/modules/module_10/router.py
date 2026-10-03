# Module 10 ("Mobile App") is the web-side install page for the phone app.
# The phone app is the PWA under /m on the same site (see CLAUDE.md, "Phone
# section"), so there is nothing to download: the page shows the /m address
# and a QR code of it. This router reuses the shared module endpoints (status
# + role management, see app/modules/common.py) and adds that one endpoint.

import segno
from fastapi import Depends
from pydantic import BaseModel

from app.core.config import settings
from app.db.models.user import User
from app.landing.deps import get_current_user
from app.modules.common import create_module_router

router = create_module_router(module_key="module-10", module_label="Mobile App")

# The phone section's path on the web app (frontend/src/app/[locale]/m/).
PHONE_SECTION_PATH = "/m"


class PwaInstallInfo(BaseModel):
    """What the install page needs: the phone app's address and a QR code of it."""

    # Null when this environment has no APP_PUBLIC_URL configured.
    install_url: str | None
    # A ready-to-use "data:image/svg+xml;..." URI, so the page can show it in
    # a plain <img> without a second (authenticated) request. Null with the URL.
    qr_code_data_uri: str | None


@router.get("/install-info", response_model=PwaInstallInfo)
def get_install_info(_current_user: User = Depends(get_current_user)) -> PwaInstallInfo:
    """Return the phone app's address and a QR code of it.

    Any logged-in user may read this (the page itself is only reachable for
    users granted module-10 access; the address is not secret). The address is
    built from settings.app_public_url, so test and production each point at
    their own site.
    """
    if not settings.app_public_url:
        return PwaInstallInfo(install_url=None, qr_code_data_uri=None)

    install_url = f"{settings.app_public_url.rstrip('/')}{PHONE_SECTION_PATH}"
    # Medium error correction (same as the karblad QR codes) and a quiet zone
    # of 2 modules: easily scanned from a screen, without a large white border.
    qr_code = segno.make(install_url, error="m", micro=False)
    return PwaInstallInfo(install_url=install_url, qr_code_data_uri=qr_code.svg_data_uri(scale=6, border=2))
