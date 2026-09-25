# The smartphone app's login endpoints. Same rules as the web login
# (app/landing/auth.py) — same users, same password check, same refresh
# token rotation — but tokens travel in the JSON body instead of cookies,
# because a native app has no browser cookie jar.

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_token,
    verify_password,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.landing.auth import (
    _as_aware_utc,
    _build_current_user_response,
    _issue_and_store_refresh_token,
    _record_login_attempt,
)
from app.landing.deps import get_current_user
from app.mobile.schemas import MobileRefreshRequest, MobileTokenResponse
from app.mobile.version_gate import require_supported_app_version
from app.schemas.auth import CurrentUserResponse, LoginRequest

# Every route here starts with "/api/mobile/v1/auth", and every one of them
# refuses app builds older than the configured minimum version.
router = APIRouter(
    prefix="/api/mobile/v1/auth",
    tags=["mobile-auth"],
    dependencies=[Depends(require_supported_app_version)],
)


def _build_token_response(db: Session, user: User, access_token: str, refresh_token: str) -> MobileTokenResponse:
    """Bundle a fresh token pair with the user's details for the phone."""
    return MobileTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_minutes * 60,
        user=_build_current_user_response(db, user),
    )


@router.post("/login", response_model=MobileTokenResponse)
def mobile_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> MobileTokenResponse:
    """Check an email/password combination and hand back tokens in the body."""
    user = db.scalar(select(User).where(User.email == payload.email))

    # Same single, vague error for every failure as the web login, so an
    # attacker can't tell a wrong email from a wrong password.
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        _record_login_attempt(db, request, payload.email, user, success=False, source="mobile")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    session_end = datetime.now(timezone.utc) + timedelta(hours=settings.session_max_hours)
    access_token = create_access_token(user.id, session_end)
    refresh_token = _issue_and_store_refresh_token(db, user.id, session_end)
    _record_login_attempt(db, request, payload.email, user, success=True, source="mobile")
    db.commit()

    return _build_token_response(db, user, access_token, refresh_token)


@router.post("/refresh", response_model=MobileTokenResponse)
def mobile_refresh(payload: MobileRefreshRequest, db: Session = Depends(get_db)) -> MobileTokenResponse:
    """Swap a valid refresh token for a brand-new access + refresh token."""
    try:
        user_id = decode_token(payload.refresh_token, expected_type="refresh")
    except InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again") from error

    # Find the stored (hashed) record matching the token the phone sent.
    stored_tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
    )
    matching_record = next((record for record in stored_tokens if verify_password(payload.refresh_token, record.token_hash)), None)

    # Unknown, already-used (rotated away) or expired tokens are all refused.
    if matching_record is None or _as_aware_utc(matching_record.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or disabled")

    # Rotate: the old refresh token dies here, a new one replaces it.
    matching_record.revoked = True
    # Keep the original session end: renewing never extends the login.
    session_end = _as_aware_utc(matching_record.expires_at)
    new_access_token = create_access_token(user.id, session_end)
    new_refresh_token = _issue_and_store_refresh_token(db, user.id, session_end)
    db.commit()

    return _build_token_response(db, user, new_access_token, new_refresh_token)


@router.post("/logout")
def mobile_logout(payload: MobileRefreshRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Revoke the phone's refresh token so it can never be used again."""
    for record in db.scalars(select(RefreshToken).where(RefreshToken.revoked.is_(False))):
        if verify_password(payload.refresh_token, record.token_hash):
            record.revoked = True
    db.commit()
    return {"logged_out": True}


@router.get("/me", response_model=CurrentUserResponse)
def mobile_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CurrentUserResponse:
    """Who is logged in, and which modules can they open (Bearer token required)."""
    return _build_current_user_response(db, current_user)
