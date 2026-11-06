# Atelier's RFID pieces (block 6, used by the Raspberry Pi app): a clothing
# piece carries an RFID tag (TagScan's Tagscan_rfid_tag registry) that says
# which article size it is (RfidTag.atelier_article_size_id). The only place
# that links tags to Atelier pieces; the desk books them through
# desk_service.create_handout (rfid_tag_id per line) and the existing
# person-level return. Stock stays counted per article size: the tag only
# adds which physical piece is with whom.
#
# TagScan's tag register (Scans > Tagbeheer, Tagscan_rfid_tag) is the
# reference for every tag: linking creates or updates its row there, and every
# Pi action with a tag notes when and by which scanner it was last read
# (touch). A hand-out line keeps the EPC as a fixed reference (handout_epc,
# return_epc), so history() can trace a piece even after the tag changed.
#
# Nothing here commits: the router does.

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import belgian_today
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_handout import AtelierHandout
from app.db.models.atelier_handout_line import AtelierHandoutLine
from app.db.models.atelier_person import AtelierPerson
from app.db.models.atelier_return_status import AtelierReturnStatus
from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.festival import Festival
from app.db.models.atelier_size import AtelierSize
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.module_5.stock_service import StockError

# What a read EPC turned out to be (ResolvedTag.state):
UNKNOWN = "unknown"  # never registered
NOT_ATELIER = "not_atelier"  # a registered tag without an Atelier piece (free, or a StockMaster product / kar)
INACTIVE = "inactive"  # an Atelier piece whose tag is lost/damaged/retired
PIECE = "piece"  # an Atelier piece that can be booked

# The most EPCs one call may send (a counter reads a handful of pieces).
MAX_EPCS = 200


@dataclass
class Reader:
    """The RFID reader that read the tags: the Pi's scanner name and location
    (its settings screen), noted on the tags in TagScan's register."""

    name: str | None = None
    location: str | None = None


def touch(tag: RfidTag, reader: Reader | None) -> None:
    """Note on the tag's row in TagScan's register that this reader read it
    just now (nothing without a reader: e.g. the website's desk)."""
    if reader is None:
        return
    tag.last_read_at = datetime.now(timezone.utc)
    if reader.name:
        tag.last_reader_id = reader.name[:255]
    if reader.location:
        tag.last_location = reader.location[:255]


@dataclass
class ResolvedTag:
    """One read EPC with the Atelier piece behind it and, when the piece is
    out, the open hand-out line (and person) that has it."""

    epc: str
    state: str
    rfid_tag_id: int | None = None
    article_id: int | None = None
    article_name: str | None = None
    article_size_id: int | None = None
    size_name: str | None = None
    fit: str | None = None
    open_line_id: int | None = None
    person_id: int | None = None
    person_name: str | None = None
    # A registered tag that isn't an Atelier piece: what it belongs to ("Bekers",
    # "Kar 36"); None = free, so "Tags koppelen" may still link it.
    assigned_to: str | None = None


def clean_epcs(epcs: list[str]) -> list[str]:
    """The EPCs as stored by TagScan (trimmed), each once, in reading order;
    refused when there are too many."""
    cleaned = list(dict.fromkeys(epc.strip() for epc in epcs if epc and epc.strip()))
    if len(cleaned) > MAX_EPCS:
        raise StockError("too_many_tags", MAX_EPCS)
    return cleaned


def open_line_of_tag(db: Session, tag_id: int) -> AtelierHandoutLine | None:
    """The hand-out line that has this piece out right now (an open pick-up,
    not returned), if any."""
    return db.scalar(
        select(AtelierHandoutLine)
        .join(AtelierHandout, AtelierHandout.id == AtelierHandoutLine.handout_id)
        .where(
            AtelierHandoutLine.rfid_tag_id == tag_id,
            AtelierHandoutLine.returned_at.is_(None),
            AtelierHandout.status == "open",
        )
    )


