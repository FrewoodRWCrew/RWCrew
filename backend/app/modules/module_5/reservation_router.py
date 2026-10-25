# Atelier's (module-5) reservations — the sidebar's "Reservaties" group:
# per festival and per ploeg the number of persons and their package
# (articles × pieces per person), all on one screen ("Reservaties", with
# "copy from last year"), and what that means for the store each festival
# day plus a printable picklist ("Voorbereiden"). Its own APIRouter on the
# module's /api/modules/module-5 prefix (included in app/main.py).
#
# Writes go through reservation_service.py, the calculation lives in
# preparation_service.py (nothing stored), the PDF in picklist_pdf.py.

from datetime import date
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_reservation import AtelierReservation
from app.db.models.festival import Festival
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.module_5.deps import require_screen_permission, require_view_on_any
from app.modules.module_5.picklist_pdf import build_picklist_pdf
from app.modules.module_5.preparation_service import build_preparation, festival_summary
from app.modules.module_5.reservation_service import (
    KEEP,
    ReservationError,
    copy_from_previous_festival,
    festival_days,
    lines_by_reservation,
    offered_teams,
    previous_festival,
    reservations_by_team,
    upsert_reservation,
)
from app.schemas.atelier import (
    CopyReservationsRequest,
    CopyReservationsResponse,
    FestivalReservationStatsResponse,
    FestivalSummaryResponse,
    PackageLine,
    PreparationResponse,
    PreviousReservationsResponse,
    ReservationRowResponse,
    SaveReservationsRequest,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

KPI_SCREEN = "atelier.kpi"
RESERVATIONS_SCREEN = "atelier.reservations"
PREPARATION_SCREEN = "atelier.preparation"

Locale = Literal["nl", "en"]


def _get_festival_or_404(db: Session, festival_id: int) -> Festival:
    """Load one festival or answer 404."""
    festival = db.get(Festival, festival_id)
    if festival is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival not found")
    return festival


@router.get("/festivals", response_model=list[FestivalSummaryResponse])
def list_festivals(
    season_id: int = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_view_on_any(RESERVATIONS_SCREEN, PREPARATION_SCREEN, KPI_SCREEN)),
) -> list[FestivalSummaryResponse]:
    """The season's active festivals in calendar order, each with its days."""
    if db.get(Season, season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    festivals = db.scalars(
        select(Festival)
        .where(Festival.season_id == season_id, Festival.active.is_(True))
        .order_by(Festival.start_date, Festival.name)
    ).all()
    return [festival_summary(festival) for festival in festivals]


# --- Reservaties ----------------------------------------------------------------


def _rows(db: Session, festival: Festival, *, only_reserved: bool = False) -> list[ReservationRowResponse]:
    """The festival's table: every offered team (or only the teams with a
    reservation) with persons, note and package, the lines in article-name order."""
    reservations = reservations_by_team(db, festival.id)
    lines = lines_by_reservation(db, [row.id for row in reservations.values()])
    article_names = {article.id: article.name.lower() for article in db.scalars(select(AtelierArticle)).all()}

    rows = []
    for team in offered_teams(db, festival):
        reservation = reservations.get(team.id)
        if only_reserved and reservation is None:
            continue
        package = sorted(
            lines.get(reservation.id, []) if reservation else [], key=lambda line: article_names[line.article_id]
        )
        rows.append(
            ReservationRowResponse(
                team_id=team.id,
                team_name=team.name,
                team_active=team.active,
                persons=reservation.persons if reservation else 0,
                lines=[PackageLine.model_validate(line) for line in package],
                note=reservation.note if reservation else None,
                updated_by_name=reservation.updated_by_name if reservation else None,
                updated_at=reservation.updated_at if reservation else None,
            )
        )
    return rows


@router.get("/reservations", response_model=list[ReservationRowResponse])
def list_reservations(
    festival_id: int = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(RESERVATIONS_SCREEN, "view")),
) -> list[ReservationRowResponse]:
    """The Reservaties table for one festival: every active team."""
    return _rows(db, _get_festival_or_404(db, festival_id))


