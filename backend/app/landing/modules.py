# This file defines the endpoint that lists all 9 modules. Any logged-in
# user can call it — the frontend combines this full list with the
# "accessible_module_keys" from /api/auth/me to decide which tiles to
# show as open versus locked.

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.module import Module
from app.db.models.user import User
from app.landing.deps import get_current_user
from app.schemas.module import ModuleResponse
from app.schemas.user import AltsienKernlidResponse

router = APIRouter(prefix="/api/modules", tags=["modules"])


@router.get("", response_model=list[ModuleResponse])
def list_modules(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[ModuleResponse]:
    """Return every site-wide-active module, in the order tiles should appear."""
    modules = db.scalars(select(Module).where(Module.is_active.is_(True)).order_by(Module.sort_order)).all()
    return [ModuleResponse(key=module.key, name=module.name, sort_order=module.sort_order) for module in modules]


@router.get("/altsien-kernleden", response_model=list[AltsienKernlidResponse])
def list_altsien_kernleden(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[User]:
    """Every active user flagged "Altsien Kernlid" (set on the Manage Access
    screen), for the Teams / Distributiepunt / Afleverlocatie pickers. Open
    to any logged-in user since those screens' users aren't super admins.
    """
    return list(
        db.scalars(
            select(User)
            .where(User.is_altsien_kernlid.is_(True), User.is_active.is_(True))
            .order_by(User.display_name)
        ).all()
    )
