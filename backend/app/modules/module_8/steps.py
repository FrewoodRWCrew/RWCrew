# This file is the single source of truth for the steps of Altsien Select's
# Ploeg Wizard, in the order they are shown. To add a new step later:
#   1. add one StepDefinition below (optionally with a completion check);
#   2. add its step component to frontend/src/components/module-8/wizard/steps/
#      and register it in that folder's index.ts (an unknown key falls back
#      to a generic placeholder step, so nothing breaks in the meantime);
#   3. add its title/description to the "altsienSelect.steps" translations;
#   4. optionally give it its own section in ploegfiche_pdf.py (otherwise it
#      is listed only in the progress overview).
# Progress is stored per step key in AltsienSelect_step_progress, so no
# database migration is needed for a new step.

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.team_festival import TeamFestival

# A completion check gets (db, season_id, team_id) and returns None when
# the step may be marked as done, or an error message explaining why not.
CompletionCheck = Callable[[Session, int, int], str | None]


@dataclass(frozen=True)
class StepDefinition:
    """Describes one wizard step."""

    # Stable identifier, stored in the progress table — never change it.
    key: str
    # English fallback label (the frontend shows its own translation).
    label: str
    # Position in the wizard (1 = first).
    sort_order: int
    # True while the step's real content is still being built in another
    # module; the wizard then only shows a "coming soon" note and a
    # "mark as done" button.
    placeholder: bool = False
    # Optional rule that must hold before the step can be marked as done.
    completion_check: CompletionCheck | None = None


def selected_festival_ids(db: Session, season_id: int, team_id: int) -> set[int]:
    """The festivals this team is active at in this season (step 1)."""
    return set(
        db.scalars(
            select(TeamFestival.festival_id).where(
                TeamFestival.season_id == season_id, TeamFestival.team_id == team_id
            )
        ).all()
    )


def _check_festivals(db: Session, season_id: int, team_id: int) -> str | None:
    """Step 1 is done once at least one festival is chosen."""
    if not selected_festival_ids(db, season_id, team_id):
        return "Select at least one festival first"
    return None


def _check_afleverlocaties(db: Session, season_id: int, team_id: int) -> str | None:
    """Step 2 is done once every chosen festival has a delivery location."""
    festival_ids = selected_festival_ids(db, season_id, team_id)
    if not festival_ids:
        return "Select at least one festival first"
    planned_count = db.scalar(
        select(func.count())
        .select_from(KarTrackerKarAfleverlocatie)
        .where(
            KarTrackerKarAfleverlocatie.season_id == season_id,
            KarTrackerKarAfleverlocatie.team_id == team_id,
            KarTrackerKarAfleverlocatie.festival_id.in_(festival_ids),
        )
    )
    if planned_count != len(festival_ids):
        return "Every selected festival needs a delivery location"
    return None


STEP_DEFINITIONS: list[StepDefinition] = [
    StepDefinition(key="festivals", label="Festivals", sort_order=1, completion_check=_check_festivals),
    StepDefinition(
        key="afleverlocaties", label="Delivery locations", sort_order=2, completion_check=_check_afleverlocaties
    ),
    # Placeholder until the products module exists.
    StepDefinition(key="products", label="Products", sort_order=3, placeholder=True),
    StepDefinition(key="special_requests", label="Special requests", sort_order=4),
    # Placeholder until the walkie-talkie module exists.
    StepDefinition(key="walkies", label="Walkie-talkies", sort_order=5, placeholder=True),
]

# Quick lookup by key.
STEPS_BY_KEY: dict[str, StepDefinition] = {step.key: step for step in STEP_DEFINITIONS}
