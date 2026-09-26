# Schemas for Altsien Select (module-8): the Ploeg Wizard, the Ploegfiche,
# special requests with their statuses, and the KPI dashboard. The
# custom-roles shapes (screens, roles, permissions, users) are identical to
# module 3's, so they are re-used from app/schemas/intervention_requests.py
# instead of being copied a third time.

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.intervention_requests import (  # noqa: F401  (re-exported for the router)
    CreateOrGrantUserRequest,
    InterventionRequestsUserSummaryResponse as UserSummaryResponse,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    StatusColor,
)


# --- Wizard steps ---------------------------------------------------------


class StepResponse(BaseModel):
    """One step of the Ploeg Wizard (see app/modules/module_8/steps.py)."""

    key: str
    label: str
    sort_order: int
    placeholder: bool


class StepProgressResponse(BaseModel):
    """One completed step for a team, with who/when."""

    step_key: str
    completed_at: datetime
    completed_by_name: str | None


# --- Teams ----------------------------------------------------------------


class TeamSummaryResponse(BaseModel):
    """One team in the user's scope, with how far its wizard is."""

    team_id: int
    team_name: str
    completed_step_keys: list[str]
    open_request_count: int


class TeamInfoResponse(BaseModel):
    """The team's master data, shown at the top of the Ploegfiche."""

    id: int
    name: str
    location: str | None
    delivery_method: str | None
    description: str | None
    kernleden: list[str]


class FestivalChoiceResponse(BaseModel):
    """One active festival of the season, whether the team is active there,
    and (if so) the delivery location chosen for it.
    """

    festival_id: int
    festival_name: str
    start_date: date
    end_date: date
    selected: bool
    afleverlocatie_id: int | None
    afleverlocatie_name: str | None
    afleverlocatie_description: str | None


class AfleverlocatieOptionResponse(BaseModel):
    """One delivery location offered in step 2's dropdowns."""

    id: int
    name: str
    description: str | None


# --- Special requests -----------------------------------------------------


class SpecialRequestResponse(BaseModel):
    """One special request, with its status details flattened in."""

    id: int
    season_id: int
    team_id: int
    team_name: str
    text: str
    status_id: int
    status_name: str
    status_color: StatusColor
    status_is_open: bool
    organisation_note: str | None
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime
    # Whether the calling user may still change/delete it from the wizard
    # (only while it is in the first status and the season is editable).
    editable_by_me: bool


class SpecialRequestWriteRequest(BaseModel):
    """What the wizard sends to add or change a request."""

    text: str = Field(min_length=1, max_length=5000)


class SpecialRequestFollowUpRequest(BaseModel):
    """What the organisation sends on the follow-up screen."""

    status_id: int
    organisation_note: str | None = Field(default=None, max_length=5000)


# --- Full team state (wizard + Ploegfiche) --------------------------------


class TeamStateResponse(BaseModel):
    """Everything chosen for one team in one season — the wizard's data
    and, as-is, the Ploegfiche.
    """

    season_id: int
    season_name: str
    season_open: bool
    # Whether the calling user may still change these choices.
    can_edit: bool
    team: TeamInfoResponse
    steps: list[StepResponse]
    progress: list[StepProgressResponse]
    festivals: list[FestivalChoiceResponse]
    afleverlocaties: list[AfleverlocatieOptionResponse]
    requests: list[SpecialRequestResponse]


class SaveFestivalsRequest(BaseModel):
    """Step 1: the complete list of festivals the team is active at."""

    season_id: int
    festival_ids: list[int]


class AfleverlocatieChoice(BaseModel):
    """Step 2: one festival's delivery location (null clears it)."""

    festival_id: int
    afleverlocatie_id: int | None = None


class SaveAfleverlocatiesRequest(BaseModel):
    """Step 2: the delivery location for each selected festival."""

    season_id: int
    rows: list[AfleverlocatieChoice]


# --- Request statuses (master data) ---------------------------------------


class RequestStatusResponse(BaseModel):
    """One special-request status."""

    id: int
    name: str
    is_open: bool
    color: StatusColor
    sort_order: int


class RequestStatusWriteRequest(BaseModel):
    """What's sent to create or update a status."""

    name: str = Field(min_length=1, max_length=255)
    is_open: bool = True
    color: StatusColor = "gray"
    sort_order: int = 0


# --- KPI dashboard --------------------------------------------------------


class StepBreakdownItem(BaseModel):
    """How many teams completed one wizard step."""

    step_key: str
    label: str
    completed_count: int


class StatusBreakdownItem(BaseModel):
    """How many special requests are in one status."""

    status_name: str
    color: StatusColor
    count: int


class DashboardResponse(BaseModel):
    """The KPI screen's figures for one season, limited to the user's teams."""

    season_id: int | None
    total_teams: int
    completed_teams: int
    in_progress_teams: int
    not_started_teams: int
    total_requests: int
    open_requests: int
    step_breakdown: list[StepBreakdownItem]
    status_breakdown: list[StatusBreakdownItem]
