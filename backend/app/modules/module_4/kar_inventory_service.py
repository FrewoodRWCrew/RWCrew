# StockMaster's "Kar inventaris": a team counts what is in its own kar at the
# end of a festival, before the kar is picked up. The team reaches it without
# an RWCrew login through the karblad's QR code (public kar page) and unlocks
# the kar with its lock code (KarTracker_karren.kar_code, only the team knows
# it). The public endpoints are in public_kar_inventory_router.py, the staff
# list in kar_inventory_router.py.
#
# Purely informative: this module never books or changes stock, tags or trips.
# It is the only writer of StockMaster_kar_inventory(_line).

import hashlib
import secrets
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.product import Product
from app.db.models.season import Season
from app.db.models.stockmaster_kar_inventory import StockMasterKarInventory
from app.db.models.stockmaster_kar_inventory_line import StockMasterKarInventoryLine
from app.db.models.stockmaster_kar_trip import StockMasterKarTrip
from app.db.models.team import Team
from app.modules.module_4.stock_queries import load_stock
from app.modules.module_4.stock_service import StockError, dispatched_lines, open_trip_of
from app.modules.wristband.visibility import default_season_id
from app.schemas.stockmaster import (
    KarInventoryCreateRequest,
    KarInventoryLineResponse,
    KarInventoryResponse,
)

# How long an unlocked kar stays open on the phone before the code is asked again.
TOKEN_LIFETIME = timedelta(hours=2)
# The token's type claim, so a login token can never be used here (and the reverse).
_TOKEN_TYPE = "kar_inventory"
# How many earlier inventories the public screen shows.
HISTORY_LIMIT = 20


# --- Finding the kar and checking its code ----------------------------------


def normalize_kar_nummer(value: str) -> str:
    """A kar number as typed or scanned, for comparing: trimmed, upper case."""
    return value.strip().upper()


def find_kar(db: Session, kar_nummer: str) -> KarTrackerKar | None:
    """The kar with this number (ignoring case and spaces around it)."""
    return db.scalar(
        select(KarTrackerKar).where(func.upper(func.trim(KarTrackerKar.kar_nummer)) == normalize_kar_nummer(kar_nummer))
    )


def _code_fingerprint(code: str) -> str:
    """A short hash of the lock code, put in the token so changing the code on
    KarManagement ends every open session of that kar."""
    return hashlib.sha256(f"{settings.jwt_secret}|{code}".encode()).hexdigest()[:16]


def code_matches(kar: KarTrackerKar, code: str) -> bool:
    """True when the typed code is the kar's lock code (spaces around it ignored).
    A kar without a code can't be unlocked; the caller reports that first."""
    stored = (kar.kar_code or "").strip()
    return bool(stored) and secrets.compare_digest(stored.encode(), code.strip().encode())


