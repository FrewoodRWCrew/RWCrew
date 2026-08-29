# All 9 modules currently need the exact same handful of endpoints: a
# "coming soon" placeholder page, and a way for that module's own admin to
# manage who holds which role inside it. Rather than repeating that code
# nine times, this file builds one reusable APIRouter that any module's
# thin router file (see app/modules/module_1/router.py etc.) can create by
# just passing in its own module key.
#
# When a module's real functionality is built later, its own router file
# can add further module-specific endpoints alongside (or instead of)
# this shared placeholder behaviour.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.module import Module
from app.db.models.module_role import ModuleRole, ModuleRoleName
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.landing.deps import get_current_user
from app.schemas.module import ModuleRoleAssignmentResponse, SetModuleRoleRequest


def _get_module_or_404(db: Session, module_key: str) -> Module:
    module = db.scalar(select(Module).where(Module.key == module_key))
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return module


def _get_user_role_in_module(db: Session, user_id: int, module_id: int) -> ModuleRoleName | None:
    role_row = db.scalar(
        select(ModuleRole).where(ModuleRole.user_id == user_id, ModuleRole.module_id == module_id)
    )
    return role_row.role if role_row else None


def create_module_router(module_key: str, module_label: str) -> APIRouter:
    """Build the shared set of endpoints for one module, scoped to its key.

    module_key: the stable identifier, e.g. "module-1".
    module_label: a human-readable name for error messages, e.g. "Module 1".
    """
    router = APIRouter(prefix=f"/api/modules/{module_key}", tags=[module_label])

    def require_module_access(
        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
    ) -> Module:
        """Only let the request through if the user has been granted access
        to THIS module (super admins are not automatically exempt — see
        app/shared/access.py for why).
        """
        module = _get_module_or_404(db, module_key)
        has_access = db.scalar(
            select(UserModuleAccess).where(
                UserModuleAccess.user_id == current_user.id, UserModuleAccess.module_id == module.id
            )
        )
        if has_access is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No access to {module_label}")
        return module

    def require_module_admin(
        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
    ) -> Module:
        """Only let the request through if the user is this module's own
        admin, OR the site-wide super admin (who can always step in to fix
        a module's roles, e.g. if its only admin leaves).
        """
        module = _get_module_or_404(db, module_key)
        if current_user.is_super_admin:
            return module

        role = _get_user_role_in_module(db, current_user.id, module.id)
        if role != ModuleRoleName.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not an admin of {module_label}")
        return module

    @router.get("/status")
    def get_status(
        module: Module = Depends(require_module_access),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        """The placeholder landing content for this module: its name and
        the caller's own role, until real functionality is built.
        """
        return {
            "module_key": module.key,
            "module_name": module.name,
            "your_role": _get_user_role_in_module(db, current_user.id, module.id),
        }

    @router.get("/roles", response_model=list[ModuleRoleAssignmentResponse])
    def list_roles(
        module: Module = Depends(require_module_admin),
        db: Session = Depends(get_db),
    ) -> list[ModuleRoleAssignmentResponse]:
        """List every user with access to this module, and their current role.

        Only this module's own admin(s), or the super admin, can see this.
        """
        users_with_access = db.scalars(
            select(User)
            .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
            .where(UserModuleAccess.module_id == module.id)
            .order_by(User.display_name)
        ).all()

        return [
            ModuleRoleAssignmentResponse(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                role=_get_user_role_in_module(db, user.id, module.id),
            )
            for user in users_with_access
        ]

    @router.put("/roles/{user_id}", response_model=ModuleRoleAssignmentResponse)
    def set_role(
        user_id: int,
        payload: SetModuleRoleRequest,
        module: Module = Depends(require_module_admin),
        db: Session = Depends(get_db),
    ) -> ModuleRoleAssignmentResponse:
        """Set (or, if role is null, remove) a user's role inside this module."""
        target_user = db.get(User, user_id)
        if target_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        has_access = db.scalar(
            select(UserModuleAccess).where(
                UserModuleAccess.user_id == user_id, UserModuleAccess.module_id == module.id
            )
        )
        if has_access is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user must first be granted access to the module by the super admin",
            )

        existing_role_row = db.scalar(
            select(ModuleRole).where(ModuleRole.user_id == user_id, ModuleRole.module_id == module.id)
        )

        if payload.role is None:
            # Removing the role: delete the row if one exists.
            if existing_role_row is not None:
                db.delete(existing_role_row)
        elif existing_role_row is not None:
            # Updating an existing role.
            existing_role_row.role = payload.role
        else:
            # Assigning a role for the first time.
            db.add(ModuleRole(user_id=user_id, module_id=module.id, role=payload.role))

        db.commit()

        return ModuleRoleAssignmentResponse(
            user_id=target_user.id,
            email=target_user.email,
            display_name=target_user.display_name,
            role=payload.role,
        )

    return router
