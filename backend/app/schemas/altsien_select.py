# Schemas for Altsien Select (module-8): the Ploeg Wizard, the Ploegfiche,
# special requests with their statuses, and the KPI dashboard. The
# custom-roles shapes (screens, roles, permissions, users) are identical to
# module 3's, so they are re-used from app/schemas/intervention_requests.py
# instead of being copied a third time.

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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
from app.schemas.masterdata import TeamResponsibleResponse


# --- Wizard steps ---------------------------------------------------------


class StepResponse(BaseModel):
    """One step of the Ploeg Wizard (see app/modules/module_8/steps.py)."""

    key: str
    label: str
    sort_order: int
    placeholder: bool
    # Whether the step offers "copy from last season" (see previous_season.py).
    copy_from_previous: bool = False


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


class TeamKarResponse(BaseModel):
    """One kar from KarManagement (module-2) currently assigned to the team.
    The kar's cijfercode is not stored yet; it is a placeholder on screen.
    """

    id: int
    kar_nummer: str
    transport_type: str | None


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
    """One delivery location offered in step 2's dropdowns, with its
    coordinates so the chosen locations can be pinned on the step's map.
    """

    id: int
    name: str
    description: str | None
    latitude: float | None
    longitude: float | None


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

    # Trim before validating, so "   " counts as empty instead of passing
    # min_length and being stored as "" once the service trims it.
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=5000)


class ResponsibleWriteRequest(BaseModel):
    """What the wizard sends to add or change a responsible person — the
    team and season come from the URL. Everything but comments is required.
    """

    # Trim before validating, so "   " counts as empty instead of passing
    # min_length and being stored as "" once the service trims it.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    phone: str = Field(min_length=1, max_length=50)
    comments: str | None = Field(default=None, max_length=5000)


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
    # The karren KarManagement assigned to the team (not season-scoped).
    karren: list[TeamKarResponse]
    steps: list[StepResponse]
    progress: list[StepProgressResponse]
    festivals: list[FestivalChoiceResponse]
    afleverlocaties: list[AfleverlocatieOptionResponse]
    requests: list[SpecialRequestResponse]
    # The team's responsible people ("Ploegverantwoordelijken") this season.
    responsibles: list[TeamResponsibleResponse]


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


# --- Copy from last season ------------------------------------------------


class PreviousSeasonLineResponse(BaseModel):
    """One of last season's values for a step (see previous_season.py)."""

    key: str
    label: str
    detail: str | None
    target: str | None
    current_detail: str | None
    already_present: bool
    unavailable_reason: str | None


class PreviousSeasonResponse(BaseModel):
    """Last season's values for one step of one team; no season (and no
    lines) when there is no earlier season.
    """

    previous_season_id: int | None
    previous_season_name: str | None
    lines: list[PreviousSeasonLineResponse]


class CopyPreviousRequest(BaseModel):
    """Which of last season's lines to copy into this season."""

    season_id: int
    line_keys: list[str]


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
