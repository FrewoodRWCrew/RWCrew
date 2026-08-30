# This file defines the super-admin-only endpoints behind the landing
# page's admin sidebar: creating user accounts, and granting/revoking
# which modules each user is allowed to open ("Manage Access").
#
# Every endpoint in this file requires the super-admin flag (see
# require_super_admin in deps.py) — a normal user gets a 403 Forbidden
# error if they try to call any of these.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.landing.deps import require_super_admin
from app.schemas.module import SetUserAccessRequest
from app.schemas.user import UserCreateRequest, UserSummaryResponse
from app.shared.access import get_accessible_module_keys

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _build_user_summary(db: Session, user: User) -> UserSummaryResponse:
    """Turn a User database row into the summary shown in the admin table."""
    return UserSummaryResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_super_admin=user.is_super_admin,
        is_active=user.is_active,
        accessible_module_keys=get_accessible_module_keys(db, user.id),
    )


@router.get("/users", response_model=list[UserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_super_admin),
) -> list[UserSummaryResponse]:
    """List every user account, for the "Manage Access" table."""
    users = db.scalars(select(User).order_by(User.display_name)).all()
    return [_build_user_summary(db, user) for user in users]


@router.post("/users", response_model=UserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_super_admin),
) -> UserSummaryResponse:
    """Create a brand-new user account. Only the super admin can do this —
    RW Crew has no public "sign up" page, matching the requirement that
    access is created by admins, not requested by users.
    """
    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
        is_super_admin=payload.is_super_admin,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as error:
        # This happens if the email address is already taken.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists") from error

    db.refresh(new_user)
    return _build_user_summary(db, new_user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_super_admin: User = Depends(require_super_admin),
) -> None:
    """Permanently delete a user account, along with their module access
    and role assignments (removed automatically by the database).
    """
    if user_id == current_super_admin.id:
        # Stop a super admin from deleting the account they're currently
        # using, which could leave nobody left who can manage access.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()


@router.put("/users/{user_id}/access", response_model=UserSummaryResponse)
def set_user_module_access(
    user_id: int,
    payload: SetUserAccessRequest,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_super_admin),
) -> UserSummaryResponse:
    """Replace which modules a user can open with exactly the given list.

    This is the endpoint behind the "Manage Access" checkbox grid: the
    frontend sends the complete, current state of one user's row of
    checkboxes, and we make the database match it — adding any newly
    checked modules and removing any newly unchecked ones.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Look up the requested modules by their keys, so we can store the
    # relationship using module ids (and reject unknown keys up front).
    requested_modules = db.scalars(select(Module).where(Module.key.in_(payload.module_keys))).all()
    if len(requested_modules) != len(set(payload.module_keys)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more module keys are unknown")

    # Remove every access grant this user currently has...
    existing_grants = db.scalars(select(UserModuleAccess).where(UserModuleAccess.user_id == user_id)).all()
    for grant in existing_grants:
        db.delete(grant)

    # ...sending those deletes to the database now (instead of leaving
    # them queued alongside the inserts below), since otherwise
    # SQLAlchemy is free to run the inserts first — which would collide
    # with the unique (user_id, module_id) constraint whenever a module
    # that was already granted is being "re-granted" unchanged.
    db.flush()

    # ...then re-add exactly the ones that were requested.
    for module in requested_modules:
        db.add(UserModuleAccess(user_id=user_id, module_id=module.id))

    db.commit()
    return _build_user_summary(db, user)
