# Atelier's (module-5) counter desk — block 4, the sidebar's "Balie" group:
# "Uitgifte & inname" (every transaction starts with the choice Ophalen /
# Terugbrengen) and "Openstaand" (pieces not returned yet). Its own APIRouter
# on the module's /api/modules/module-5 prefix (included in app/main.py).
#
# Block 5: the desk screen polls the wristband scans of its scanner
# (/desk/scanners, /desk/scans) and can dismiss one; a pick-up or return made
# from a scan sends its scan_id so the scan is marked used.
#
# After an Ophalen and after a Terugbrengen (the person-level return) the
# person gets a mail, built by notifications.py from the admin's templates.
#
# All writes go through desk_service.py; a StockError becomes HTTP detail
# "code|param|…", translated by the frontend under atelier.desk.errors.<code>
# (or atelier.stock.errors.<code> for stock rules such as insufficient_stock).

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.timezone import belgian_now
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_handout import AtelierHandout
from app.db.models.atelier_handout_line import AtelierHandoutLine
from app.db.models.atelier_person import AtelierPerson
from app.db.models.atelier_person_bracelet import AtelierPersonBracelet
from app.db.models.atelier_scan import AtelierScan
from app.db.models.atelier_scanner import AtelierScanner
from app.db.models.atelier_size import AtelierSize
from app.db.models.festival import Festival
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.module_5.deps import require_screen_permission, require_view_on_any
from app.modules.module_5.desk_service import (
    CANCELLED,
    OPEN,
    bracelet_of,
    cancel_handout,
    create_handout,
    find_person,
    get_festival,
    open_lines_of,
    package_for_desk,
    person_by_bracelet,
    return_lines,
    return_person_lines,
    served_today,
    wristband_required,
)
from app.modules.module_5.notifications import HANDOUT, RETURN, queue_desk_mail
from app.modules.module_5.reservation_service import lines_by_reservation, reservations_by_team
from app.modules.module_5.scan_service import dismiss, waiting_scans
from app.modules.module_5.stock_service import StockError
from app.schemas.atelier import (
    DeskContextResponse,
    DeskOpenLine,
    DeskPackageArticle,
    DeskPersonResponse,
    DeskSizeOption,
    DeskStatsResponse,
    DeskTeamOption,
    HandoutLineResponse,
    HandoutRequest,
    HandoutResponse,
    ReturnRequest,
    ScannerResponse,
    ScanResponse,
)

router = APIRouter(prefix="/api/modules/module-5", tags=["Atelier"])

DESK_SCREEN = "atelier.desk"
OPEN_SCREEN = "atelier.open"
KPI_SCREEN = "atelier.kpi"


