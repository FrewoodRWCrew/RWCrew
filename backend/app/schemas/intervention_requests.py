# Schemas for module-3's two real screens (the manageable "Intervention
# Statuses" lookup list, and the main "Intervention Requests" entity) and
# its custom-roles-with-per-screen-permissions system (screens, roles,
# permissions, users) — identical shapes to app/schemas/masterdata.py's
# equivalents.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

# The fixed set of colours a status can be assigned on the Intervention
# Statuses screen, used to colour every row of the Intervention Requests
# list for that status (see frontend/src/lib/status-colors.ts for the
# matching Tailwind classes — keep both lists in sync).
StatusColor = Literal["red", "orange", "amber", "green", "teal", "blue", "indigo", "purple", "gray"]


class ScreenResponse(BaseModel):
    """One screen registered in the Intervention Requests module."""

    id: int
    key: str
    label: str
    sort_order: int


class ScreenPermissionResponse(BaseModel):
    """One role's permissions on one specific screen, for display in the
    permission-matrix grid (includes the screen's own details so the
    frontend doesn't need a separate lookup).
    """

    screen_id: int
    screen_key: str
    screen_label: str
    can_view: bool
    can_create: bool
    can_edit: bool
    can_delete: bool


class RoleResponse(BaseModel):
    """One Intervention Requests role, with its full permission matrix."""

    id: int
    name: str
    permissions: list[ScreenPermissionResponse]


class RoleCreateRequest(BaseModel):
    """What's sent to create a brand-new, empty (no permissions yet) role."""

    name: str = Field(min_length=1, max_length=255)


class RoleUpdateRequest(BaseModel):
    """What's sent to rename an existing role."""

    name: str = Field(min_length=1, max_length=255)


class ScreenPermissionUpdate(BaseModel):
    """One screen's permissions, as sent when saving a role's whole matrix."""

    screen_id: int
    can_view: bool = False
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False


class SetRolePermissionsRequest(BaseModel):
    """Replace a role's entire permission matrix in one call — the
    complete, current state of every screen's checkboxes, the same
    "send everything" pattern used by the site-wide access checkboxes.
    """

    permissions: list[ScreenPermissionUpdate]


class InterventionRequestsUserSummaryResponse(BaseModel):
    """One user who has access to Intervention Requests, and their current role (if any)."""

    user_id: int
    email: str
    display_name: str
    role_id: int | None
    role_name: str | None


class SetUserRoleRequest(BaseModel):
    """What's sent to assign (or, if null, remove) a user's Intervention Requests role."""

    role_id: int | None


class CreateOrGrantUserRequest(BaseModel):
    """What an Intervention Requests admin sends to give someone access to
    Intervention Requests.

    If no user with this email exists yet, one is created using
    display_name/password (both required in that case). Either way, the
    resulting user is granted access to Intervention Requests ONLY, and
    optionally assigned the given role in the same step.
    """

    email: EmailStr
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8)
    role_id: int | None = None


class MyPermissionsResponse(BaseModel):
    """Which Intervention Requests screens the calling user is allowed to
    view — used by the frontend to decide what to show in the sidebar,
    without it having to know the full permission-checking rules itself.
    """

    viewable_screen_keys: list[str]


class InterventionRequestsTeamResponse(BaseModel):
    """One MasterData team, as shown in the Intervention Requests screen's
    "Ploeg" dropdown — just enough to populate it (id + name), read
    directly from MasterData_team (see app/db/models/team.py) rather than
    MasterData's own TeamResponse, so Intervention Requests users can
    always pick a team regardless of whether they also have a MasterData
    role (see the "teams" endpoint in module_3/router.py).
    """

    id: int
    name: str


class TeamKarUserResponse(BaseModel):
    """One user in the whole app, with whether they're currently a member
    of TeamKar — one row of the TeamKar screen's table.
    """

    user_id: int
    email: str
    display_name: str
    is_member: bool


class SetTeamKarMembersRequest(BaseModel):
    """Replace TeamKar's entire membership with exactly this set of user
    ids — the same "send everything" pattern as SetUserRoleRequest and the
    site-wide access checkboxes.
    """

    user_ids: list[int]


class TeamKarMemberOptionResponse(BaseModel):
    """One current TeamKar member, as shown in the Intervention Requests
    screen's "Team Kar" dropdown — just enough to populate it (id + name).
    Gated by Intervention Requests' own "requests" screen permission, not
    TeamKar's own, the same reasoning as the "teams" endpoint below: a user
    can always pick a Team Kar member here regardless of whether they also
    have the TeamKar screen's permission.
    """

    id: int
    display_name: str


