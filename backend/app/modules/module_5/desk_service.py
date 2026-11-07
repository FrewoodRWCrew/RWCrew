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
#   - the reservation's number of persons is a limit (decided 2026-11-07):
#     once as many people of the team at this festival hold clothing as
#     reserved, a new person is refused (reservation_full) unless a user with
#     "edit" on the desk confirms it; someone who brought everything back
#     frees a place (persons_holding);
#   - "Uitgifte annuleren" only while nothing of the pick-up was returned;
#   - a known person with another wristband at this festival needs a
#     confirmation (two people can share a name);
#   - a piece that never comes back is written off from Openstaand, which
#     closes its line like a return (its return document is the write-off);
#   - a piece read by its RFID tag (the Raspberry Pi app) must be a piece of
#     exactly the line's article size and not out with someone (rfid_service);
#     the line keeps the tag and its EPC, a return by tag keeps the tag read,
#     and every pick-up / return notes where it was booked ("web" / "pi").

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
from app.db.models.atelier_return_status import AtelierReturnStatus
from app.db.models.atelier_settings import AtelierSettings
from app.db.models.atelier_size import FITS, AtelierSize
from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.festival import Festival
from app.db.models.rfid_tag import RfidTag
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.wristband_scan import WristbandScan
from app.modules.module_5.reservation_service import festival_days, lines_by_reservation, reservations_by_team
from app.modules.module_5.deps import MODULE_KEY
from app.modules.module_5.rfid_service import Reader, check_handout_tags, check_return_tags, touch
from app.modules.wristband.scan_service import NEW, mark_used
from app.modules.module_5.stock_service import (
    AVAILABLE,
    StockError,
    all_balances,
    hand_out,
    return_pieces,
    reverse_document,
    write_off_handed_out,
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


def _waiting_scan(db: Session, scan_id: int | None) -> WristbandScan | None:
    """The scan a transaction came from (must still be waiting)."""
    if scan_id is None:
        return None
    scan = db.get(WristbandScan, scan_id)
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


def persons_holding(db: Session, festival_id: int, team_id: int) -> set[int]:
    """The people of the team at this festival who hold clothing right now
    (an open pick-up = at least one piece not returned)."""
    return set(
        db.scalars(
            select(AtelierHandout.person_id).where(
                AtelierHandout.festival_id == festival_id,
                AtelierHandout.team_id == team_id,
                AtelierHandout.status == OPEN,
            )
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
    confirm_new_bracelet: bool = False,
    booked_at: datetime | None = None,
    line_tags: dict[int, int] | None = None,
    source: str = "web",
    reader: Reader | None = None,
    confirm_over_reservation: bool = False,
) -> AtelierHandout:
    """Ophalen: hand out one piece of each chosen (article, article size) to
    a person, after checking the rules above; books available → handed out.
    `confirm_new_bracelet`: the desk confirmed this is the same person, with
    another wristband than the one known at this festival. `booked_at`: a
    back-dated pick-up (already checked by stock_service.check_booked_at).
    `line_tags`: per article the RFID tag of the piece read (the Raspberry Pi
    app), checked by rfid_service.check_handout_tags and kept on the line with
    its EPC. `source`: "web" or "pi"; `reader`: the Pi's scanner, noted on the
    tags in TagScan's register. `confirm_over_reservation`: a user with "edit"
    on the desk confirmed handing out beyond the reservation (the router
    checks that right)."""
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
    tags = line_tags or {}
    if not set(tags) <= set(article_ids):
        raise StockError("tag_without_line")
    check_handout_tags(db, [(article_id, article_size_id, tags.get(article_id)) for article_id, article_size_id in lines])

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

    # The reservation is full when as many people of the team hold clothing as
    # reserved; a person already holding something takes no extra place.
    # Back-dated loads of last year's lists are not limited.
    if booked_at is None and not confirm_over_reservation:
        holding = persons_holding(db, festival_id, team_id)
        reserved = reservations_by_team(db, festival_id)[team_id].persons
        if person.id not in holding and len(holding) >= reserved:
            raise StockError("reservation_full", team.name, len(holding), reserved)

    # The wristband number at this festival: a typed/scanned one is stored
    # (an empty field keeps the one already known); required when switched on.
    if bracelet_number is not None:
        known = bracelet_of(db, person.id, festival_id)
        if known is not None and known.number != bracelet_number and not confirm_new_bracelet:
            raise StockError("bracelet_differs", known.number, person.full_name)
        _set_bracelet(db, person, festival_id, bracelet_number)
    elif wristband_required(db) and bracelet_of(db, person.id, festival_id) is None:
        raise StockError("bracelet_required")

    document = hand_out(
        db, user, [article_size_id for _article, article_size_id in lines], note=person.full_name, booked_at=booked_at
    )
    # A back-dated pick-up keeps its own moment (otherwise the database's now).
    when = {"created_at": booked_at} if booked_at is not None else {}
    handout = AtelierHandout(
        **when,
        person_id=person.id,
        festival_id=festival_id,
        team_id=team_id,
        day=day,
        stock_document_id=document.id,
        status=OPEN,
        source=source,
        created_by=user.id,
        created_by_name=user.display_name,
    )
    db.add(handout)
    db.flush()
    for article_id, article_size_id in lines:
        tag = db.get(RfidTag, tags[article_id]) if article_id in tags else None
        if tag is not None:
            touch(tag, reader)
        db.add(
            AtelierHandoutLine(
                handout_id=handout.id,
                article_id=article_id,
                article_size_id=article_size_id,
                rfid_tag_id=tag.id if tag is not None else None,
                handout_epc=tag.epc_uid if tag is not None else None,
            )
        )
    if scan is not None:
        mark_used(db, scan, person.id, MODULE_KEY)
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


def _check_return_statuses(db: Session, line_ids: list[int], line_statuses: dict[int, int]) -> None:
    """A status only goes on a piece that is coming back, and must be active."""
    if not set(line_statuses) <= set(line_ids):
        raise StockError("return_status_invalid")
    for status_id in set(line_statuses.values()):
        return_status = db.get(AtelierReturnStatus, status_id)
        if return_status is None or not return_status.active:
            raise StockError("return_status_invalid")


def return_lines(
    db: Session,
    user: User,
    handout_id: int,
    line_ids: list[int],
    scan_id: int | None = None,
    line_statuses: dict[int, int] | None = None,
    booked_at: datetime | None = None,
    line_tags: dict[int, int] | None = None,
    source: str = "web",
    reader: Reader | None = None,
) -> AtelierHandout:
    """Terugbrengen: the ticked pieces come back (handed out → to wash). The
    pick-up is "returned" once every piece is back. A scan the return came
    from is marked used. `line_statuses` notes what was wrong with a piece
    (only a remark: the stock booking stays the same). `booked_at`: a
    back-dated return (already checked). `line_tags`: per line the RFID tag
    read when it came back (the Pi; kept with its EPC). `source`: "web" or
    "pi"; `reader`: the Pi's scanner, noted on the tags."""
    statuses = line_statuses or {}
    _check_return_statuses(db, line_ids, statuses)
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
    returned_tags = check_return_tags(db, {line.id: line for line in chosen}, line_tags or {})

    person = db.get(AtelierPerson, handout.person_id)
    document = return_pieces(
        db, user, [line.article_size_id for line in chosen], note=person.full_name, booked_at=booked_at
    )
    now = booked_at or datetime.now(timezone.utc)
    for line in chosen:
        line.returned_at = now
        line.return_document_id = document.id
        line.return_status_id = statuses.get(line.id)
        line.return_source = source
        tag = returned_tags.get(line.id)
        if tag is not None:
            line.return_rfid_tag_id = tag.id
            line.return_epc = tag.epc_uid
            touch(tag, reader)
    if all(line.returned_at is not None for line in lines.values()):
        handout.status = RETURNED
    if scan is not None:
        mark_used(db, scan, person.id, MODULE_KEY)
    db.flush()
    return handout


def _person_lines(
    db: Session, person_id: int, line_ids: list[int]
) -> tuple[list[AtelierHandout], list[AtelierHandoutLine]]:
    """The ticked pieces of one person (by id) and their pick-ups (oldest
    first); refused when a piece isn't theirs."""
    if db.get(AtelierPerson, person_id) is None:
        raise StockError("person_not_found", status_code=404)
    wanted = set(line_ids)
    if not wanted:
        raise StockError("line_not_found", status_code=404)
    lines = db.scalars(select(AtelierHandoutLine).where(AtelierHandoutLine.id.in_(wanted))).all()
    if len(lines) != len(wanted):
        raise StockError("line_not_found", status_code=404)
    handouts = [_get_handout(db, handout_id) for handout_id in sorted({line.handout_id for line in lines})]
    if any(handout.person_id != person_id for handout in handouts):
        raise StockError("line_not_found", status_code=404)
    return handouts, sorted(lines, key=lambda line: line.id)


def return_person_lines(
    db: Session,
    user: User,
    person_id: int,
    line_ids: list[int],
    scan_id: int | None = None,
    line_statuses: dict[int, int] | None = None,
    booked_at: datetime | None = None,
    line_tags: dict[int, int] | None = None,
    source: str = "web",
    reader: Reader | None = None,
) -> tuple[list[AtelierHandout], list[AtelierHandoutLine]]:
    """Terugbrengen of one person in one go: the ticked pieces may belong to
    several of their open pick-ups (one return booking per pick-up, as with
    return_lines). Gives the pick-ups touched (oldest first) and the pieces
    returned, so the desk can send one mail for the whole transaction."""
    statuses = line_statuses or {}
    _check_return_statuses(db, line_ids, statuses)
    # A tag read can only go with a piece that comes back.
    if not set(line_tags or {}) <= set(line_ids):
        raise StockError("tag_without_line")
    handouts, lines = _person_lines(db, person_id, line_ids)

    # The scan (if any) goes with the first booking only: it can be used once.
    for index, handout in enumerate(handouts):
        handout_lines = [line.id for line in lines if line.handout_id == handout.id]
        handout_statuses = {line_id: statuses[line_id] for line_id in handout_lines if line_id in statuses}
        handout_tags = {line_id: tag_id for line_id, tag_id in (line_tags or {}).items() if line_id in handout_lines}
        return_lines(
            db, user, handout.id, handout_lines, scan_id if index == 0 else None, handout_statuses, booked_at=booked_at,
            line_tags=handout_tags, source=source, reader=reader,
        )
    return handouts, lines


def write_off_person_lines(
    db: Session,
    user: User,
    person_id: int,
    line_ids: list[int],
    note: str | None = None,
    booked_at: datetime | None = None,
) -> list[AtelierHandout]:
    """Openstaand's Afboeken: the ticked pieces of one person never came back.
    One write-off booking; each piece's line is closed (so the person can get
    that article again) and a pick-up with every piece closed is "returned".
    No mail, and no return status: the piece isn't a Retourprobleem."""
    handouts, lines = _person_lines(db, person_id, line_ids)
    if any(handout.status != OPEN for handout in handouts):
        raise StockError("handout_closed")
    if any(line.returned_at is not None for line in lines):
        raise StockError("already_returned")

    person = db.get(AtelierPerson, person_id)
    text = " — ".join(part for part in (person.full_name, (note or "").strip()) if part)
    document = write_off_handed_out(db, user, [line.article_size_id for line in lines], note=text, booked_at=booked_at)
    now = booked_at or datetime.now(timezone.utc)
    for line in lines:
        line.returned_at = now
        line.return_document_id = document.id
    db.flush()
    for handout in handouts:
        if all(line.returned_at is not None for line in _lines_of(db, handout.id)):
            handout.status = RETURNED
    db.flush()
    return handouts


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
