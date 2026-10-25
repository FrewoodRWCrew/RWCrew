# Atelier's counter desk (block 4): "Ophalen" (a worker picks up their team's
# package, one piece per article in the size chosen at the desk) and
# "Terugbrengen" (the pieces come back, partly or all). The only place that
# writes Atelier_person, Atelier_handout and Atelier_handout_line; the stock
# moves go through stock_service.hand_out / return_pieces in the same
# transaction. Nothing here commits: the router does.
#
# Rules (decided 2026-10-26):
#   - first name + family name (together the person's key) + email
#     (optional, not unique) + the wristband number (new per festival, unique
#     within the festival; required when the global switch is on) + team +
#     festival + day;
#   - a wristband scan (block 5, scan_service.py) can fill all that in; the
#     transaction then marks the scan "used";
#   - only the articles of the team's package for that festival, 1 piece each;
#   - a person can't get an article again while the previous one is out;
#   - more people than reserved is only a warning (the screen shows it);
#   - "Uitgifte annuleren" only while nothing of the pick-up was returned.

import re
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_handout import AtelierHandout
from app.db.models.atelier_handout_line import AtelierHandoutLine
from app.db.models.atelier_person import AtelierPerson
from app.db.models.atelier_person_bracelet import AtelierPersonBracelet
from app.db.models.atelier_scan import AtelierScan
from app.db.models.atelier_settings import AtelierSettings
from app.db.models.atelier_size import FITS, AtelierSize
from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.festival import Festival
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.module_5.reservation_service import festival_days, lines_by_reservation, reservations_by_team
from app.modules.module_5.scan_service import NEW, mark_used
from app.modules.module_5.stock_service import (
    AVAILABLE,
    StockError,
    all_balances,
    hand_out,
    return_pieces,
    reverse_document,
)

OPEN = "open"
RETURNED = "returned"
CANCELLED = "cancelled"

# A plain "something@something.something" check — enough to catch typos.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str | None) -> str | None:
    """The email as stored: trimmed and lowercase, None when empty (it's
    optional). Refused when it doesn't look like an email address."""
    value = (email or "").strip().lower()
    if not value:
        return None
    if not _EMAIL_PATTERN.match(value):
        raise StockError("email_invalid")
    return value


def wristband_required(db: Session) -> bool:
    """The global switch "Polsband verplicht bij Ophalen" (settings row 1)."""
    settings = db.get(AtelierSettings, 1)
    return bool(settings and settings.wristband_required)


def bracelet_of(db: Session, person_id: int, festival_id: int) -> AtelierPersonBracelet | None:
    """A person's wristband at a festival."""
    return db.scalar(
        select(AtelierPersonBracelet).where(
            AtelierPersonBracelet.person_id == person_id, AtelierPersonBracelet.festival_id == festival_id
        )
    )


def person_by_bracelet(db: Session, festival_id: int, number: str) -> AtelierPerson | None:
    """The person wearing this wristband number at this festival."""
    bracelet = db.scalar(
        select(AtelierPersonBracelet).where(
            AtelierPersonBracelet.festival_id == festival_id, AtelierPersonBracelet.number == number.strip()
        )
    )
    return db.get(AtelierPerson, bracelet.person_id) if bracelet else None


def _set_bracelet(db: Session, person: AtelierPerson, festival_id: int, number: str) -> None:
    """Give the person this wristband number at the festival (a new number
    replaces their old one there); refused when someone else wears it."""
    owner = person_by_bracelet(db, festival_id, number)
    if owner is not None and owner.id != person.id:
        raise StockError("bracelet_in_use", number, owner.full_name)
    bracelet = bracelet_of(db, person.id, festival_id)
    if bracelet is None:
        db.add(AtelierPersonBracelet(person_id=person.id, festival_id=festival_id, number=number))
    else:
        bracelet.number = number
    db.flush()


def _waiting_scan(db: Session, scan_id: int | None) -> AtelierScan | None:
    """The scan a transaction came from (must still be waiting)."""
    if scan_id is None:
        return None
    scan = db.get(AtelierScan, scan_id)
    if scan is None or scan.status != NEW:
        raise StockError("scan_not_waiting")
    return scan


def name_key(first_name: str, last_name: str) -> str:
    """The person's key: "first|last" in lowercase with single spaces, so
    "Jan  Peeters" and "jan peeters" are the same person."""
    return f"{' '.join(first_name.lower().split())}|{' '.join(last_name.lower().split())}"


