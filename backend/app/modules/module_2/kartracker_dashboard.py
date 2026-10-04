# Aggregate KPI stats for KarTracker's landing dashboard ("KPI Overview").
# Kept free of FastAPI/routing concerns, mirroring
# app/modules/module_3/intervention_requests_dashboard.py, so it's easy to
# unit test on its own.
#
# Three parts:
# - the fleet (KarTracker_karren): totals, per status, per team;
# - the movement log (KarTracker_kar_actions): last 7 days, and per day over
#   the last 14 days;
# - "Plan a kar" (KarTracker_kar_afleverlocaties) for one season: how many
#   (active team, active festival) pairs already have a delivery location.
#   Only filled in when a season is given.

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timezone import BELGIAN_TZ, to_belgian
from app.db.models.festival import Festival
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_action import KarTrackerKarAction
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.team import Team
from app.schemas.kartracker import (
    KarTrackerDashboardDailyMovementItem,
    KarTrackerDashboardFestivalPlanItem,
    KarTrackerDashboardResponse,
    KarTrackerDashboardStatusBreakdownItem,
    KarTrackerDashboardTeamBreakdownItem,
)

# How far back the "movements" tile and the per-day chart look.
MOVEMENT_TILE_DAYS = 7
MOVEMENT_CHART_DAYS = 14


def _status_breakdown(db: Session) -> list[KarTrackerDashboardStatusBreakdownItem]:
    """Count karren per status, ordered by status name. An outer join from
    the status lookup zero-fills statuses no kar currently has.
    """
    rows = db.execute(
        select(KarTrackerKarStatus.name, func.count(KarTrackerKar.id))
        .select_from(KarTrackerKarStatus)
        .outerjoin(KarTrackerKar, KarTrackerKar.status_id == KarTrackerKarStatus.id)
        .group_by(KarTrackerKarStatus.id, KarTrackerKarStatus.name)
        .order_by(KarTrackerKarStatus.name)
    ).all()
    return [KarTrackerDashboardStatusBreakdownItem(status_name=name, count=count) for name, count in rows]


def _team_breakdown(db: Session) -> list[KarTrackerDashboardTeamBreakdownItem]:
    """Count karren per team — only teams that actually have a kar, ordered
    by name. Karren without a team are reported separately (see the tiles),
    so they don't appear here.
    """
    rows = db.execute(
        select(Team.name, func.count(KarTrackerKar.id))
        .select_from(KarTrackerKar)
        .join(Team, KarTrackerKar.team_id == Team.id)
        .group_by(Team.id, Team.name)
        .order_by(Team.name)
    ).all()
    return [KarTrackerDashboardTeamBreakdownItem(team_name=name, count=count) for name, count in rows]


def _as_utc(moment: datetime) -> datetime:
    """SQLite hands timezone-aware columns back without a timezone; they are
    always stored in UTC, so tag them as such before comparing.
    """
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _movements(db: Session, now: datetime) -> tuple[int, list[KarTrackerDashboardDailyMovementItem]]:
    """The number of movements in the last 7 days, plus one bucket per
    Belgian calendar day for the last 14 days (today included, oldest first, zero-filled).
    Bucketing happens in Python so it works the same on SQLite and Postgres.
    """
    # Days are Belgian calendar days: the chart starts at Belgian midnight.
    today = to_belgian(now).date()
    first_day = today - timedelta(days=MOVEMENT_CHART_DAYS - 1)
    chart_start = datetime.combine(first_day, datetime.min.time(), tzinfo=BELGIAN_TZ)
    tile_start = now - timedelta(days=MOVEMENT_TILE_DAYS)

    recorded = [
        _as_utc(moment)
        for moment in db.scalars(
            select(KarTrackerKarAction.recorded_at).where(
                # In UTC: SQLite (tests) drops a parameter's timezone.
                KarTrackerKarAction.recorded_at >= min(chart_start, tile_start).astimezone(timezone.utc)
            )
        ).all()
    ]

    # Tile: a rolling 7×24h window.
    last_week = sum(1 for moment in recorded if moment >= tile_start)

    # Chart: count per calendar day, then emit every day even when empty.
    counts_by_day: dict[date, int] = {}
    for moment in recorded:
        day = to_belgian(moment).date()
        if first_day <= day <= today:
            counts_by_day[day] = counts_by_day.get(day, 0) + 1
    per_day = [
        KarTrackerDashboardDailyMovementItem(day=day, count=counts_by_day.get(day, 0))
        for day in (first_day + timedelta(days=offset) for offset in range(MOVEMENT_CHART_DAYS))
    ]
    return last_week, per_day


