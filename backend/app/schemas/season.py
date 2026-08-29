# Schemas describing "season" master data, used by the super admin's
# Master Data screen.

from pydantic import BaseModel, Field


class SeasonCreateRequest(BaseModel):
    """What an admin sends us to create a brand-new season."""

    name: str = Field(min_length=1, max_length=255)


class SeasonUpdateRequest(BaseModel):
    """What an admin sends us to rename an existing season."""

    name: str = Field(min_length=1, max_length=255)


class SeasonResponse(BaseModel):
    """One season, as shown in the Master Data table."""

    id: int
    name: str