def find_person(db: Session, first_name: str, last_name: str) -> AtelierPerson | None:
    """The worker with this first and family name, if known."""
    return db.scalar(select(AtelierPerson).where(AtelierPerson.name_key == name_key(first_name, last_name)))


def get_festival(db: Session, festival_id: int) -> Festival:
    """Load a festival, or refuse."""
    festival = db.get(Festival, festival_id)
    if festival is None:
        raise StockError("festival_not_found", status_code=404)
    return festival


def package_article_ids(db: Session, festival_id: int, team_id: int) -> list[int]:
    """The articles of the team's package for this festival (empty without one)."""
    reservation = reservations_by_team(db, festival_id).get(team_id)
    if reservation is None:
        return []
    return [line.article_id for line in lines_by_reservation(db, [reservation.id]).get(reservation.id, [])]


def open_lines_of(db: Session, person_id: int) -> list[AtelierHandoutLine]:
    """The pieces a person still has, oldest first."""
    return list(
        db.scalars(
            select(AtelierHandoutLine)
            .join(AtelierHandout, AtelierHandout.id == AtelierHandoutLine.handout_id)
            .where(
                AtelierHandout.person_id == person_id,
                AtelierHandout.status == OPEN,
                AtelierHandoutLine.returned_at.is_(None),
            )
            .order_by(AtelierHandoutLine.id)
        ).all()
    )


def served_today(db: Session, festival_id: int, team_id: int, day: date) -> int:
    """How many different people of the team picked up clothing that day."""
    return (
        db.scalar(
            select(func.count(func.distinct(AtelierHandout.person_id))).where(
                AtelierHandout.festival_id == festival_id,
                AtelierHandout.team_id == team_id,
                AtelierHandout.day == day,
                AtelierHandout.status != CANCELLED,
            )
        )
        or 0
    )


def package_for_desk(db: Session, festival_id: int, team_id: int) -> list[tuple[AtelierArticle, list[tuple[AtelierArticleSize, AtelierSize, int]]]]:
    """The team's package for the desk: per article its active sizes (in the
    size list's order) with the available pieces."""
    balances = all_balances(db)
    sizes = {size.id: size for size in db.scalars(select(AtelierSize)).all()}
    result = []
    for article_id in package_article_ids(db, festival_id, team_id):
        article = db.get(AtelierArticle, article_id)
        rows = [
            row
            for row in db.scalars(select(AtelierArticleSize).where(AtelierArticleSize.article_id == article_id)).all()
            if row.active
        ]
        rows.sort(key=lambda row: (FITS.index(sizes[row.size_id].fit), sizes[row.size_id].sort_order))
        result.append((article, [(row, sizes[row.size_id], balances.get((row.id, AVAILABLE), 0)) for row in rows]))
    return sorted(result, key=lambda item: item[0].name.lower())