def resolve(db: Session, epcs: list[str]) -> list[ResolvedTag]:
    """What each read EPC is: unknown, not an Atelier piece, an inactive
    piece, or a piece (with who has it, when it is out)."""
    cleaned = clean_epcs(epcs)
    tags = {tag.epc_uid: tag for tag in db.scalars(select(RfidTag).where(RfidTag.epc_uid.in_(cleaned))).all()} if cleaned else {}
    result = []
    for epc in cleaned:
        tag = tags.get(epc)
        if tag is None:
            result.append(ResolvedTag(epc=epc, state=UNKNOWN))
            continue
        if tag.atelier_article_size_id is None:
            result.append(ResolvedTag(epc=epc, state=NOT_ATELIER, rfid_tag_id=tag.id, assigned_to=_assigned_to(db, tag)))
            continue
        article_size = db.get(AtelierArticleSize, tag.atelier_article_size_id)
        article = db.get(AtelierArticle, article_size.article_id)
        size = db.get(AtelierSize, article_size.size_id)
        resolved = ResolvedTag(
            epc=epc,
            state=PIECE if tag.status == "active" else INACTIVE,
            rfid_tag_id=tag.id,
            article_id=article.id,
            article_name=article.name,
            article_size_id=article_size.id,
            size_name=size.name,
            fit=size.fit,
        )
        line = open_line_of_tag(db, tag.id)
        if line is not None:
            person = db.get(AtelierPerson, db.get(AtelierHandout, line.handout_id).person_id)
            resolved.open_line_id = line.id
            resolved.person_id = person.id
            resolved.person_name = person.full_name
        result.append(resolved)
    return result


def _assigned_to(db: Session, tag: RfidTag) -> str | None:
    """What a non-Atelier tag belongs to: its StockMaster product, else its kar."""
    if tag.assigned_product_id is not None:
        product = db.get(Product, tag.assigned_product_id)
        return product.name if product is not None else f"#{tag.assigned_product_id}"
    if tag.kar_id is not None:
        kar = db.get(KarTrackerKar, tag.kar_id)
        return f"Kar {kar.kar_nummer}" if kar is not None else f"Kar #{tag.kar_id}"
    return None


def _piece_label(db: Session, article_size_id: int) -> str:
    """"T-shirt M" — an article size as shown in an error."""
    article_size = db.get(AtelierArticleSize, article_size_id)
    return f"{db.get(AtelierArticle, article_size.article_id).name} {db.get(AtelierSize, article_size.size_id).name}"


def assign(
    db: Session, user: User, epcs: list[str], article_size_id: int, replace: bool = False, reader: Reader | None = None
) -> list[RfidTag]:
    """Tags koppelen: the read tags become pieces of this article size. A new
    EPC is registered in TagScan's registry; a known tag may not belong to a
    StockMaster product or kar, nor be out with someone. A tag already linked
    to another article size only changes with `replace` (the Pi asks)."""
    cleaned = clean_epcs(epcs)
    if not cleaned:
        raise StockError("no_tags")
    article_size = db.get(AtelierArticleSize, article_size_id)
    if article_size is None or not article_size.active:
        raise StockError("article_size_not_found", status_code=404)
    article = db.get(AtelierArticle, article_size.article_id)
    if article is None or not article.active:
        raise StockError("article_size_not_found", status_code=404)

    tags = []
    for epc in cleaned:
        tag = db.scalar(select(RfidTag).where(RfidTag.epc_uid == epc))
        if tag is None:
            # A new tag in TagScan's register, with who linked it and where.
            tag = RfidTag(
                epc_uid=epc,
                status="active",
                atelier_article_size_id=article_size.id,
                date_assigned=belgian_today(),
                notes_1=f"Gekoppeld via RWCrew Pi door {user.display_name}",
            )
            touch(tag, reader)
            db.add(tag)
            db.flush()
            tags.append(tag)
            continue
        if tag.assigned_product_id is not None or tag.kar_id is not None:
            raise StockError("tag_not_atelier", epc)
        if tag.atelier_article_size_id not in (None, article_size.id):
            line = open_line_of_tag(db, tag.id)
            if line is not None:
                person = db.get(AtelierPerson, db.get(AtelierHandout, line.handout_id).person_id)
                raise StockError("tag_out", epc, person.full_name)
            if not replace:
                raise StockError("tag_other_piece", epc, _piece_label(db, tag.atelier_article_size_id))
        tag.atelier_article_size_id = article_size.id
        tag.status = "active"
        tag.date_assigned = belgian_today()
        if not tag.notes_1:
            tag.notes_1 = f"Gekoppeld via RWCrew Pi door {user.display_name}"
        touch(tag, reader)
        tags.append(tag)
    db.flush()
    return tags


def check_handout_tags(db: Session, lines: list[tuple[int, int, int | None]]) -> None:
    """Ophalen with tags: each line's tag must be an active piece of exactly
    that article size, read only once, and not out with someone already."""
    tag_ids = [tag_id for _article, _size, tag_id in lines if tag_id is not None]
    if len(tag_ids) != len(set(tag_ids)):
        raise StockError("tag_twice")
    for _article_id, article_size_id, tag_id in lines:
        if tag_id is None:
            continue
        tag = db.get(RfidTag, tag_id)
        if tag is None or tag.atelier_article_size_id is None:
            raise StockError("tag_not_atelier", tag.epc_uid if tag else tag_id)
        if tag.status != "active":
            raise StockError("tag_inactive", tag.epc_uid)
        if tag.atelier_article_size_id != article_size_id:
            raise StockError("tag_size_mismatch", tag.epc_uid, _piece_label(db, tag.atelier_article_size_id))
        line = open_line_of_tag(db, tag.id)
        if line is not None:
            person = db.get(AtelierPerson, db.get(AtelierHandout, line.handout_id).person_id)
            raise StockError("tag_out", tag.epc_uid, person.full_name)


