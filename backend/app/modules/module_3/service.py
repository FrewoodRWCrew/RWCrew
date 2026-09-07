# Small helpers shared between module-3's login-gated admin router
# (router.py) and its public, no-login router (public_router.py) — kept
# here rather than duplicated in both so "how do we pick a team / a
# request number / the default status" stays defined exactly once.

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_status import InterventionStatus
from app.db.models.team import Team

# The status every new request starts in, whether it was logged by staff or
# submitted through the public form. Confirmed present in the live data
# (seeded alongside the other statuses) rather than assumed.
DEFAULT_NEW_STATUS_NAME = "Nieuw"


def list_teams_for_dropdown(db: Session) -> list[Team]:
    """Every MasterData team, for the "Ploeg" dropdown — read directly from
    MasterData_team so both routers can offer it regardless of the caller's
    MasterData role (or, for the public router, regardless of having any
    role at all).
    """
    return list(db.scalars(select(Team).order_by(Team.name)).all())


def get_default_new_status(db: Session) -> InterventionStatus:
    """The status a brand-new request is created with. Raises if the
    "Nieuw" status has been renamed or deleted from the Intervention
    Statuses screen — that's a configuration problem, not something either
    router should silently paper over.
    """
    new_status = db.scalar(select(InterventionStatus).where(InterventionStatus.name == DEFAULT_NEW_STATUS_NAME))
    if new_status is None:
        # A controlled 500, not a bare exception, so misconfiguration (the
        # "Nieuw" status renamed/deleted) surfaces as a normal API error
        # response rather than an unhandled crash.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'No InterventionStatus named "{DEFAULT_NEW_STATUS_NAME}" exists.',
        )
    return new_status


def generate_request_number(db: Session) -> str:
    """Build this request's "Aanvraagnummer": "IA" + the last 2 digits of
    the current year + "_" + a per-year sequence number, e.g. "IA26_0001".
    The highest existing sequence is used so deleting a request never makes
    its number available again. PostgreSQL's transaction advisory lock
    serializes concurrent allocations for the same year.
    """
    year_suffix = str(datetime.now(timezone.utc).year)[-2:]
    prefix = f"IA{year_suffix}_"
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:prefix))"), {"prefix": prefix})

    request_numbers = db.scalars(
        select(InterventionRequest.request_number)
        .where(InterventionRequest.request_number.like(f"{prefix}%"))
        .order_by(desc(InterventionRequest.request_number))
        .with_for_update()
    )
    existing_sequences = []
    for request_number in request_numbers:
        try:
            existing_sequences.append(int(request_number[len(prefix) :]))
        except ValueError:
            continue

    next_sequence = (max(existing_sequences) if existing_sequences else 0) + 1
    return f"{prefix}{next_sequence:04d}"
