# Read-side helpers shared by Altsien Select's router, dashboard and PDF:
# turning the stored rows (festivals, Plan a kar locations, step progress,
# special requests) into the response shapes the wizard, the Ploegfiche
# and the PDF all show.

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.altsien_select_request_status import AltsienSelectRequestStatus
from app.db.models.altsien_select_special_request import AltsienSelectSpecialRequest
from app.db.models.altsien_select_step_progress import AltsienSelectStepProgress
from app.db.models.delivery_method import DeliveryMethod
from app.db.models.festival import Festival
from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_festival import TeamFestival
from app.db.models.team_kernlid import TeamKernlid
from app.db.models.team_location import TeamLocation
from app.db.models.user import User
from app.modules.module_8.deps import season_is_editable_for
from app.modules.module_8.steps import STEP_DEFINITIONS, selected_festival_ids
from app.schemas.altsien_select import (
    AfleverlocatieOptionResponse,
    FestivalChoiceResponse,
    SpecialRequestResponse,
    StepProgressResponse,
    StepResponse,
    TeamInfoResponse,
    TeamStateResponse,
    TeamSummaryResponse,
)


def list_steps() -> list[StepResponse]:
    """The wizard's steps, in order."""
    return [
        StepResponse(key=step.key, label=step.label, sort_order=step.sort_order, placeholder=step.placeholder)
        for step in sorted(STEP_DEFINITIONS, key=lambda step: step.sort_order)
    ]


def first_request_status(db: Session) -> AltsienSelectRequestStatus | None:
    """The status a new request starts in: the lowest sort order (New)."""
    return db.scalar(
        select(AltsienSelectRequestStatus).order_by(
            AltsienSelectRequestStatus.sort_order, AltsienSelectRequestStatus.id
        )
    )


def build_request_responses(
    db: Session, user: User, requests: list[AltsienSelectSpecialRequest], season_editable: bool
) -> list[SpecialRequestResponse]:
    """Turn request rows into responses, with status/team/author names.
    A request stays editable from the wizard only while it is still in the
    first status and the season can still be edited by this user.
    """
    if not requests:
        return []

    first_status = first_request_status(db)
    statuses = {row.id: row for row in db.scalars(select(AltsienSelectRequestStatus)).all()}
    team_names = dict(
        db.execute(select(Team.id, Team.name).where(Team.id.in_({request.team_id for request in requests}))).all()
    )
    author_ids = {request.created_by_user_id for request in requests if request.created_by_user_id is not None}
    author_names = (
        dict(db.execute(select(User.id, User.display_name).where(User.id.in_(author_ids))).all()) if author_ids else {}
    )

    responses = []
    for request in requests:
        request_status = statuses[request.status_id]
        responses.append(
            SpecialRequestResponse(
                id=request.id,
                season_id=request.season_id,
                team_id=request.team_id,
                team_name=team_names.get(request.team_id, ""),
                text=request.text,
                status_id=request_status.id,
                status_name=request_status.name,
                status_color=request_status.color,
                status_is_open=request_status.is_open,
                organisation_note=request.organisation_note,
                created_by_name=author_names.get(request.created_by_user_id),
                created_at=request.created_at,
                updated_at=request.updated_at,
                editable_by_me=season_editable
                and first_status is not None
                and request.status_id == first_status.id,
            )
        )
    return responses


def build_team_summaries(db: Session, season_id: int, team_ids: set[int]) -> list[TeamSummaryResponse]:
    """The team list of the wizard/ploegfiche: each team in scope with its
    completed steps and number of still-open requests.
    """
    if not team_ids:
        return []

    teams = db.execute(select(Team.id, Team.name).where(Team.id.in_(team_ids)).order_by(Team.name)).all()

    # Completed step keys per team (only steps that still exist count).
    known_keys = {step.key for step in STEP_DEFINITIONS}
    completed: dict[int, list[str]] = {}
    for team_id, step_key in db.execute(
        select(AltsienSelectStepProgress.team_id, AltsienSelectStepProgress.step_key).where(
            AltsienSelectStepProgress.season_id == season_id, AltsienSelectStepProgress.team_id.in_(team_ids)
        )
    ).all():
        if step_key in known_keys:
            completed.setdefault(team_id, []).append(step_key)

    # Open requests per team.
    open_counts = dict(
        db.execute(
            select(AltsienSelectSpecialRequest.team_id, func.count())
            .join(AltsienSelectRequestStatus, AltsienSelectRequestStatus.id == AltsienSelectSpecialRequest.status_id)
            .where(
                AltsienSelectSpecialRequest.season_id == season_id,
                AltsienSelectSpecialRequest.team_id.in_(team_ids),
                AltsienSelectRequestStatus.is_open.is_(True),
            )
            .group_by(AltsienSelectSpecialRequest.team_id)
        ).all()
    )

    return [
        TeamSummaryResponse(
            team_id=team.id,
            team_name=team.name,
            completed_step_keys=completed.get(team.id, []),
            open_request_count=open_counts.get(team.id, 0),
        )
        for team in teams
    ]