def check_return_tags(db: Session, lines: dict[int, AtelierHandoutLine], line_tags: dict[int, int]) -> dict[int, RfidTag]:
    """Terugbrengen with tags (the Pi): the tag read for a returned line must
    be an Atelier piece of that line's article (the size may differ from a
    piece that went out by size), and one tag can return only one line.
    Gives the tags by line id."""
    if len(set(line_tags.values())) != len(line_tags):
        raise StockError("tag_twice")
    tags = {}
    for line_id, tag_id in line_tags.items():
        line = lines.get(line_id)
        if line is None:
            raise StockError("tag_without_line")
        tag = db.get(RfidTag, tag_id)
        if tag is None or tag.atelier_article_size_id is None:
            raise StockError("tag_not_atelier", tag.epc_uid if tag else tag_id)
        if db.get(AtelierArticleSize, tag.atelier_article_size_id).article_id != line.article_id:
            raise StockError("tag_article_mismatch", tag.epc_uid, _piece_label(db, tag.atelier_article_size_id))
        tags[line_id] = tag
    return tags


@dataclass
class TagEvent:
    """One piece's journey in the trace: the hand-out and (when back) the return."""

    line_id: int
    handout_id: int
    person_name: str
    team_name: str
    festival_name: str
    day: date
    article_name: str
    size_name: str
    handed_out_at: datetime
    handed_out_by: str | None
    handout_source: str
    handout_epc: str | None
    returned_at: datetime | None = None
    returned_by: str | None = None
    return_source: str | None = None
    return_epc: str | None = None
    return_status: str | None = None
    # "out", "returned", "written_off" or "cancelled".
    state: str = "out"


@dataclass
class TagHistory:
    """A tag as TagScan's register knows it now, and every Atelier event of its EPC."""

    epc: str
    rfid_tag_id: int | None = None
    status: str | None = None
    piece: str | None = None
    last_read_at: datetime | None = None
    last_reader_id: str | None = None
    last_location: str | None = None
    events: list[TagEvent] = field(default_factory=list)


def history(db: Session, epc: str) -> TagHistory:
    """Everything the piece with this EPC went through at the Atelier desk:
    each hand-out line that went out or came back with this EPC, newest first."""
    epc = epc.strip()
    if not epc:
        raise StockError("no_tags")
    tag = db.scalar(select(RfidTag).where(RfidTag.epc_uid == epc))
    result = TagHistory(epc=epc)
    if tag is not None:
        result.rfid_tag_id = tag.id
        result.status = tag.status
        result.piece = _piece_label(db, tag.atelier_article_size_id) if tag.atelier_article_size_id else None
        result.last_read_at = tag.last_read_at
        result.last_reader_id = tag.last_reader_id
        result.last_location = tag.last_location
    lines = db.scalars(
        select(AtelierHandoutLine)
        .where((AtelierHandoutLine.handout_epc == epc) | (AtelierHandoutLine.return_epc == epc))
        .order_by(AtelierHandoutLine.id.desc())
    ).all()
    for line in lines:
        handout = db.get(AtelierHandout, line.handout_id)
        size = db.get(AtelierSize, db.get(AtelierArticleSize, line.article_size_id).size_id)
        event = TagEvent(
            line_id=line.id,
            handout_id=handout.id,
            person_name=db.get(AtelierPerson, handout.person_id).full_name,
            team_name=db.get(Team, handout.team_id).name,
            festival_name=db.get(Festival, handout.festival_id).name,
            day=handout.day,
            article_name=db.get(AtelierArticle, line.article_id).name,
            size_name=size.name,
            handed_out_at=handout.created_at,
            handed_out_by=handout.created_by_name,
            handout_source=handout.source,
            handout_epc=line.handout_epc,
        )
        if handout.status == "cancelled":
            event.state = "cancelled"
        elif line.returned_at is not None:
            document = db.get(AtelierStockDocument, line.return_document_id) if line.return_document_id else None
            event.state = "written_off" if document is not None and document.doc_type == "write_off" else "returned"
            event.returned_at = line.returned_at
            event.returned_by = document.created_by_name if document is not None else None
            event.return_source = line.return_source
            event.return_epc = line.return_epc
            if line.return_status_id:
                event.return_status = db.get(AtelierReturnStatus, line.return_status_id).name
        result.events.append(event)
    return result
