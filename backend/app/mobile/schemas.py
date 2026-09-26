# The request/response shapes of the smartphone app's API. They live here
# (not in app/schemas/) so all phone-specific code stays in this package —
# see CLAUDE.md, "Mobile app (mobile/)".

from pydantic import BaseModel

from app.schemas.auth import CurrentUserResponse
from app.schemas.intervention_requests import (
    InterventionRequestsTeamResponse,
    InterventionStatusResponse,
    TeamKarMemberOptionResponse,
)


class MobileRefreshRequest(BaseModel):
    """What the phone sends to swap its refresh token for a fresh pair.

    The web app keeps this token in a cookie; the phone has no cookie jar,
    so it stores the token in the device's secure storage and sends it here.
    """

    refresh_token: str


class MobileModule3PermissionsResponse(BaseModel):
    """What the calling user may do on the phone's Intervention Requests
    "Akties" screen, so the app only shows buttons the web roles allow.
    (There is no delete flag: deleting is web-only.)
    """

    can_view_requests: bool
    can_create_requests: bool
    can_edit_requests: bool


class MobileModule3LookupsResponse(BaseModel):
    """Every dropdown list the request form needs, in one round trip."""

    statuses: list[InterventionStatusResponse]
    teams: list[InterventionRequestsTeamResponse]
    teamkar_members: list[TeamKarMemberOptionResponse]


class MobileTokenResponse(BaseModel):
    """The tokens (plus who the user is) handed back after login/refresh."""

    access_token: str
    refresh_token: str
    # Always "bearer": the phone sends the access token as
    # "Authorization: Bearer <access_token>" on every later request.
    token_type: str = "bearer"
    # How many seconds the access token stays valid, so the app knows when
    # to refresh it before it expires.
    expires_in: int
    user: CurrentUserResponse
