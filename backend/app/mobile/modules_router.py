# The endpoint behind the phone app's landing page: the tiles the current
# user may open. Same idea as the web landing page (all modules combined
# with the user's accessible_module_keys), but the backend already narrows
# the answer down to the modules the phone actually supports.

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.module import Module
from app.db.models.user import User
from app.landing.deps import get_current_user
from app.mobile.registry import PHONE_MODULE_KEYS
from app.mobile.version_gate import require_supported_app_version
from app.schemas.module import ModuleResponse
from app.shared.access import get_accessible_module_keys

router = APIRouter(
    prefix="/api/mobile/v1/modules",
    tags=["mobile-modules"],
    dependencies=[Depends(require_supported_app_version)],
)


@router.get("", response_model=list[ModuleResponse])
def list_phone_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ModuleResponse]:
    """The landing-page tiles for this user, in tile order.

    A module appears only if (1) the phone supports it, (2) it is switched
    on site-wide, and (3) the super admin granted this user access to it.
    Being super admin does not grant access by itself, exactly like the web.
    """
    accessible_keys = set(get_accessible_module_keys(db, current_user.id))
    # Only keys that are both accessible and phone-supported survive.
    wanted_keys = accessible_keys & set(PHONE_MODULE_KEYS)

    modules = db.scalars(
        select(Module).where(Module.key.in_(wanted_keys), Module.is_active.is_(True)).order_by(Module.sort_order)
    ).all()
    return [ModuleResponse(key=module.key, name=module.name, sort_order=module.sort_order) for module in modules]
