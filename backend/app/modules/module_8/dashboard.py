# Builds the figures for Altsien Select's KPI screen (the module's landing
# page), for one season and limited to the teams the user can see — a
# Kernlid sees the progress of their own teams, the organisation sees all.

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_request_status import AltsienSelectRequestStatus
from app.db.models.altsien_select_special_request import AltsienSelectSpecialRequest
from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.modules.module_8.steps import STEP_DEFINITIONS
from app.schemas.altsien_select import DashboardResponse, StatusBreakdownItem, StepBreakdownItem


def build_dashboard(db: Session, season_id: int | None, team_ids: set[int]) -> DashboardResponse:
    """Wizard progress and special-request figures for the given teams."""
    # Without a season (none chosen yet) there is nothing to count.
    if season_id is None or not team_ids:
        return DashboardResponse(
            season_id=season_id,
            total_teams=len(team_ids),
            completed_teams=0,
            in_progress_teams=0,
            not_started_teams=len(team_ids),
            total_requests=0,
            open_requests=0,
            step_breakdown=[
                StepBreakdownItem(step_key=step.key, label=step.label, completed_count=0) for step in STEP_DEFINITIONS
            ],
            status_breakdown=[],
        )

    # Completed steps per team (steps that no longer exist are ignored).
    step_keys = {step.key for step in STEP_DEFINITIONS}
    done_by_team: dict[int, set[str]] = {}
    for team_id, step_key in db.execute(
        select(AltsienSelectStepProgress.team_id, AltsienSelectStepProgress.step_key).where(
            AltsienSelectStepProgress.season_id == season_id, AltsienSelectStepProgress.team_id.in_(team_ids)
        )
    ).all():
        if step_key in step_keys:
            done_by_team.setdefault(team_id, set()).add(step_key)

    # A team is complete when every step is done, in progress when some are.
    completed_teams = sum(1 for keys in done_by_team.values() if keys == step_keys)
    in_progress_teams = sum(1 for keys in done_by_team.values() if keys and keys != step_keys)
    not_started_teams = len(team_ids) - completed_teams - in_progress_teams

    # How many teams finished each step, in wizard order.
    step_breakdown = [
        StepBreakdownItem(
            step_key=step.key,
            label=step.label,
            completed_count=sum(1 for keys in done_by_team.values() if step.key in keys),
        )
        for step in sorted(STEP_DEFINITIONS, key=lambda step: step.sort_order)
    ]

    # Requests per status — outer join so unused statuses show as 0.
    status_rows = db.execute(
        select(
            AltsienSelectRequestStatus.name,
            AltsienSelectRequestStatus.color,
            AltsienSelectRequestStatus.is_open,
            func.count(AltsienSelectSpecialRequest.id),
        )
        .outerjoin(
            AltsienSelectSpecialRequest,
            (AltsienSelectSpecialRequest.status_id == AltsienSelectRequestStatus.id)
            & (AltsienSelectSpecialRequest.season_id == season_id)
            & (AltsienSelectSpecialRequest.team_id.in_(team_ids)),
        )
        .group_by(
            AltsienSelectRequestStatus.id,
            AltsienSelectRequestStatus.name,
            AltsienSelectRequestStatus.color,
            AltsienSelectRequestStatus.is_open,
            AltsienSelectRequestStatus.sort_order,
        )
        .order_by(AltsienSelectRequestStatus.sort_order, AltsienSelectRequestStatus.name)
    ).all()
    total_requests = sum(row[3] for row in status_rows)
    open_requests = sum(row[3] for row in status_rows if row[2])

    return DashboardResponse(
        season_id=season_id,
        total_teams=len(team_ids),
        completed_teams=completed_teams,
        in_progress_teams=in_progress_teams,
        not_started_teams=not_started_teams,
        total_requests=total_requests,
        open_requests=open_requests,
        step_breakdown=step_breakdown,
        status_breakdown=[
            StatusBreakdownItem(status_name=row[0], color=row[1], count=row[3]) for row in status_rows
        ],
    )
