# The request/response shapes of the wristband scans, shared by the Scans
# module and the modules with a counter (see app/modules/wristband).

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScanResponse(BaseModel):
    """One received scan message (the desk card and the logs)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    received_at: datetime
    source: str
    status: str
    status_detail: str | None
    event: str | None
    device_id: str | None
    device_name: str | None
    wristband_number: str | None
    first_name: str | None
    last_name: str | None
    team_name: str | None
    team_id: int | None
    profile_name: str | None
    email: str | None
    size: str | None
    person_id: int | None


class ScanLogEntry(ScanResponse):
    """A scan in the logs, with the message as received and where it waits."""

    raw: str | None
    used_by_module: str | None = None
    # The counters where it waits (empty on a "new" scan = no reservation anywhere).
    visible_at: list[str] = []


class TeamSummaryResponse(BaseModel):
    """A MasterData team (the Test-scan form's team dropdown)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    active: bool


class ScannerResponse(BaseModel):
    """A scanner of the wristband company (auto-registered by its first scan)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    device_name: str | None
    label: str | None
    last_seen_at: datetime | None


class ScannerLabelRequest(BaseModel):
    """Our own name for a scanner, e.g. "Balie 1" (empty = none)."""

    label: str | None = Field(default=None, max_length=255)


class WristbandSettingsResponse(BaseModel):
    """The Scans module's Settings screen: the webhook address, whether its
    token is configured and where the JSON files are kept."""

    webhook_path: str
    webhook_token_configured: bool
    webhook_token_generated_at: datetime | None
    webhook_token_last_used_at: datetime | None
    source_folder: str


class WristbandTokenResponse(BaseModel):
    """A freshly generated webhook token: the only time the key is sent."""

    token: str


class TestScanRequest(BaseModel):
    """A Test-scan screen: a message exactly as the wristband company would send it."""

    raw: str = Field(min_length=1, max_length=100_000)


class TestScanResponse(BaseModel):
    """What the processing did with a test message."""

    scan: ScanResponse
    http_status: int
    team_name_matched: str | None
    # The counters where it now waits.
    visible_at: list[str]
