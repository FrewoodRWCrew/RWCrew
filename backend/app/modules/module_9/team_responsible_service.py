# Shared logic for "Ploegverantwoordelijken" (MasterData_team_responsible):
# used by MasterData's own screen (module_9/router.py) and by Altsien
# Select's wizard step (module_8/router.py), so both write the rows the
# exact same way — the same idea as module_2/plan_kar_service.py.

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.team_responsible import TeamResponsible

# The Altsien Select wizard step that needs at least one responsible person
# (see module_8/steps.py) — kept here so every place that removes one can
# un-mark that step.
RESPONSIBLES_STEP_KEY = "ploegverantwoordelijken"


def apply_team_responsible_fields(
    team_responsible: TeamResponsible, *, name: str, email: str, phone: str, comments: str | None
) -> None:
    """Copy the contact details onto a row, trimmed; blank comments are
    stored as "no comments" rather than an empty string.
    """
    team_responsible.name = name.strip()
    team_responsible.email = email.strip()
    team_responsible.phone = phone.strip()
    team_responsible.comments = (comments or "").strip() or None


def list_team_responsibles(db: Session, season_id: int, team_id: int) -> list[TeamResponsible]:
    """One team's responsible people in one season, sorted by name."""
    return list(
        db.scalars(
            select(TeamResponsible)
            .where(TeamResponsible.season_id == season_id, TeamResponsible.team_id == team_id)
            .order_by(TeamResponsible.name, TeamResponsible.id)
        ).all()
    )

def reopen_step_if_no_responsibles(db: Session, season_id: int, team_id: int) -> None:
    """After a responsible person left a team + season (deleted, or moved to
    another team/season), un-mark Altsien Select's "Ploegverantwoordelijken"
    step there once nobody is left, since its completion rule no longer
    holds. Pending changes are flushed first; the caller commits.
    """
    db.flush()
    if list_team_responsibles(db, season_id, team_id):
        return
    db.execute(
        delete(AltsienSelectStepProgress).where(
            AltsienSelectStepProgress.season_id == season_id,
            AltsienSelectStepProgress.team_id == team_id,
            AltsienSelectStepProgress.step_key == RESPONSIBLES_STEP_KEY,
        )
    )