@router.put("/reservations/{festival_id}", response_model=list[ReservationRowResponse])
def save_reservations(
    festival_id: int,
    payload: SaveReservationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(RESERVATIONS_SCREEN, "edit")),
) -> list[ReservationRowResponse]:
    """Save the sent teams' persons, notes and (when sent) packages in one
    go; other teams stay as they are."""
    festival = _get_festival_or_404(db, festival_id)
    offered_ids = {team.id for team in offered_teams(db, festival)}
    team_ids = [item.team_id for item in payload.reservations]
    if len(team_ids) != len(set(team_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A team can only be sent once")
    if any(team_id not in offered_ids for team_id in team_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only active teams can get a reservation")

    try:
        for item in payload.reservations:
            lines = KEEP if item.lines is None else [(line.article_id, line.quantity_per_person) for line in item.lines]
            upsert_reservation(
                db, current_user, festival, item.team_id, persons=item.persons, note=item.note, lines=lines
            )
    except ReservationError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    db.commit()
    return _rows(db, festival)


@router.get("/reservations/{festival_id}/previous", response_model=PreviousReservationsResponse)
def get_previous_reservations(
    festival_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(RESERVATIONS_SCREEN, "view")),
) -> PreviousReservationsResponse:
    """The same festival last season (matched by name) and its reservations,
    for the "copy from last year" panel."""
    source = previous_festival(db, _get_festival_or_404(db, festival_id))
    if source is None:
        return PreviousReservationsResponse(festival=None, rows=[])
    return PreviousReservationsResponse(festival=festival_summary(source), rows=_rows(db, source, only_reserved=True))


@router.post("/reservations/{festival_id}/copy-previous", response_model=CopyReservationsResponse)
def copy_previous_reservations(
    festival_id: int,
    payload: CopyReservationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(RESERVATIONS_SCREEN, "edit")),
) -> CopyReservationsResponse:
    """Copy last year's reservations of the given teams: package lines are
    added/updated (never removed), persons only taken over while still 0."""
    festival = _get_festival_or_404(db, festival_id)
    result = copy_from_previous_festival(db, current_user, festival, payload.team_ids)
    db.commit()
    return CopyReservationsResponse(teams_changed=result.teams_changed, skipped_inactive=result.skipped_inactive)


# --- Voorbereiden -----------------------------------------------------------------


@router.get("/preparation", response_model=PreparationResponse)
def get_preparation(
    festival_id: int = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(PREPARATION_SCREEN, "view")),
) -> PreparationResponse:
    """What to prepare each day of the festival: store totals and bundles."""
    return build_preparation(db, _get_festival_or_404(db, festival_id))


@router.get("/preparation/pdf")
def get_picklist_pdf(
    festival_id: int = Query(...),
    day: date = Query(...),
    team_ids: list[int] | None = Query(default=None),
    locale: Locale = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(PREPARATION_SCREEN, "view")),
) -> Response:
    """The picklist of one festival day, for every reserved team or only the
    given ones; opened inline in a new browser tab."""
    festival = _get_festival_or_404(db, festival_id)
    if day not in festival_days(festival):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This day is not part of the festival")
    preparation = build_preparation(db, festival, team_ids)
    content = build_picklist_pdf(preparation, day, locale, current_user.display_name)
    filename = f"Picklijst {festival.name} {day.strftime('%d-%m-%Y')}.pdf"
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace('"', "_")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"},
    )


# --- KPI page -------------------------------------------------------------------------


@router.get("/reservation-stats", response_model=list[FestivalReservationStatsResponse])
def get_reservation_stats(
    season_id: int = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KPI_SCREEN, "view")),
) -> list[FestivalReservationStatsResponse]:
    """Per active festival of the season: persons and pieces per day, how
    many teams reserved, how many of those have no package yet, and which
    teams were probably forgotten there."""
    festivals = db.scalars(
        select(Festival)
        .where(Festival.season_id == season_id, Festival.active.is_(True))
        .order_by(Festival.start_date, Festival.name)
    ).all()
    missing = _forgotten_teams(db, season_id, [festival.id for festival in festivals])
    stats = []
    for festival in festivals:
        preparation = build_preparation(db, festival)
        stats.append(
            FestivalReservationStatsResponse(
                festival=preparation.festival,
                persons_per_day=preparation.persons_per_day,
                pieces_per_day=preparation.pieces_per_day,
                teams_reserved=len(preparation.bundles) + len(preparation.teams_without_package),
                teams_without_package=len(preparation.teams_without_package),
                teams_missing=missing.get(festival.id, []),
            )
        )
    return stats


def _forgotten_teams(db: Session, season_id: int, festival_ids: list[int]) -> dict[int, list[str]]:
    """Per festival, the active teams (by name) that have persons at another
    of these festivals but nothing here — no persons and no note. A team that
    really doesn't come can be silenced with 0 persons and a note."""
    filled: dict[int, set[int]] = {}  # team id -> festivals with persons
    handled: dict[int, set[int]] = {}  # team id -> festivals with persons or a note
    for row in db.scalars(
        select(AtelierReservation).where(
            AtelierReservation.season_id == season_id, AtelierReservation.festival_id.in_(festival_ids)
        )
    ).all():
        if row.persons > 0:
            filled.setdefault(row.team_id, set()).add(row.festival_id)
        if row.persons > 0 or row.note:
            handled.setdefault(row.team_id, set()).add(row.festival_id)

    teams = {team.id: team for team in db.scalars(select(Team).where(Team.id.in_(filled))).all()}
    missing: dict[int, list[str]] = {}
    for team_id in sorted(filled, key=lambda team_id: teams[team_id].name.lower()):
        if not teams[team_id].active:
            continue
        for festival_id in festival_ids:
            if festival_id not in handled.get(team_id, set()):
                missing.setdefault(festival_id, []).append(teams[team_id].name)
    return missing
