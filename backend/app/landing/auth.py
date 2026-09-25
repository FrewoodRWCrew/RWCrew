# This file defines the login-related API endpoints: logging in, getting
# a fresh access token via the refresh token, logging out, and asking
# "who am I currently logged in as".

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
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
from app.schemas.auth import ChangePasswordRequest, CurrentUserResponse, LoginRequest
from app.shared.access import get_accessible_module_keys

# Every route in this file will automatically start with "/api/auth".
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _seconds_until(moment: datetime) -> int:
    """Whole seconds from now until `moment` (negative once it has passed)."""
    return int((_as_aware_utc(moment) - datetime.now(timezone.utc)).total_seconds())


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, session_expires_at: datetime) -> None:
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
        max_age=max(0, min(settings.access_token_minutes * 60, _seconds_until(session_expires_at))),
        path="/",
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=max(0, _seconds_until(session_expires_at)),
        path="/",
    )


def _issue_and_store_refresh_token(db: Session, user_id: int, session_expires_at: datetime | None = None) -> str:
    """Create a new refresh token and remember its hash in the database.

    Pass `session_expires_at` (the old token's expiry) when rotating, so the
    login session keeps its original end; omit it for a fresh login.
    """
    if session_expires_at is None:
        session_expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_max_hours)
    refresh_token = create_refresh_token(user_id, session_expires_at)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_password(refresh_token),
            expires_at=session_expires_at,
        )
    )
    return refresh_token


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    """End every login session of this user: none of their refresh tokens can
    be used to renew a session any more (their access tokens die within minutes)."""
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))


def _record_login_attempt(
    db: Session, request: Request, email: str, user: User | None, success: bool, source: str = "web"
) -> None:
    """Remember one login attempt (successful or not) for the admin
    "Login History" screen, so there's a record of who is using the tool
    and when — including attempts that failed. `source` says whether it came
    from the web app ("web") or the smartphone app ("mobile").
    """
    db.add(
        LoginHistory(
            user_id=user.id if user is not None else None,
            email_attempted=email,
            success=success,
            ip_address=request.client.host if request.client is not None else None,
            source=source,
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
    # The session ends a fixed number of hours from now, whatever happens.
    session_end = datetime.now(timezone.utc) + timedelta(hours=settings.session_max_hours)
    access_token = create_access_token(user.id, session_end)
    refresh_token = _issue_and_store_refresh_token(db, user.id, session_end)
    _record_login_attempt(db, request, payload.email, user, success=True)
    db.commit()

    _set_auth_cookies(response, access_token, refresh_token, session_end)
    return _build_current_user_response(db, user)


@router.post("/refresh", response_model=CurrentUserResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> CurrentUserResponse:
    """Use a valid refresh token cookie to issue a brand-new access token.

    This lets a user stay logged in beyond the short access-token
    lifetime, without having to re-enter their password, as long as they
    still have a valid, unused refresh token and the login session (at most
    `session_max_hours` since the password was entered) hasn't ended.
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
    # The new tokens keep the ORIGINAL session end: renewing never extends
    # the login, so the user must re-enter their password after the limit.
    session_end = _as_aware_utc(matching_record.expires_at)
    new_access_token = create_access_token(user.id, session_end)
    new_refresh_token = _issue_and_store_refresh_token(db, user.id, session_end)
    db.commit()

    _set_auth_cookies(response, new_access_token, new_refresh_token, session_end)
    return _build_current_user_response(db, user)


@router.post("/change-password", response_model=CurrentUserResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    """Let a logged-in user change their own password.

    Their other sessions (other browsers, the phone) are ended; this browser
    gets fresh tokens so the user isn't logged out, but the original session
    end is kept, so changing the password never extends the 6-hour limit.
    """
    # The current password must be re-entered, so a hijacked open session
    # can't be used to lock the real owner out.
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

    # Keep this session's original end: read it from the refresh cookie's record.
    session_end = datetime.now(timezone.utc) + timedelta(hours=settings.session_max_hours)
    cookie_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if cookie_token is not None:
        for record in db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == current_user.id, RefreshToken.revoked.is_(False))
        ):
            if verify_password(cookie_token, record.token_hash):
                session_end = _as_aware_utc(record.expires_at)
                break

    current_user.hashed_password = hash_password(payload.new_password)
    revoke_all_refresh_tokens(db, current_user.id)
    new_access_token = create_access_token(current_user.id, session_end)
    new_refresh_token = _issue_and_store_refresh_token(db, current_user.id, session_end)
    db.commit()

    _set_auth_cookies(response, new_access_token, new_refresh_token, session_end)
    return _build_current_user_response(db, current_user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Log the current user out by revoking their refresh token and clearing cookies."""
    token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if token is not None:
        try:
            user_id = decode_token(token, expected_type="refresh")
        except InvalidTokenError:
            # Garbage or expired cookie: nothing to revoke, just clear it below.
            user_id = None
        if user_id is not None:
            # Only this user's still-valid tokens can match. (Checking every
            # user's tokens made logout take many seconds, because each
            # comparison is a deliberately slow password-style hash.)
            # Newest first, and stop at the match: a token hash is unique.
            candidates = db.scalars(
                select(RefreshToken)
                .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
                .order_by(RefreshToken.created_at.desc())
            )
            for record in candidates:
                if verify_password(token, record.token_hash):
                    # Revoke it so it can never be used again even if
                    # someone still has a copy of it.
                    record.revoked = True
                    break
            db.commit()

    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return {"logged_out": True}


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CurrentUserResponse:
    """Tell the frontend who is currently logged in, and which modules they can see."""
    return _build_current_user_response(db, current_user)