def _build_team_info(db: Session, team: Team) -> TeamInfoResponse:
    """The team's master data plus the names of its Altsien Kernleden."""
    location = db.get(TeamLocation, team.location_id) if team.location_id else None
    delivery_method = db.get(DeliveryMethod, team.delivery_method_id) if team.delivery_method_id else None
    kernleden = db.scalars(
        select(User.display_name)
        .join(TeamKernlid, TeamKernlid.altsien_kernlid_id == User.id)
        .where(TeamKernlid.team_id == team.id)
        .order_by(User.display_name)
    ).all()
    return TeamInfoResponse(
        id=team.id,
        name=team.name,
        location=location.location if location else None,
        delivery_method=delivery_method.delivery_method if delivery_method else None,
        description=team.description,
        kernleden=list(kernleden),
    )


def build_team_state(db: Session, user: User, season: Season, team: Team) -> TeamStateResponse:
    """Everything chosen for one team in one season (wizard + Ploegfiche)."""
    selected_ids = selected_festival_ids(db, season.id, team.id)

    # Every active festival of the season, plus any inactive one the team
    # was already linked to (so an old choice never silently disappears),
    # each outer-joined with its Plan a kar location.
    festival_rows = db.execute(
        select(
            Festival.id,
            Festival.name,
            Festival.start_date,
            Festival.end_date,
            KarTrackerAfleverlocatie.id.label("location_id"),
            KarTrackerAfleverlocatie.name.label("location_name"),
            KarTrackerAfleverlocatie.description.label("location_description"),
        )
        .outerjoin(
            KarTrackerKarAfleverlocatie,
            (KarTrackerKarAfleverlocatie.festival_id == Festival.id)
            & (KarTrackerKarAfleverlocatie.season_id == season.id)
            & (KarTrackerKarAfleverlocatie.team_id == team.id),
        )
        .outerjoin(KarTrackerAfleverlocatie, KarTrackerAfleverlocatie.id == KarTrackerKarAfleverlocatie.afleverlocatie_id)
        .where(Festival.season_id == season.id, Festival.active.is_(True) | Festival.id.in_(selected_ids))
        .order_by(Festival.start_date, Festival.name)
    ).all()
    festivals = [
        FestivalChoiceResponse(
            festival_id=row.id,
            festival_name=row.name,
            start_date=row.start_date,
            end_date=row.end_date,
            selected=row.id in selected_ids,
            afleverlocatie_id=row.location_id,
            afleverlocatie_name=row.location_name,
            afleverlocatie_description=row.location_description,
        )
        for row in festival_rows
    ]

    # The delivery locations offered in step 2.
    afleverlocaties = [
        AfleverlocatieOptionResponse(id=row.id, name=row.name, description=row.description)
        for row in db.execute(
            select(KarTrackerAfleverlocatie.id, KarTrackerAfleverlocatie.name, KarTrackerAfleverlocatie.description)
            .where(KarTrackerAfleverlocatie.active.is_(True))
            .order_by(KarTrackerAfleverlocatie.name)
        ).all()
    ]

    # Which steps are done, by whom.
    progress_rows = db.execute(
        select(AltsienSelectStepProgress, User.display_name)
        .outerjoin(User, User.id == AltsienSelectStepProgress.completed_by_user_id)
        .where(AltsienSelectStepProgress.season_id == season.id, AltsienSelectStepProgress.team_id == team.id)
    ).all()
    progress = [
        StepProgressResponse(step_key=row[0].step_key, completed_at=row[0].completed_at, completed_by_name=row[1])
        for row in progress_rows
    ]

    # The team's special requests, newest first.
    can_edit = season_is_editable_for(db, user, season)
    requests = db.scalars(
        select(AltsienSelectSpecialRequest)
        .where(AltsienSelectSpecialRequest.season_id == season.id, AltsienSelectSpecialRequest.team_id == team.id)
        .order_by(AltsienSelectSpecialRequest.created_at.desc(), AltsienSelectSpecialRequest.id.desc())
    ).all()

    return TeamStateResponse(
        season_id=season.id,
        season_name=season.name,
        season_open=season.periode_open,
        can_edit=can_edit,
        team=_build_team_info(db, team),
        steps=list_steps(),
        progress=progress,
        festivals=festivals,
        afleverlocaties=afleverlocaties,
        requests=build_request_responses(db, user, list(requests), can_edit),
    )


def clear_step(db: Session, season_id: int, team_id: int, step_key: str) -> None:
    """Un-mark a step (used when its underlying choices change so that it
    no longer satisfies its completion rule).
    """
    existing = db.scalar(
        select(AltsienSelectStepProgress).where(
            AltsienSelectStepProgress.season_id == season_id,
            AltsienSelectStepProgress.team_id == team_id,
            AltsienSelectStepProgress.step_key == step_key,
        )
    )
    if existing is not None:
        db.delete(existing)


def selected_festivals_of(db: Session, season_id: int, team_id: int) -> list[TeamFestival]:
    """The team's festival link rows for the season."""
    return list(
        db.scalars(
            select(TeamFestival).where(TeamFestival.season_id == season_id, TeamFestival.team_id == team_id)
        ).all()
    )