def create_token(kar: KarTrackerKar) -> str:
    """A signed token that opens this one kar's inventory for TOKEN_LIFETIME."""
    now = datetime.now(timezone.utc)
    payload = {
        "typ": _TOKEN_TYPE,
        "kar": kar.id,
        "kc": _code_fingerprint((kar.kar_code or "").strip()),
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def kar_from_token(db: Session, token: str | None) -> KarTrackerKar:
    """The kar a token opens. 401 `token_invalid` when it is missing, expired,
    of another type, for a deleted kar or made with an old lock code."""
    if not token:
        raise StockError("token_invalid", status_code=401)
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as error:
        raise StockError("token_invalid", status_code=401) from error
    if payload.get("typ") != _TOKEN_TYPE or not isinstance(payload.get("kar"), int):
        raise StockError("token_invalid", status_code=401)
    kar = db.get(KarTrackerKar, payload["kar"])
    if kar is None or payload.get("kc") != _code_fingerprint((kar.kar_code or "").strip()):
        raise StockError("token_invalid", status_code=401)
    return kar


# --- What should be in the kar -----------------------------------------------


@dataclass
class KarExpectation:
    """What should be in the kar now: {product_id: pieces}, and the open trip
    it is counted against (None = the kar stands in the warehouse)."""

    trip: StockMasterKarTrip | None
    quantities: dict[int, int]


def expected_contents(db: Session, kar: KarTrackerKar) -> KarExpectation:
    """While the kar is out: everything that left with it (Kar vertrekt plus
    the follow-up deliveries). In the warehouse: what it holds there."""
    trip = open_trip_of(db, kar.id)
    if trip is not None:
        quantities = dispatched_lines(db, trip)
    else:
        quantities = load_stock(db).kar_contents(kar.id)
    return KarExpectation(trip=trip, quantities={pid: qty for pid, qty in quantities.items() if qty > 0})


def season_of(db: Session, expectation: KarExpectation) -> int | None:
    """The season an inventory belongs to: the trip's, else the last open one."""
    if expectation.trip is not None:
        return expectation.trip.season_id
    return default_season_id(db)


def products_by_id(db: Session, product_ids: set[int]) -> dict[int, Product]:
    """The products by id (only those that still exist)."""
    if not product_ids:
        return {}
    return {product.id: product for product in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()}


def search_products(db: Session, query: str = "", limit: int = 1000) -> list[Product]:
    """Products the team can add as an extra line: not blocked, alphabetical;
    with a text only those whose name contains it (ignoring case). The public
    screen loads the whole list once and filters while typing."""
    statement = select(Product).where(Product.is_blocked.is_(False)).order_by(Product.name).limit(limit)
    text = query.strip()
    if text:
        statement = statement.where(func.lower(Product.name).like(f"%{text.lower()}%"))
    return list(db.scalars(statement).all())


# --- Saving ------------------------------------------------------------------


def create_inventory(
    db: Session, kar: KarTrackerKar, payload: KarInventoryCreateRequest, client_ip: str | None
) -> StockMasterKarInventory:
    """Store one inventory. `expected` is worked out here again (never taken
    from the phone). Every product of the kar's list must be counted (0 is a
    count); extra lines are products not on the list. Doesn't commit."""
    name = payload.counted_by_name.strip()
    if not name:
        raise StockError("name_required")
    expectation = expected_contents(db, kar)
    expected = expectation.quantities

    # Each product once, over both lists.
    seen: set[int] = set()
    for line in [*payload.lines, *payload.extra]:
        if line.product_id in seen:
            raise StockError("duplicate_product", line.product_id)
        seen.add(line.product_id)

    products = products_by_id(db, set(expected) | seen)
    counted = {line.product_id: line.counted for line in payload.lines}
    # A line for a product that isn't (or no longer) on the list: the list changed
    # since the screen was opened (e.g. a follow-up delivery) — reload and count again.
    for product_id in counted:
        if product_id not in expected:
            raise StockError("list_changed")
    # Every product on the list needs a count.
    for product_id in expected:
        if product_id not in counted:
            product = products.get(product_id)
            raise StockError("line_missing", product.name if product else product_id)
    # Extra products must exist, not be on the list and not be blocked.
    for line in payload.extra:
        product = products.get(line.product_id)
        if product is None or product.is_blocked:
            raise StockError("unknown_product", line.product_id)
        if line.product_id in expected:
            raise StockError("list_changed")

    team = db.get(Team, kar.team_id) if kar.team_id else None
    remark = (payload.remark or "").strip() or None
    inventory = StockMasterKarInventory(
        kar_id=kar.id,
        kar_nummer=kar.kar_nummer,
        season_id=season_of(db, expectation),
        team_id=team.id if team else None,
        team_name=team.name if team else None,
        trip_id=expectation.trip.id if expectation.trip else None,
        counted_by_name=name,
        remark=remark,
        client_ip=client_ip,
    )
    db.add(inventory)
    db.flush()

    # The list's lines in name order, then the extra ones.
    listed = sorted(expected, key=lambda pid: products[pid].name.lower() if pid in products else "")
    for product_id in listed:
        db.add(
            StockMasterKarInventoryLine(
                inventory_id=inventory.id,
                product_id=product_id if product_id in products else None,
                product_name=products[product_id].name if product_id in products else f"#{product_id}",
                expected=expected[product_id],
                counted=counted[product_id],
                is_extra=False,
            )
        )
    for line in payload.extra:
        db.add(
            StockMasterKarInventoryLine(
                inventory_id=inventory.id,
                product_id=line.product_id,
                product_name=products[line.product_id].name,
                expected=0,
                counted=line.counted,
                is_extra=True,
            )
        )
    db.flush()
    return inventory


# --- Reading -------------------------------------------------------------------


def list_inventories(
    db: Session,
    *,
    season_id: int | None = None,
    kar_id: int | None = None,
    ids: set[int] | None = None,
    limit: int | None = None,
) -> list[StockMasterKarInventory]:
    """Inventories newest first, optionally of one season, one kar and/or only these ids."""
    query = select(StockMasterKarInventory).order_by(
        StockMasterKarInventory.created_at.desc(), StockMasterKarInventory.id.desc()
    )
    if season_id is not None:
        query = query.where(StockMasterKarInventory.season_id == season_id)
    if kar_id is not None:
        query = query.where(StockMasterKarInventory.kar_id == kar_id)
    if ids is not None:
        query = query.where(StockMasterKarInventory.id.in_(ids))
    if limit is not None:
        query = query.limit(limit)
    return list(db.scalars(query).all())


def get_inventory(db: Session, inventory_id: int) -> StockMasterKarInventory:
    """One inventory, or 404 `inventory_not_found`."""
    inventory = db.get(StockMasterKarInventory, inventory_id)
    if inventory is None:
        raise StockError("inventory_not_found", status_code=404)
    return inventory


def to_responses(db: Session, inventories: list[StockMasterKarInventory]) -> list[KarInventoryResponse]:
    """Inventories with their lines, season names and totals."""
    ids = [inventory.id for inventory in inventories]
    lines: dict[int, list[StockMasterKarInventoryLine]] = defaultdict(list)
    if ids:
        for line in db.scalars(
            select(StockMasterKarInventoryLine)
            .where(StockMasterKarInventoryLine.inventory_id.in_(ids))
            .order_by(StockMasterKarInventoryLine.id)
        ).all():
            lines[line.inventory_id].append(line)
    season_ids = {inventory.season_id for inventory in inventories if inventory.season_id}
    seasons = (
        {season.id: season.name for season in db.scalars(select(Season).where(Season.id.in_(season_ids))).all()}
        if season_ids
        else {}
    )
    return [
        KarInventoryResponse(
            id=inventory.id,
            kar_id=inventory.kar_id,
            kar_nummer=inventory.kar_nummer,
            season_id=inventory.season_id,
            season_name=seasons.get(inventory.season_id) if inventory.season_id else None,
            team_name=inventory.team_name,
            counted_by_name=inventory.counted_by_name,
            remark=inventory.remark,
            created_at=inventory.created_at,
            total_expected=sum(line.expected for line in lines[inventory.id]),
            total_counted=sum(line.counted for line in lines[inventory.id]),
            lines=[KarInventoryLineResponse.model_validate(line) for line in lines[inventory.id]],
        )
        for inventory in inventories
    ]


def season_name(db: Session, season_id: int | None) -> str | None:
    """A season's name (None without one)."""
    season = db.get(Season, season_id) if season_id else None
    return season.name if season else None
