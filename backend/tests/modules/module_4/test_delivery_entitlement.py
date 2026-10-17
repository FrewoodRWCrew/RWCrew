# The flow diagram behind Kar laden's "Op dit moment beschikbaar voor levering"
# (app/modules/module_4/delivery_entitlement.py): each branch on its own, and
# the kar detail that fills `entitled` + the trace on every row.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.product import Product
from app.db.models.product_limit import ProductLimit
from app.modules.module_4.delivery_entitlement import delivery_entitlement, limit_kind
from tests.modules.module_4.conftest import BASE, StockWorld, book


def _product(**fields) -> Product:
    """An unsaved product with the flags the diagram looks at."""
    defaults = {"name": "P", "is_blocked": False, "is_logistics_product": False, "limit_value": None, "max_initial_stock": None}
    return Product(**{**defaults, **fields})


def _run(product: Product, limit: str | None, requested: int = 10, stock: int = 100, demand: int = 50,
         status: str | None = "Beschikbaar", cap_used: int = 0):
    """The diagram for one row."""
    return delivery_entitlement(product, limit, requested, stock, demand, status, cap_used)


def test_limit_names_map_to_rules() -> None:
    assert limit_kind("Automatisch") == "automatic"
    assert limit_kind("  toegewezen   AANTAL ") == "assigned"
    assert limit_kind("Percentage") == "percentage"
    assert limit_kind("Ongelimiteerd") == "unlimited"
    # No Limiet, or a name the diagram doesn't know: no limit.
    assert limit_kind(None) == "unlimited"
    assert limit_kind("Iets anders") == "unlimited"


def test_blocked_and_logistics_come_first() -> None:
    blocked = _run(_product(is_blocked=True, is_logistics_product=True), "Percentage")
    assert (blocked.entitled, blocked.path) == (0, ["blocked:yes", "result:zero"])

    logistics = _run(_product(is_logistics_product=True, max_initial_stock=2), "Percentage")
    assert (logistics.entitled, logistics.path) == (10, ["blocked:no", "logistics:yes", "result:logistics"])


def test_unlimited_gives_what_was_asked() -> None:
    trace = _run(_product(max_initial_stock=2), "Ongelimiteerd")
    assert trace.entitled == 10
    assert trace.path[-1] == "result:unlimited"


def test_automatic_enough_stock_gives_what_was_asked_without_cap() -> None:
    trace = _run(_product(max_initial_stock=2), "Automatisch", stock=60, demand=50)
    assert trace.entitled == 10
    assert trace.path[-2:] == ["shortage:no", "result:automatic_enough"]


def test_automatic_short_gives_a_rounded_down_share_capped_until_delivered() -> None:
    # 7 asked, 60 in stock for 100 asked in all: 60 % of 7 = 4.2 → 4.
    trace = _run(_product(), "Automatisch", requested=7, stock=60, demand=100)
    assert (trace.share_percent, trace.before_cap, trace.entitled) == (60.0, 4, 4)
    assert trace.path[-4:] == ["shortage:yes", "calc:share", "delivered:no", "result:automatic_capped"]

    capped = _run(_product(max_initial_stock=3), "Automatisch", requested=7, stock=60, demand=100)
    assert (capped.before_cap, capped.entitled) == (4, 3)

    delivered = _run(_product(max_initial_stock=3), "Automatisch", requested=7, stock=60, demand=100, status="geleverd")
    assert delivered.entitled == 4
    assert delivered.path[-2:] == ["delivered:yes", "result:automatic"]


def test_percentage_rounds_down_and_caps() -> None:
    trace = _run(_product(limit_value=50), "Percentage", requested=7)
    assert (trace.before_cap, trace.entitled) == (3, 3)
    assert _run(_product(limit_value=50, max_initial_stock=2), "Percentage", requested=7).entitled == 2
    assert _run(_product(limit_value=50, max_initial_stock=2), "Percentage", requested=7, status="Geleverd").entitled == 3
    # Without a Limietwaarde nothing is taken off.
    assert _run(_product(), "Percentage", requested=7).entitled == 7


def test_assigned_caps_until_delivered_and_shares_the_cap() -> None:
    product = _product(max_initial_stock=5)
    assert _run(product, "Toegewezen aantal", requested=8).entitled == 5
    assert _run(product, "Toegewezen aantal", requested=8, status="Geleverd").entitled == 8
    # A Manueel row only gets what the Altsien row left of the maximum.
    manual = _run(product, "Toegewezen aantal", requested=4, cap_used=3)
    assert (manual.entitled, manual.cap_used_by_other_row) == (2, 3)
    assert _run(product, "Toegewezen aantal", requested=4, cap_used=6).entitled == 0


def test_kar_detail_fills_entitlement_per_row(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    # Tape: Automatisch, 12 in stock; 10 needed on K101 and 10 on K043, 4 asked by hand on K101 → 24 asked.
    limit = ProductLimit(name="Automatisch")
    db_session.add(limit)
    db_session.flush()
    tape = db_session.get(Product, world.tape.id)
    tape.limit_id = limit.id
    tape.max_initial_stock = 4
    db_session.commit()
    book(as_warehouse, world, "book_in", [(world.tape.id, 12)])
    for kar in (world.k101, world.k043):
        as_warehouse.put(
            f"{BASE}/requirements",
            json={"season_id": world.season.id, "kar_id": kar.id, "lines": [{"product_id": world.tape.id, "quantity": 10}]},
        )
    as_warehouse.post(
        f"{BASE}/kars/{world.k101.id}/manual-requests",
        json={"season_id": world.season.id, "product_id": world.tape.id, "quantity": 4},
    )

    def detail() -> dict:
        return as_warehouse.get(f"{BASE}/kars/{world.k101.id}", params={"season_id": world.season.id}).json()

    data = detail()
    line = next(line for line in data["lines"] if line["name"] == "Tape")
    trace = line["entitlement_trace"]
    # 12 for 24 asked = 50 %: 10 → 5, capped at Maximum initiële stock 4.
    assert (trace["total_stock"], trace["season_demand"], trace["before_cap"], line["entitled"]) == (12, 24, 5, 4)
    # The Manueel row: 50 % of 4 = 2, but the Altsien row already used the whole maximum.
    manual = data["manual_requests"][0]
    assert (manual["entitlement_trace"]["before_cap"], manual["entitled"]) == (2, 0)

    # Once the kar is "Geleverd" the maximum no longer applies.
    delivered = KarTrackerKarStatus(name="Geleverd")
    db_session.add(delivered)
    db_session.flush()
    db_session.get(type(world.k101), world.k101.id).status_id = delivered.id
    db_session.commit()
    data = detail()
    assert next(line for line in data["lines"] if line["name"] == "Tape")["entitled"] == 5
    assert data["manual_requests"][0]["entitled"] == 2
