# "Dependencies" are small functions FastAPI runs automatically before an
# endpoint, to fetch or check something every matching endpoint needs. We
# use them here to figure out "who is making this request" and to block
# the request early if that's not allowed.

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_token
from app.db.models.user import User

# The name of the browser cookie that stores the short-lived access token.
ACCESS_TOKEN_COOKIE_NAME = "rwcrew_access_token"
# The name of the browser cookie that stores the longer-lived refresh token.
REFRESH_TOKEN_COOKIE_NAME = "rwcrew_refresh_token"


def _read_bearer_token(request: Request) -> str | None:
    """Return the token from an "Authorization: Bearer <token>" header, if any."""
    header = request.headers.get("authorization")
    if header is None:
        return None
    # The header looks like "Bearer eyJhbGci..."; anything else is ignored.
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Identify the logged-in user making this request, or reject it.

    Reads the access-token cookie the browser automatically sends along
    with the request, checks it's a valid, non-expired token, and looks up
    the matching user. Any endpoint that depends on this function
    automatically requires the caller to be logged in.
    """
    # Read the access token out of the cookies the browser sent us. The
    # cookie always wins, so the web app behaves exactly as before.
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if token is None:
        # No cookie: the smartphone app has no cookie jar, so it sends the
        # same access token in an "Authorization: Bearer <token>" header.
        token = _read_bearer_token(request)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")

    # Verify the token is genuine, unexpired, and of the right type.
    try:
        user_id = decode_token(token, expected_type="access")
    except InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again") from error

    # Look up the user this token belongs to.
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        # Either the account was deleted, or it has since been disabled by
        # an admin — either way, treat this as "not logged in".
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or disabled")

    return user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Like get_current_user, but also requires the super-admin flag.

    Use this on endpoints that only the site-wide super admin may call,
    such as granting or revoking module access for other users.
    """
    if not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return current_user