def create_handout(
    db: Session,
    user: User,
    *,
    first_name: str,
    last_name: str,
    email: str | None = None,
    bracelet_number: str | None = None,
    festival_id: int,
    team_id: int,
    day: date,
    lines: list[tuple[int, int]],
    scan_id: int | None = None,
) -> AtelierHandout:
    """Ophalen: hand out one piece of each chosen (article, article size) to
    a person, after checking the rules above; books available → handed out."""
    first_name = " ".join(first_name.split())
    last_name = " ".join(last_name.split())
    if not first_name or not last_name:
        raise StockError("name_required")
    email = normalize_email(email)
    bracelet_number = (bracelet_number or "").strip() or None
    festival = get_festival(db, festival_id)
    scan = _waiting_scan(db, scan_id)
    if day not in festival_days(festival):
        raise StockError("day_not_in_festival")
    team = db.get(Team, team_id)
    if team is None:
        raise StockError("team_not_found", status_code=404)

    package = set(package_article_ids(db, festival_id, team_id))
    if not package:
        raise StockError("no_package", team.name)
    article_ids = [article_id for article_id, _size in lines]
    if len(article_ids) != len(set(article_ids)):
        raise StockError("article_twice")
    for article_id, article_size_id in lines:
        article = db.get(AtelierArticle, article_id)
        if article is None or article_id not in package:
            raise StockError("not_in_package", article.name if article else article_id)
        row = db.get(AtelierArticleSize, article_size_id)
        if row is None or row.article_id != article_id or not row.active:
            raise StockError("size_required", article.name)

    # The person, found (or created) by first + family name; the latest
    # spelling, email (when given) and team win.
    person = find_person(db, first_name, last_name)
    if person is None:
        person = AtelierPerson(
            first_name=first_name,
            last_name=last_name,
            name_key=name_key(first_name, last_name),
            email=email,
            last_team_id=team_id,
        )
        db.add(person)
        db.flush()
    else:
        person.first_name = first_name
        person.last_name = last_name
        if email is not None:
            person.email = email
        person.last_team_id = team_id
        # An article can't be picked up again while the previous one is out.
        still_out = {line.article_id for line in open_lines_of(db, person.id)}
        for article_id in article_ids:
            if article_id in still_out:
                raise StockError("article_still_out", db.get(AtelierArticle, article_id).name)

    # The wristband number at this festival: a typed/scanned one is stored
    # (an empty field keeps the one already known); required when switched on.
    if bracelet_number is not None:
        _set_bracelet(db, person, festival_id, bracelet_number)
    elif wristband_required(db) and bracelet_of(db, person.id, festival_id) is None:
        raise StockError("bracelet_required")

    document = hand_out(db, user, [article_size_id for _article, article_size_id in lines], note=person.full_name)
    handout = AtelierHandout(
        person_id=person.id,
        festival_id=festival_id,
        team_id=team_id,
        day=day,
        stock_document_id=document.id,
        status=OPEN,
        created_by=user.id,
        created_by_name=user.display_name,
    )
    db.add(handout)
    db.flush()
    for article_id, article_size_id in lines:
        db.add(AtelierHandoutLine(handout_id=handout.id, article_id=article_id, article_size_id=article_size_id))
    if scan is not None:
        mark_used(db, scan, person.id)
    db.flush()
    return handout


def _get_handout(db: Session, handout_id: int) -> AtelierHandout:
    """Load a pick-up, or refuse."""
    handout = db.get(AtelierHandout, handout_id)
    if handout is None:
        raise StockError("handout_not_found", status_code=404)
    return handout


def _lines_of(db: Session, handout_id: int) -> list[AtelierHandoutLine]:
    """A pick-up's pieces."""
    return list(
        db.scalars(select(AtelierHandoutLine).where(AtelierHandoutLine.handout_id == handout_id).order_by(AtelierHandoutLine.id)).all()
    )


def return_lines(
    db: Session, user: User, handout_id: int, line_ids: list[int], scan_id: int | None = None
) -> AtelierHandout:
    """Terugbrengen: the ticked pieces come back (handed out → to wash). The
    pick-up is "returned" once every piece is back. A scan the return came
    from is marked used."""
    handout = _get_handout(db, handout_id)
    scan = _waiting_scan(db, scan_id)
    if handout.status != OPEN:
        raise StockError("handout_closed")
    lines = {line.id: line for line in _lines_of(db, handout.id)}
    chosen = []
    for line_id in set(line_ids):
        line = lines.get(line_id)
        if line is None:
            raise StockError("line_not_found", status_code=404)
        if line.returned_at is not None:
            raise StockError("already_returned")
        chosen.append(line)

    person = db.get(AtelierPerson, handout.person_id)
    document = return_pieces(db, user, [line.article_size_id for line in chosen], note=person.full_name)
    now = datetime.now(timezone.utc)
    for line in chosen:
        line.returned_at = now
        line.return_document_id = document.id
    if all(line.returned_at is not None for line in lines.values()):
        handout.status = RETURNED
    if scan is not None:
        mark_used(db, scan, person.id)
    db.flush()
    return handout


def cancel_handout(db: Session, user: User, handout_id: int) -> AtelierHandout:
    """Uitgifte annuleren: undo a pick-up of which nothing was returned yet
    (its stock booking is reversed; the pick-up stays, marked cancelled)."""
    handout = _get_handout(db, handout_id)
    if handout.status != OPEN or any(line.returned_at is not None for line in _lines_of(db, handout.id)):
        raise StockError("cannot_cancel")
    document = db.get(AtelierStockDocument, handout.stock_document_id)
    reverse_document(db, user, document, note="Uitgifte geannuleerd", from_desk=True)
    handout.status = CANCELLED
    db.flush()
    return handout
