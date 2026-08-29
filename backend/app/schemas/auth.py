# "Schemas" describe the exact shape of the data that goes into and out of
# our API endpoints. FastAPI uses these to validate incoming requests
# automatically (e.g. rejecting a login attempt with no password) and to
# document the API.

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """What the frontend must send us to log a user in."""

    email: EmailStr
    password: str


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