class InterventionRequestsStatusBreakdownItem(BaseModel):
    """One status, with how many intervention requests currently carry it —
    one bar of the KPI dashboard's status breakdown chart.
    """

    status_name: str
    color: StatusColor
    count: int


class InterventionRequestsTeamBreakdownItem(BaseModel):
    """One team/association name, with how many intervention requests were
    logged for it — one bar of the KPI dashboard's team breakdown chart.
    """

    team_name: str
    count: int


class InterventionRequestsDashboardResponse(BaseModel):
    """Aggregate KPI stats for Intervention Requests' landing dashboard
    ("KPI overview").
    """

    total_requests: int
    open_requests: int
    closed_requests: int
    status_breakdown: list[InterventionRequestsStatusBreakdownItem]
    team_breakdown: list[InterventionRequestsTeamBreakdownItem]


class InterventionStatusResponse(BaseModel):
    """One status, as shown on the Intervention Statuses screen."""

    id: int
    name: str
    is_open: bool
    color: StatusColor


class InterventionStatusCreateRequest(BaseModel):
    """What's sent to create a brand-new status."""

    name: str = Field(min_length=1, max_length=255)
    is_open: bool = True
    color: StatusColor = "gray"


class InterventionStatusUpdateRequest(BaseModel):
    """What's sent to update an existing status."""

    name: str = Field(min_length=1, max_length=255)
    is_open: bool = True
    color: StatusColor = "gray"


def _validate_team_reference(team_id: int | None, team_name: str | None) -> None:
    """"Ploeg" is either a real MasterData team (team_id) or, when the
    caller (customer or staff) typed a name that isn't in that list yet, a
    free-text name (team_name) — never both, never neither. Shared by every
    schema below that carries this pair so the rule can't drift between
    the admin and public create/update paths.
    """
    has_team_id = team_id is not None
    has_team_name = bool(team_name and team_name.strip())
    if has_team_id == has_team_name:
        raise ValueError("Exactly one of team_id or team_name must be provided")


class InterventionRequestResponse(BaseModel):
    """One intervention request, as shown on the Intervention Requests screen."""

    id: int
    request_number: str
    submitted_at: datetime
    team_id: int | None
    team_name: str | None
    cart_number: str | None
    question: str
    employee_name: str | None
    employee_phone: str | None
    preferred_delivery_at: datetime | None
    delivery_location: str | None
    zone: str | None
    status_id: int
    handled_by: str | None
    team_cart_user_id: int | None


class InterventionRequestCreateRequest(BaseModel):
    """What's sent to create a brand-new intervention request.

    request_number and submitted_at are never accepted here — both are
    computed by the endpoint itself (see create_intervention_request).
    """

    team_id: int | None = None
    team_name: str | None = Field(default=None, max_length=255)
    cart_number: str | None = Field(default=None, max_length=50)
    question: str = Field(min_length=1)
    employee_name: str | None = Field(default=None, max_length=255)
    employee_phone: str | None = Field(default=None, max_length=50)
    preferred_delivery_at: datetime | None = None
    delivery_location: str | None = Field(default=None, max_length=255)
    zone: str | None = Field(default=None, max_length=100)
    status_id: int
    handled_by: str | None = Field(default=None, max_length=255)
    team_cart_user_id: int | None = None

    @model_validator(mode="after")
    def _check_team_reference(self) -> "InterventionRequestCreateRequest":
        _validate_team_reference(self.team_id, self.team_name)
        return self


class InterventionRequestUpdateRequest(InterventionRequestCreateRequest):
    """What's sent to update an existing intervention request — same shape
    as creating one (request_number/submitted_at stay fixed once set).
    """


class PublicInterventionRequestCreateRequest(BaseModel):
    """What the public (no-login) intervention-request form sends to create
    a request. Deliberately a separate, trimmed-down shape from
    InterventionRequestCreateRequest — status_id/handled_by/
    team_cart_user_id are internal-only fields a customer must never set;
    the public endpoint fills those in itself (see public_router.py).
    """

    team_id: int | None = None
    team_name: str | None = Field(default=None, max_length=255)
    cart_number: str | None = Field(default=None, max_length=50)
    question: str = Field(min_length=1)
    employee_name: str | None = Field(default=None, max_length=255)
    employee_phone: str | None = Field(default=None, max_length=50)
    preferred_delivery_at: datetime | None = None
    delivery_location: str | None = Field(default=None, max_length=255)
    zone: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _check_team_reference(self) -> "PublicInterventionRequestCreateRequest":
        _validate_team_reference(self.team_id, self.team_name)
        return self
