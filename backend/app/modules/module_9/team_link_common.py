# Shared pieces of the "team link" bulk imports on MasterData's Data
# Upload/Download screen (tasks, Kernleden and festivals per team, and
# Ploegverantwoordelijken): finding a team or season by name, and adding a
# link row only when it doesn't exist yet.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.season import Season
from app.db.models.team import Team
from app.modules.module_9.xlsx_common import ImportOutcome


def link_key(*parts: str | None) -> str | None:
    """How a row reads in the results, e.g. "Team A — Opbouw"; None when blank."""
    present = [part for part in parts if part]
    return " — ".join(present) or None


def resolve_team(db: Session, team_name: str | None) -> Team:
    """The team with this name (ignoring case) — required."""
    if team_name is None:
        raise ValueError("team_name is required")
    team = db.scalar(select(Team).where(Team.name.ilike(team_name)))
    if team is None:
        raise ValueError(f'Team "{team_name}" not found')
    return team


def resolve_season(db: Session, season_name: str | None) -> Season:
    """The season with this name (ignoring case) — required."""
    if season_name is None:
        raise ValueError("season_name is required")
    season = db.scalar(select(Season).where(Season.name.ilike(season_name)))
    if season is None:
        raise ValueError(f'Year "{season_name}" not found')
    return season


def add_link(db: Session, model: type, **values: int) -> ImportOutcome:
    """Add one link row unless an identical one exists ("unchanged")."""
    conditions = [getattr(model, column) == value for column, value in values.items()]
    if db.scalar(select(model.id).where(*conditions)) is not None:
        return "unchanged"
    db.add(model(**values))
    # Flushed now, so a second identical row in the same file is "unchanged" too.
    db.flush()
    return "created"
