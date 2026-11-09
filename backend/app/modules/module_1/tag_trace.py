# Small helpers shared by every module that books with RFID tags read on the
# RWCrew Pi (Atelier's pieces in module_5/rfid_service.py, StockMaster's
# products in module_4/tag_service.py). They live here, next to TagScan's tag
# register (Tagscan_rfid_tag), because that register is the reference for
# every tag: each Pi action notes on the tag when and by which scanner it was
# last read.

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.models.rfid_tag import RfidTag


@dataclass
class Reader:
    """The RFID reader that read the tags: the Pi's scanner name and location
    (its settings screen), noted on the tags in TagScan's register."""

    name: str | None = None
    location: str | None = None


def touch(tag: RfidTag, reader: Reader | None) -> None:
    """Note on the tag's row in TagScan's register that this reader read it
    just now (nothing without a reader: e.g. a booking on the website)."""
    if reader is None:
        return
    tag.last_read_at = datetime.now(timezone.utc)
    if reader.name:
        tag.last_reader_id = reader.name[:255]
    if reader.location:
        tag.last_location = reader.location[:255]


def clean_epcs(epcs: list[str], limit: int, too_many: Callable[[int], Exception]) -> list[str]:
    """The EPCs as stored by TagScan (trimmed), each once, in reading order.
    More than `limit` raises the module's own error made by `too_many(limit)`
    (each module translates its own "too_many_tags")."""
    cleaned = list(dict.fromkeys(epc.strip() for epc in epcs if epc and epc.strip()))
    if len(cleaned) > limit:
        raise too_many(limit)
    return cleaned
