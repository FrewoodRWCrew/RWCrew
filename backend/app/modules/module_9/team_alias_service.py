# A team's aliases: other names it goes by in outside applications (see
# app/db/models/team_alias.py). The only writer of MasterData_team_alias, used
# by the team endpoints and the Teams XLSX import. An alias may belong to only
# one team and may not be another team's name, so a name always leads to
# exactly one team. Never commits.

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models.team import Team
from app.db.models.team_alias import TeamAlias

# The separator between aliases in the XLSX column.
XLSX_SEPARATOR = ";"


def normalize_name(name: str) -> str:
    """A team name or alias as compared: lowercase, single spaces."""
    return " ".join(name.lower().split())


def clean_aliases(aliases: list[str], own_name: str | None) -> list[str]:
    """The aliases trimmed, without empty ones, doubles and the team's own name."""
    cleaned: dict[str, str] = {}
    for alias in aliases:
        key = normalize_name(alias)
        if key and key != normalize_name(own_name or ""):
            cleaned.setdefault(key, " ".join(alias.split()))
    return list(cleaned.values())


def check_aliases(db: Session, aliases: list[str], team_id: int | None) -> None:
    """Refuse (ValueError) an alias that's another team's alias or name.
    `team_id` is the team they're for (None = a new team)."""
    for alias in aliases:
        key = normalize_name(alias)
        taken = db.scalar(select(TeamAlias).where(TeamAlias.alias_key == key))
        if taken is not None and taken.team_id != team_id:
            raise ValueError(f'The alias "{alias}" is already used by team "{db.get(Team, taken.team_id).name}"')
        named = db.scalar(select(Team).where(func.lower(Team.name) == key))
        if named is not None and named.id != team_id:
            raise ValueError(f'The alias "{alias}" is the name of team "{named.name}"')


def replace_aliases(db: Session, team_id: int, aliases: list[str]) -> None:
    """Make the team's aliases match this list exactly."""
    db.execute(delete(TeamAlias).where(TeamAlias.team_id == team_id))
    for alias in aliases:
        db.add(TeamAlias(team_id=team_id, alias=alias, alias_key=normalize_name(alias)))


def aliases_of(db: Session, team_id: int) -> list[str]:
    """The team's aliases, sorted."""
    return sorted(db.scalars(select(TeamAlias.alias).where(TeamAlias.team_id == team_id)).all(), key=str.lower)


def team_by_alias(db: Session, name: str) -> Team | None:
    """The team with this alias, ignoring case and extra spaces."""
    team_id = db.scalar(select(TeamAlias.team_id).where(TeamAlias.alias_key == normalize_name(name)))
    return db.get(Team, team_id) if team_id is not None else None
