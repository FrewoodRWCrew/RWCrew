# This file defines the login-related API endpoints: logging in, getting
# a fresh access token via the refresh token, logging out, and asking
# "who am I currently logged in as".

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.login_history import LoginHistory
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.landing.deps import ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME, get_current_user
from app.schemas.auth import CurrentUserResponse, LoginRequest
from app.shared.access import get_accessible_module_keys

# Every route in this file will automatically start with "/api/auth".
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Attach the access and refresh tokens to the response as secure cookies.

    "HttpOnly" means JavaScript in the browser can never read these
    cookies (only the browser itself sends them back to our API), which
    protects the tokens from being stolen by malicious frontend code.
    """
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        path="/",
    )


def _issue_and_store_refresh_token(db: Session, user_id: int) -> str:
    """Create a new refresh token and remember its hash in the database."""
    refresh_token = create_refresh_token(user_id)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_password(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
        )
    )
    return refresh_token


def _record_login_attempt(db: Session, request: Request, email: str, user: User | None, success: bool) -> None:
    """Remember one login attempt (successful or not) for the admin
    "Login History" screen, so there's a record of who is using the tool
    and when — including attempts that failed.
    """
    db.add(
        LoginHistory(
            user_id=user.id if user is not None else None,
            email_attempted=email,
            success=success,
            ip_address=request.client.host if request.client is not None else None,
        )
    )


def _as_aware_utc(value: datetime) -> datetime:
    """Make sure a datetime read back from the database can be compared
    against datetime.now(timezone.utc).

    PostgreSQL remembers that a "timestamp with time zone" column is in
    UTC, but some databases (e.g. SQLite, used in our automated tests)
    don't store timezone information at all and hand back a "naive"
    datetime instead. This treats any such naive value as UTC, which is
    what we always store, so comparisons work the same on every database.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _build_current_user_response(db: Session, user: User) -> CurrentUserResponse:
    """Turn a User database row into the shape we send back to the frontend."""
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_super_admin=user.is_super_admin,
        language_preference=user.language_preference,
        accessible_module_keys=get_accessible_module_keys(db, user.id),
    )


@router.post("/login", response_model=CurrentUserResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> CurrentUserResponse:
    """Check an email/password combination and, if valid, log the user in."""
    # Look up the user by email. We deliberately give the exact same error
    # message below whether the email doesn't exist or the password is
    # wrong, so an attacker can't use the error to guess valid emails.
    user = db.scalar(select(User).where(User.email == payload.email))

    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        _record_login_attempt(db, request, payload.email, user, success=False)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Credentials are correct: issue a fresh pair of tokens and remember
    # the refresh token (hashed) so it can be revoked/rotated later.
    access_token = create_access_token(user.id)
    refresh_token = _issue_and_store_refresh_token(db, user.id)
    _record_login_attempt(db, request, payload.email, user, success=True)
    db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    return _build_current_user_response(db, user)


@router.post("/refresh", response_model=CurrentUserResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> CurrentUserResponse:
    """Use a valid refresh token cookie to issue a brand-new access token.

    This lets a user stay logged in beyond the short access-token
    lifetime, without having to re-enter their password, as long as they
    still have a valid, unused refresh token.
    """
    token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")

    try:
        user_id = decode_token(token, expected_type="refresh")
    except InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again") from error

    # Find the stored (hashed) refresh token record that matches the
    # cookie the browser just sent us.
    stored_tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
    )
    matching_record = next((record for record in stored_tokens if verify_password(token, record.token_hash)), None)

    if matching_record is None or _as_aware_utc(matching_record.expires_at) < datetime.now(timezone.utc):
        # Either we never issued this token, it was already used once
        # before (rotated away), or it has genuinely expired.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or disabled")

    # "Rotate" the refresh token: mark the old one as used, and issue a
    # brand-new one. If this same old token is ever presented again later,
    # that's a sign it may have been stolen and reused by someone else.
    matching_record.revoked = True
    new_access_token = create_access_token(user.id)
    new_refresh_token = _issue_and_store_refresh_token(db, user.id)
    db.commit()

    _set_auth_cookies(response, new_access_token, new_refresh_token)
    return _build_current_user_response(db, user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Log the current user out by revoking their refresh token and clearing cookies."""
    token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if token is not None:
        # Revoke every currently-valid refresh token that matches, so it
        # can never be used again even if someone still has a copy of it.
        for record in db.scalars(select(RefreshToken).where(RefreshToken.revoked.is_(False))):
            if verify_password(token, record.token_hash):
                record.revoked = True
        db.commit()

    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return {"logged_out": True}


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CurrentUserResponse:
    """Tell the frontend who is currently logged in, and which modules they can see."""
    return _build_current_user_response(db, current_user)
