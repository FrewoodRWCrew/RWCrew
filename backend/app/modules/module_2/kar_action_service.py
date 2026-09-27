# Shared "Manuele kar beweging" logic: reading and logging kar movements
# (KarTracker_kar_actions). Used by KarTracker's own web screen
# (module_2/router.py) and by the phone app's KarScan (app/mobile/
# module_2_router.py), so both always read and write movements the same way.

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_action import KarTrackerKarAction
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.team import Team
from app.db.models.user import User
from app.schemas.kartracker import KarActionCreateRequest, KarActionResponse


def kar_action_query():
    """The history query: every logged movement joined to the names shown in
    the table. Outer joins for team/user, since both may be empty.
    """
    return (
        select(
            KarTrackerKarAction,
            KarTrackerKar.kar_nummer,
            KarTrackerKarStatus.name.label("status_name"),
            Team.name.label("team_name"),
            User.display_name.label("user_name"),
        )
        .join(KarTrackerKar, KarTrackerKar.id == KarTrackerKarAction.kar_id)
        .join(KarTrackerKarStatus, KarTrackerKarStatus.id == KarTrackerKarAction.status_id)
        .outerjoin(Team, Team.id == KarTrackerKarAction.team_id)
        .outerjoin(User, User.id == KarTrackerKarAction.user_id)
    )


def build_kar_action_response(row) -> KarActionResponse:
    """Turn one row of kar_action_query() into its response shape."""
    action: KarTrackerKarAction = row[0]
    return KarActionResponse(
        id=action.id,
        kar_id=action.kar_id,
        kar_nummer=row.kar_nummer,
        status_id=action.status_id,
        status_name=row.status_name,
        team_id=action.team_id,
        team_name=row.team_name,
        latitude=action.latitude,
        longitude=action.longitude,
        recorded_at=action.recorded_at,
        user_name=row.user_name,
    )


def list_kar_actions(db: Session, kar_id: int | None, limit: int) -> list[KarActionResponse]:
    """The movement history, newest first, optionally for one kar only."""
    query = kar_action_query()
    if kar_id is not None:
        query = query.where(KarTrackerKarAction.kar_id == kar_id)
    rows = db.execute(
        query.order_by(KarTrackerKarAction.recorded_at.desc(), KarTrackerKarAction.id.desc()).limit(limit)
    ).all()
    return [build_kar_action_response(row) for row in rows]


def log_kar_action(db: Session, payload: KarActionCreateRequest, user: User) -> KarActionResponse:
    """Log one kar movement, make it the kar's latest known state, commit,
    and return the logged row.
    """
    kar = db.get(KarTrackerKar, payload.kar_id)
    if kar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kar not found")
    if db.get(KarTrackerKarStatus, payload.status_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kar status not found")

    # The log row: the team is the kar's team right now (a snapshot), the
    # timestamp is the server's clock.
    recorded_at = datetime.now(timezone.utc)
    action = KarTrackerKarAction(
        kar_id=kar.id,
        status_id=payload.status_id,
        team_id=kar.team_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        recorded_at=recorded_at,
        user_id=user.id,
    )
    db.add(action)

    # The kar itself now shows this status/location as its latest one, so
    # KarManagement and Kar Map stay in sync with the log.
    kar.status_id = payload.status_id
    kar.last_latitude = payload.latitude
    kar.last_longitude = payload.longitude
    kar.last_recorded_at = recorded_at

    db.commit()

    row = db.execute(kar_action_query().where(KarTrackerKarAction.id == action.id)).one()
    return build_kar_action_response(row)
