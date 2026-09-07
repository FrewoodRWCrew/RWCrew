# Aggregate KPI stats for Intervention Requests' landing dashboard ("KPI
# overview"). Kept free of FastAPI/routing concerns, mirroring
# app/modules/module_9/masterdata_dashboard.py, so it's easy to unit test
# on its own.
#
# Unlike MasterData's breakdowns (a fixed, pre-existing lookup universe),
# the team breakdown here only lists teams/names that actually appear on
# at least one request — the same idea as TagScan's "top products"
# breakdown, which only lists products that actually have tags.

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.intervention_request import InterventionRequest
from app.db.models.intervention_status import InterventionStatus
from app.db.models.team import Team
from app.schemas.intervention_requests import (
    InterventionRequestsDashboardResponse,
    InterventionRequestsStatusBreakdownItem,
    InterventionRequestsTeamBreakdownItem,
)


def _status_breakdown(db: Session) -> list[InterventionRequestsStatusBreakdownItem]:
    """Count requests per status, ordered by status name. status_id is
    required on every request, so an outer join from InterventionStatus
    naturally zero-fills any status nobody has used yet, without a
    separate "unassigned" bucket.
    """
    rows = db.execute(
        select(InterventionStatus.name, InterventionStatus.color, func.count(InterventionRequest.id))
        .select_from(InterventionStatus)
        .outerjoin(InterventionRequest, InterventionRequest.status_id == InterventionStatus.id)
        .group_by(InterventionStatus.id, InterventionStatus.name, InterventionStatus.color)
        .order_by(InterventionStatus.name)
    ).all()
    return [
        InterventionRequestsStatusBreakdownItem(status_name=name, color=color, count=count)
        for name, color, count in rows
    ]


def _team_breakdown(db: Session) -> list[InterventionRequestsTeamBreakdownItem]:
    """Count requests per team/association name. "Ploeg" is either a real
    MasterData team (team_id) or free text typed by a customer (team_name)
    — never both (see _validate_team_reference) — so the two are counted
    with separate GROUP BYs and merged by name before returning.
    """
    fk_rows = db.execute(
        select(Team.name, func.count(InterventionRequest.id))
        .select_from(InterventionRequest)
        .join(Team, InterventionRequest.team_id == Team.id)
        .group_by(Team.id, Team.name)
    ).all()
    freetext_rows = db.execute(
        select(InterventionRequest.team_name, func.count(InterventionRequest.id))
        .where(InterventionRequest.team_id.is_(None))
        .group_by(InterventionRequest.team_name)
    ).all()

    counts_by_name: dict[str, int] = {}
    for name, count in [*fk_rows, *freetext_rows]:
        counts_by_name[name] = counts_by_name.get(name, 0) + count

    return [
        InterventionRequestsTeamBreakdownItem(team_name=name, count=count)
        for name, count in sorted(counts_by_name.items(), key=lambda item: item[0].lower())
    ]


def build_dashboard_stats(db: Session) -> InterventionRequestsDashboardResponse:
    total_requests = db.scalar(select(func.count()).select_from(InterventionRequest))
    open_requests = db.scalar(
        select(func.count())
        .select_from(InterventionRequest)
        .join(InterventionStatus, InterventionRequest.status_id == InterventionStatus.id)
        .where(InterventionStatus.is_open)
    )
    closed_requests = total_requests - open_requests

    return InterventionRequestsDashboardResponse(
        total_requests=total_requests,
        open_requests=open_requests,
        closed_requests=closed_requests,
        status_breakdown=_status_breakdown(db),
        team_breakdown=_team_breakdown(db),
    )
