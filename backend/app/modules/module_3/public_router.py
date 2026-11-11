# The public, no-login entry point for Intervention Requests: customers
# reach this via the karblad's QR code (public kar page → "Interventie"
# tile), which encodes a URL with query parameters pre-filling Ploeg/Karnr/
# Afleverplaats/Zone. Every endpoint here is deliberately free of
# get_current_user/require_module_access — modeled on app/landing/auth.py's
# login endpoint, the codebase's existing unauthenticated-endpoint pattern —
# unlike every endpoint in router.py, which is staff-only.

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.intervention_request import InterventionRequest
from app.db.models.team import Team
from app.modules.module_3.notifications import queue_new_request_mail
from app.modules.module_3.service import (
    generate_request_number,
    get_default_new_status,
    list_teams_for_dropdown,
)
from app.schemas.intervention_requests import (
    InterventionRequestResponse,
    InterventionRequestsTeamResponse,
    PublicInterventionRequestCreateRequest,
)
from app.shared.rate_limit import SlidingWindowLimiter

router = APIRouter(prefix="/api/public/intervention-requests", tags=["Intervention Requests (Public)"])

PUBLIC_REQUEST_RATE_LIMIT = 10
PUBLIC_REQUEST_RATE_WINDOW_SECONDS = 60.0
# A small number of public submissions per client IP per minute (in memory, see app/shared/rate_limit.py).
_public_request_limiter = SlidingWindowLimiter(PUBLIC_REQUEST_RATE_LIMIT, PUBLIC_REQUEST_RATE_WINDOW_SECONDS)


@router.get("/teams", response_model=list[InterventionRequestsTeamResponse])
def list_public_teams(db: Session = Depends(get_db)) -> list[Team]:
    """Every MasterData team, for the public form's "Ploeg" dropdown."""
    return list_teams_for_dropdown(db)


@router.post("", response_model=InterventionRequestResponse, status_code=status.HTTP_201_CREATED)
def create_public_intervention_request(
    payload: PublicInterventionRequestCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> InterventionRequest:
    """Create a brand-new intervention request from the public form.

    Unlike the staff-only create_intervention_request in router.py, the
    caller can never choose status_id/handled_by/team_cart_user_id — those
    are internal-only fields, set here rather than trusted from an
    anonymous submitter.
    """
    _public_request_limiter.enforce(request)

    if payload.team_id is not None and db.get(Team, payload.team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    new_request = InterventionRequest(
        request_number=generate_request_number(db),
        status_id=get_default_new_status(db).id,
        handled_by=None,
        team_cart_user_id=None,
        **payload.model_dump(),
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    # Let the mailing list know (sent after this response has gone out).
    queue_new_request_mail(db, new_request, background_tasks)
    return new_request
