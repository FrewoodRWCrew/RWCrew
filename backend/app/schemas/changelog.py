# Schema of one line of the changelog (the super admin's "Wijzigingen" screen).
# The lines themselves live in changelog.json on the "changelog" git branch,
# see app/landing/changelog.py.

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# A full git commit hash, never a shortened one.
FullCommitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]


class ChangelogEntry(BaseModel):
    """One update, correction or new functionality of the app."""

    # An unknown field is almost certainly a typo in the file, so refuse it.
    model_config = ConfigDict(extra="forbid")

    id: int
    # The numbers of this line in the colleagues' sheet: empty for past work,
    # several when one piece of work solved several points.
    issues: list[str] = Field(default_factory=list)
    # Belgian calendar date: the day the work was finished, or the day it was
    # added/started while it isn't done yet.
    date: Date
    type: Literal["feature", "update", "fix"]
    status: Literal["open", "in_progress", "done"]
    module: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    # Empty until the work is committed; a point can take several commits.
    commits: list[FullCommitSha] = Field(default_factory=list)