def _plan_kar(db: Session, season_id: int) -> tuple[int, list[KarTrackerDashboardFestivalPlanItem]]:
    """"Plan a kar" coverage for one season: (number of active teams,
    per-festival planned-team counts). Only assignments whose team and
    festival are both still active are counted, so the totals stay
    comparable with "active teams × active festivals".
    """
    active_team_count = db.scalar(select(func.count()).select_from(Team).where(Team.active.is_(True))) or 0

    # Every active festival of the season, earliest first (same order as the
    # Plan a kar and Kar Planning screens), with its number of planned teams.
    rows = db.execute(
        select(Festival.name, func.count(Team.id))
        .select_from(Festival)
        .outerjoin(
            KarTrackerKarAfleverlocatie,
            (KarTrackerKarAfleverlocatie.festival_id == Festival.id)
            & (KarTrackerKarAfleverlocatie.season_id == season_id),
        )
        .outerjoin(Team, (Team.id == KarTrackerKarAfleverlocatie.team_id) & Team.active.is_(True))
        .where(Festival.season_id == season_id, Festival.active.is_(True))
        .group_by(Festival.id, Festival.name, Festival.start_date)
        .order_by(Festival.start_date, Festival.name)
    ).all()

    per_festival = [
        KarTrackerDashboardFestivalPlanItem(festival_name=name, planned_teams=count) for name, count in rows
    ]
    return active_team_count, per_festival


def build_dashboard_stats(
    db: Session, season_id: int | None, now: datetime | None = None
) -> KarTrackerDashboardResponse:
    """All KPI figures for the landing page. `now` can be passed in by tests
    to pin the movement windows; `season_id` None leaves the Plan a kar
    figures empty.
    """
    now = now or datetime.now(timezone.utc)

    # Fleet totals: team_id is optional, so "without a team" is the rest.
    total_karren = db.scalar(select(func.count()).select_from(KarTrackerKar)) or 0
    karren_with_team = (
        db.scalar(select(func.count()).select_from(KarTrackerKar).where(KarTrackerKar.team_id.is_not(None))) or 0
    )

    movements_last_week, movements_per_day = _movements(db, now)

    # Plan a kar figures only exist for a chosen season.
    planned_pairs: int | None = None
    expected_pairs: int | None = None
    festival_plan_breakdown: list[KarTrackerDashboardFestivalPlanItem] | None = None
    active_team_count: int | None = None
    if season_id is not None:
        active_team_count, festival_plan_breakdown = _plan_kar(db, season_id)
        # Expected = every active team at every active festival of the season.
        planned_pairs = sum(item.planned_teams for item in festival_plan_breakdown)
        expected_pairs = active_team_count * len(festival_plan_breakdown)

    return KarTrackerDashboardResponse(
        total_karren=total_karren,
        karren_with_team=karren_with_team,
        karren_without_team=total_karren - karren_with_team,
        movements_last_7_days=movements_last_week,
        status_breakdown=_status_breakdown(db),
        team_breakdown=_team_breakdown(db),
        movements_per_day=movements_per_day,
        season_id=season_id,
        active_teams=active_team_count,
        plan_kar_planned=planned_pairs,
        plan_kar_expected=expected_pairs,
        festival_plan_breakdown=festival_plan_breakdown,
    )
