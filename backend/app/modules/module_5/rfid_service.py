# Atelier's RFID pieces (block 6, used by the Raspberry Pi app): a clothing
# piece carries an RFID tag (TagScan's Tagscan_rfid_tag registry) that says
# which article size it is (RfidTag.atelier_article_size_id). The only place
# that links tags to Atelier pieces; the desk books them through
# desk_service.create_handout (rfid_tag_id per line) and the existing
# person-level return. Stock stays counted per article size: the tag only
# adds which physical piece is with whom.
#
# Nothing here commits: the router does.

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import belgian_today
from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_handout import AtelierHandout
from app.db.models.atelier_handout_line import AtelierHandoutLine
from app.db.models.atelier_person import AtelierPerson
from app.db.models.atelier_size import AtelierSize
from app.db.models.rfid_tag import RfidTag
from app.db.models.user import User
from app.modules.module_5.stock_service import StockError

# What a read EPC turned out to be (ResolvedTag.state):
UNKNOWN = "unknown"  # never registered
NOT_ATELIER = "not_atelier"  # a registered tag without an Atelier piece (e.g. a StockMaster product or kar)
INACTIVE = "inactive"  # an Atelier piece whose tag is lost/damaged/retired
PIECE = "piece"  # an Atelier piece that can be booked

# The most EPCs one call may send (a counter reads a handful of pieces).
MAX_EPCS = 200


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
            result.append(ResolvedTag(epc=epc, state=NOT_ATELIER, rfid_tag_id=tag.id))
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


def _piece_label(db: Session, article_size_id: int) -> str:
    """"T-shirt M" — an article size as shown in an error."""
    article_size = db.get(AtelierArticleSize, article_size_id)
    return f"{db.get(AtelierArticle, article_size.article_id).name} {db.get(AtelierSize, article_size.size_id).name}"


def assign(db: Session, user: User, epcs: list[str], article_size_id: int, replace: bool = False) -> list[RfidTag]:
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
            # A new tag, registered with who and where it was linked.
            tag = RfidTag(
                epc_uid=epc,
                status="active",
                atelier_article_size_id=article_size.id,
                date_assigned=belgian_today(),
                last_reader_id=user.display_name,
            )
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