def _error(error: StockError) -> HTTPException:
    """A refused desk action as an HTTP error with detail "code|param|…"."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _line_parts(db: Session, line: AtelierHandoutLine) -> tuple[str, str, str]:
    """(article name, size name, fit) of a hand-out line."""
    article = db.get(AtelierArticle, line.article_id)
    size = db.get(AtelierSize, db.get(AtelierArticleSize, line.article_size_id).size_id)
    return article.name, size.name, size.fit


def _handout_response(db: Session, handout: AtelierHandout) -> HandoutResponse:
    """A pick-up with its pieces, for the screens."""
    person = db.get(AtelierPerson, handout.person_id)
    lines = db.scalars(
        select(AtelierHandoutLine).where(AtelierHandoutLine.handout_id == handout.id).order_by(AtelierHandoutLine.id)
    ).all()
    line_rows = []
    for line in lines:
        article_name, size_name, fit = _line_parts(db, line)
        line_rows.append(
            HandoutLineResponse(
                id=line.id,
                article_id=line.article_id,
                article_name=article_name,
                size_name=size_name,
                fit=fit,
                returned_at=line.returned_at,
            )
        )
    return HandoutResponse(
        id=handout.id,
        person_id=person.id,
        person_name=person.full_name,
        email=person.email,
        bracelet_number=_bracelet_number(db, person.id, handout.festival_id),
        festival_name=db.get(Festival, handout.festival_id).name,
        team_name=db.get(Team, handout.team_id).name,
        day=handout.day,
        status=handout.status,
        created_at=handout.created_at,
        created_by_name=handout.created_by_name,
        lines=line_rows,
    )


def _bracelet_number(db: Session, person_id: int, festival_id: int | None) -> str | None:
    """A person's wristband number at the festival; without a festival, the
    latest one they got."""
    if festival_id is not None:
        bracelet = bracelet_of(db, person_id, festival_id)
    else:
        bracelet = db.scalar(
            select(AtelierPersonBracelet)
            .where(AtelierPersonBracelet.person_id == person_id)
            .order_by(AtelierPersonBracelet.id.desc())
            .limit(1)
        )
    return bracelet.number if bracelet else None


def _person_response(db: Session, person: AtelierPerson, festival_id: int | None = None) -> DeskPersonResponse:
    """A worker with the pieces still out (and their wristband number at the festival)."""
    open_lines = []
    for line in open_lines_of(db, person.id):
        handout = db.get(AtelierHandout, line.handout_id)
        article_name, size_name, fit = _line_parts(db, line)
        open_lines.append(
            DeskOpenLine(
                line_id=line.id,
                handout_id=handout.id,
                article_id=line.article_id,
                article_name=article_name,
                size_name=size_name,
                fit=fit,
                festival_name=db.get(Festival, handout.festival_id).name,
                team_name=db.get(Team, handout.team_id).name,
                day=handout.day,
                handed_out_at=handout.created_at,
            )
        )
    return DeskPersonResponse(
        id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        name=person.full_name,
        email=person.email,
        bracelet_number=_bracelet_number(db, person.id, festival_id),
        last_team_id=person.last_team_id,
        open_lines=open_lines,
    )


# --- Lookups ------------------------------------------------------------------------


@router.get("/desk/teams", response_model=list[DeskTeamOption])
def list_desk_teams(
    festival_id: int = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_view_on_any(DESK_SCREEN, OPEN_SCREEN)),
) -> list[DeskTeamOption]:
    """The teams with a package at the festival (the desk's team dropdown), by name."""
    try:
        get_festival(db, festival_id)
    except StockError as error:
        raise _error(error) from error
    reservations = reservations_by_team(db, festival_id)
    lines = lines_by_reservation(db, [row.id for row in reservations.values()])
    options = []
    for team_id, reservation in reservations.items():
        if not lines.get(reservation.id):
            continue
        team = db.get(Team, team_id)
        options.append(DeskTeamOption(team_id=team.id, team_name=team.name, persons=reservation.persons))
    return sorted(options, key=lambda option: option.team_name.lower())


@router.get("/desk/persons", response_model=list[DeskPersonResponse])
def search_persons(
    q: str = Query(min_length=2, max_length=100),
    festival_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> list[DeskPersonResponse]:
    """Workers whose name ("first last"), email or wristband number (any
    festival) contains the text (max 10), with their open pieces."""
    needle = f"%{' '.join(q.lower().split())}%"
    full_name = func.lower(AtelierPerson.first_name + " " + AtelierPerson.last_name)
    with_bracelet = select(AtelierPersonBracelet.person_id).where(func.lower(AtelierPersonBracelet.number).like(needle))
    persons = db.scalars(
        select(AtelierPerson)
        .where(
            or_(
                full_name.like(needle),
                func.lower(AtelierPerson.email).like(needle),
                AtelierPerson.id.in_(with_bracelet),
            )
        )
        .order_by(AtelierPerson.first_name, AtelierPerson.last_name)
        .limit(10)
    ).all()
    return [_person_response(db, person, festival_id) for person in persons]


@router.get("/desk/persons/lookup", response_model=DeskPersonResponse | None)
def lookup_person(
    first_name: str = Query(min_length=1, max_length=255),
    last_name: str = Query(min_length=1, max_length=255),
    festival_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> DeskPersonResponse | None:
    """The worker with exactly this first + family name (the person's key), or null."""
    person = find_person(db, first_name, last_name)
    return _person_response(db, person, festival_id) if person else None


@router.get("/desk/persons/by-bracelet", response_model=DeskPersonResponse | None)
def lookup_person_by_bracelet(
    festival_id: int = Query(...),
    number: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> DeskPersonResponse | None:
    """The worker wearing this wristband number at the festival, or null."""
    person = person_by_bracelet(db, festival_id, number)
    return _person_response(db, person, festival_id) if person else None


@router.get("/desk/wristband-required", response_model=bool)
def get_wristband_required(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> bool:
    """Whether a pick-up needs a wristband number (the global switch)."""
    return wristband_required(db)


# --- Wristband scans at the desk -----------------------------------------------------------


@router.get("/desk/scanners", response_model=list[ScannerResponse])
def list_desk_scanners(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> list[AtelierScanner]:
    """The scanners known from their messages (the desk's "this desk = …" dropdown)."""
    return list(db.scalars(select(AtelierScanner).order_by(AtelierScanner.label, AtelierScanner.device_name)).all())


@router.get("/desk/scans", response_model=list[ScanResponse])
def list_desk_scans(
    device_id: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> list[AtelierScan]:
    """The scans waiting at this scanner (polled by the desk screen), newest first."""
    return waiting_scans(db, device_id)


@router.post("/desk/scans/{scan_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_desk_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "create")),
) -> None:
    """"Negeren": the scan no longer waits at the desk."""
    scan = db.get(AtelierScan, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    dismiss(scan)
    db.commit()


@router.get("/desk/context", response_model=DeskContextResponse)
def get_desk_context(
    festival_id: int = Query(...),
    team_id: int = Query(...),
    day: date = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> DeskContextResponse:
    """The team's package (articles + sizes with available pieces), its
    reserved persons and how many people already picked up that day."""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    reservation = reservations_by_team(db, festival_id).get(team_id)
    articles = [
        DeskPackageArticle(
            article_id=article.id,
            code=article.code,
            name=article.name,
            has_image=article.has_image,
            image_updated_at=article.image_updated_at,
            sizes=[
                DeskSizeOption(article_size_id=row.id, size_name=size.name, fit=size.fit, available=available)
                for row, size, available in sizes
            ],
        )
        for article, sizes in package_for_desk(db, festival_id, team_id)
    ]
    return DeskContextResponse(
        team_id=team.id,
        team_name=team.name,
        persons_reserved=reservation.persons if reservation else 0,
        served_today=served_today(db, festival_id, team_id, day),
        articles=articles,
    )


# --- Ophalen / Terugbrengen -------------------------------------------------------------


@router.post("/desk/handouts", response_model=HandoutResponse, status_code=status.HTTP_201_CREATED)
def post_handout(
    payload: HandoutRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(DESK_SCREEN, "create")),
) -> HandoutResponse:
    """Ophalen: hand out the package's pieces to a person (who then gets the
    "Uitgifte" mail, when they have an email address)."""
    try:
        handout = create_handout(
            db,
            current_user,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            bracelet_number=payload.bracelet_number,
            festival_id=payload.festival_id,
            team_id=payload.team_id,
            day=payload.day,
            lines=[(line.article_id, line.article_size_id) for line in payload.lines],
            scan_id=payload.scan_id,
        )
    except StockError as error:
        db.rollback()
        raise _error(error) from error
    db.commit()
    person = db.get(AtelierPerson, handout.person_id)
    lines = db.scalars(
        select(AtelierHandoutLine).where(AtelierHandoutLine.handout_id == handout.id).order_by(AtelierHandoutLine.id)
    ).all()
    queue_desk_mail(
        db, HANDOUT, person, handout, list(lines), _bracelet_number(db, person.id, handout.festival_id), background_tasks
    )
    return _handout_response(db, handout)


@router.get("/desk/persons/{person_id}/open", response_model=list[HandoutResponse])
def list_person_open_handouts(
    person_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(DESK_SCREEN, "view")),
) -> list[HandoutResponse]:
    """A person's pick-ups that still have pieces out (Terugbrengen)."""
    handouts = db.scalars(
        select(AtelierHandout)
        .where(AtelierHandout.person_id == person_id, AtelierHandout.status == OPEN)
        .order_by(AtelierHandout.id)
    ).all()
    return [_handout_response(db, handout) for handout in handouts]


@router.post("/desk/persons/{person_id}/return", response_model=list[HandoutResponse])
def post_person_return(
    person_id: int,
    payload: ReturnRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(DESK_SCREEN, "create")),
) -> list[HandoutResponse]:
    """Terugbrengen (the desk's call): the ticked pieces of one person come
    back, from any of their open pick-ups, and the person gets one "Inname"
    mail for the whole transaction."""
    try:
        handouts, lines = return_person_lines(db, current_user, person_id, payload.line_ids, payload.scan_id)
    except StockError as error:
        db.rollback()
        raise _error(error) from error
    db.commit()
    # The mail names the festival/team/day of the latest pick-up returned.
    latest = handouts[-1]
    queue_desk_mail(
        db,
        RETURN,
        db.get(AtelierPerson, person_id),
        latest,
        lines,
        _bracelet_number(db, person_id, latest.festival_id),
        background_tasks,
    )
    return [_handout_response(db, handout) for handout in handouts]


@router.post("/desk/handouts/{handout_id}/return", response_model=HandoutResponse)
def post_return(
    handout_id: int,
    payload: ReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(DESK_SCREEN, "create")),
) -> HandoutResponse:
    """Terugbrengen of one pick-up (sends no mail; the desk uses the
    person-level return above)."""
    try:
        handout = return_lines(db, current_user, handout_id, payload.line_ids, payload.scan_id)
    except StockError as error:
        db.rollback()
        raise _error(error) from error
    db.commit()
    return _handout_response(db, handout)


@router.post("/desk/handouts/{handout_id}/cancel", response_model=HandoutResponse)
def post_cancel(
    handout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(DESK_SCREEN, "edit")),
) -> HandoutResponse:
    """Uitgifte annuleren (only while nothing was returned)."""
    try:
        handout = cancel_handout(db, current_user, handout_id)
    except StockError as error:
        db.rollback()
        raise _error(error) from error
    db.commit()
    return _handout_response(db, handout)


# --- Openstaand and KPI ---------------------------------------------------------------------


@router.get("/desk/open", response_model=list[HandoutResponse])
def list_open_handouts(
    festival_id: int | None = Query(default=None),
    day: date | None = Query(default=None),
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(OPEN_SCREEN, "view")),
) -> list[HandoutResponse]:
    """Pick-ups with pieces not returned yet, oldest first, optionally per
    festival / day / team. Only the pieces still out are listed."""
    query = select(AtelierHandout).where(AtelierHandout.status == OPEN).order_by(AtelierHandout.day, AtelierHandout.id)
    if festival_id is not None:
        query = query.where(AtelierHandout.festival_id == festival_id)
    if day is not None:
        query = query.where(AtelierHandout.day == day)
    if team_id is not None:
        query = query.where(AtelierHandout.team_id == team_id)
    result = []
    for handout in db.scalars(query).all():
        response = _handout_response(db, handout)
        response.lines = [line for line in response.lines if line.returned_at is None]
        result.append(response)
    return result


@router.get("/desk/stats", response_model=DeskStatsResponse)
def get_desk_stats(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KPI_SCREEN, "view")),
) -> DeskStatsResponse:
    """The KPI page's desk tiles."""
    today = belgian_now().date()
    handed_out_today = (
        db.scalar(
            select(func.count(AtelierHandoutLine.id))
            .join(AtelierHandout, AtelierHandout.id == AtelierHandoutLine.handout_id)
            .where(AtelierHandout.day == today, AtelierHandout.status != CANCELLED)
        )
        or 0
    )
    open_lines = (
        select(AtelierHandoutLine.id, AtelierHandout.person_id)
        .join(AtelierHandout, AtelierHandout.id == AtelierHandoutLine.handout_id)
        .where(AtelierHandout.status == OPEN, AtelierHandoutLine.returned_at.is_(None))
        .subquery()
    )
    still_out = db.scalar(select(func.count()).select_from(open_lines)) or 0
    persons = db.scalar(select(func.count(func.distinct(open_lines.c.person_id)))) or 0
    return DeskStatsResponse(handed_out_today=handed_out_today, still_out=still_out, persons_with_open=persons)
