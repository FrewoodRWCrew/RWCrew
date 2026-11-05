# "Schemas" describe the exact shape of the data that goes into and out of
# our API endpoints. FastAPI uses these to validate incoming requests
# automatically (e.g. rejecting a login attempt with no password) and to
# document the API.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """What the frontend must send us to log a user in."""

    email: EmailStr
    password: str
    # Which part of the app the login form is on, for the login history:
    # "web" (the website) or "pwa" (the phone section /m). Optional, so a
    # client that doesn't send it counts as the website.
    client: Literal["web", "pwa"] = "web"


class TokenLoginRequest(BaseModel):
    """The Raspberry Pi app's login (POST /api/auth/token): same email and
    password as the website, recorded as client "pi" in the login history."""

    email: EmailStr
    password: str
    # Read by the login history (same field name as LoginRequest).
    client: Literal["pi"] = "pi"


class TokenRefreshRequest(BaseModel):
    """The Raspberry Pi app sends its refresh token in the body (it has no cookies)."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """What a logged-in user sends to change their own password."""

    current_password: str
    new_password: str = Field(min_length=8)


class CurrentUserResponse(BaseModel):
    """What we tell the frontend about the currently logged-in user."""

    id: int
    email: str
    display_name: str
    is_super_admin: bool
    language_preference: str
    # The "key" of every module (e.g. "module-3") this user is currently
    # allowed to open, so the frontend knows which tiles to show.
    accessible_module_keys: list[str]


class TokenResponse(BaseModel):
    """The Raspberry Pi app's tokens (it sends the access token as
    "Authorization: Bearer"), with who is logged in."""

    access_token: str
    refresh_token: str
    # When the access token stops working (renew it before) and when the whole
    # login session ends (then the password must be entered again).
    access_expires_at: datetime
    session_expires_at: datetime
    user: CurrentUserResponse
