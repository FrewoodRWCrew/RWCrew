# Atelier's stock (block 3): receipts, washing, write-offs, counts, undo,
# the never-negative rule, the session user on bookings, the error codes,
# the rights, the shortage on Voorbereiden, Te bestellen, the minimum-stock
# warnings and the PDFs.

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.user import User
from app.modules.module_5.stock_service import (
    TO_WASH,
    StockError,
    StockLine,
    _Move,
    _new_document,
    _post_moves,
    receive,
    write_off,
)

# The block-1 fixtures and helpers (module, seasons, teams, sizes, a user with every right).
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    _create_article,
    _login,
    _make_role,
    _make_user,
    _size_id,
    as_atelier,
    world,
)


@pytest.fixture()
def tshirt(as_atelier: TestClient, world: dict) -> dict:
    """A T-shirt in M-men (min stock 5) and L-men, split 50/50."""
    article = as_atelier.post(
        f"{BASE}/articles",
        json={
            "code": "TS",
            "name": "T-shirt",
            "sizes": [
                {"size_id": _size_id(world, "M", "men"), "min_stock": 5, "size_share_pct": 50},
                {"size_id": _size_id(world, "L", "men"), "size_share_pct": 50},
            ],
        },
    ).json()
    m, l = (row["id"] for row in article["sizes"])
    return {"article": article["id"], "m": m, "l": l}


def _stock(client: TestClient, article_size_id: int) -> tuple[int, int, int]:
    """(available, to wash, handed out) of one article size."""
    for article in client.get(f"{BASE}/stock").json():
        for size in article["sizes"]:
            if size["article_size_id"] == article_size_id:
                return size["available"], size["to_wash"], size["handed_out"]
    raise AssertionError("article size not on the stock overview")


def _put_to_wash(db_session: Session, world: dict, article_size_id: int, quantity: int) -> None:
    """Pieces come back from a shift (block 4 will book that): put them
    straight in "to wash" with a low-level booking."""
    booker = db_session.scalar(select(User))
    document = _new_document(db_session, booker, "receipt")
    _post_moves(db_session, document, [_Move(article_size_id, quantity, None, TO_WASH)])
    db_session.commit()


def test_receipt_wash_write_off_and_count(as_atelier: TestClient, db_session: Session, world: dict, tshirt: dict) -> None:
    # Ontvangst: 10 M + 4 L become available; the booker is the session user.
    response = as_atelier.post(
        f"{BASE}/stock/receipt",
        json={"lines": [{"article_size_id": tshirt["m"], "quantity": 6}, {"article_size_id": tshirt["m"], "quantity": 4},
                        {"article_size_id": tshirt["l"], "quantity": 4}], "reference": "Levering 1"},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["doc_number"].startswith("AT-") and document["created_by_name"] == "atelier@example.com"
    # The two M lines were merged into one ledger line.
    assert [(line["size_name"], line["quantity"]) for line in document["movements"]] == [("M", 10), ("L", 4)]
    assert _stock(as_atelier, tshirt["m"]) == (10, 0, 0)

    # Wassen: only what is "to wash" can be washed.
    _put_to_wash(db_session, world, tshirt["m"], 3)
    refused = as_atelier.post(f"{BASE}/stock/wash", json={"lines": [{"article_size_id": tshirt["m"], "quantity": 4}]})
    assert refused.status_code == 400 and refused.json()["detail"].startswith("insufficient_stock|")
    assert as_atelier.post(f"{BASE}/stock/wash", json={"lines": [{"article_size_id": tshirt["m"], "quantity": 3}]}).status_code == 201
    assert _stock(as_atelier, tshirt["m"]) == (13, 0, 0)

    # Afboeken: a reason is needed, "other" needs a note, never more than present.
    line = {"article_size_id": tshirt["l"], "quantity": 1, "from_status": "available"}
    assert as_atelier.post(f"{BASE}/stock/write-off", json={"lines": [line], "reason": "other"}).json()["detail"] == "note_required"
    too_many = {**line, "quantity": 9}
    assert as_atelier.post(f"{BASE}/stock/write-off", json={"lines": [too_many], "reason": "lost"}).status_code == 400
    assert as_atelier.post(f"{BASE}/stock/write-off", json={"lines": [line], "reason": "damaged"}).status_code == 201
    assert _stock(as_atelier, tshirt["l"]) == (3, 0, 0)

    # Telling: only differences are booked; no differences is refused.
    count = {"lines": [{"article_size_id": tshirt["m"], "status": "available", "counted": 12},
                       {"article_size_id": tshirt["l"], "status": "available", "counted": 3}]}
    counted = as_atelier.post(f"{BASE}/stock/count", json=count).json()
    assert [(move["size_name"], move["from_status"], move["to_status"], move["quantity"]) for move in counted["movements"]] == [
        ("M", "available", None, 1)
    ]
    assert as_atelier.post(f"{BASE}/stock/count", json=count).json()["detail"] == "no_differences"


def test_undo_by_counter_booking(as_atelier: TestClient, tshirt: dict) -> None:
    receipt = as_atelier.post(f"{BASE}/stock/receipt", json={"lines": [{"article_size_id": tshirt["m"], "quantity": 5}]}).json()
    write = as_atelier.post(
        f"{BASE}/stock/write-off",
        json={"lines": [{"article_size_id": tshirt["m"], "quantity": 4, "from_status": "available"}], "reason": "lost"},
    ).json()

    # The receipt can't be undone while its pieces are gone ...
    refused = as_atelier.post(f"{BASE}/stock/documents/{receipt['id']}/reverse", json={})
    assert refused.status_code == 400 and refused.json()["detail"].startswith("insufficient_stock|")
    # ... until the write-off is undone first.
    reversal = as_atelier.post(f"{BASE}/stock/documents/{write['id']}/reverse", json={"note": "toch gevonden"}).json()
    assert reversal["doc_type"] == "reversal" and reversal["reversal_of_number"] == write["doc_number"]
    assert as_atelier.post(f"{BASE}/stock/documents/{write['id']}/reverse", json={}).json()["detail"] == "already_reversed"
    assert as_atelier.post(f"{BASE}/stock/documents/{reversal['id']}/reverse", json={}).json()["detail"] == "cannot_reverse_reversal"
    assert as_atelier.post(f"{BASE}/stock/documents/{receipt['id']}/reverse", json={}).status_code == 200
    assert _stock(as_atelier, tshirt["m"]) == (0, 0, 0)

    # History: newest first, the original marked reversed, filter by type.
    history = as_atelier.get(f"{BASE}/stock/documents").json()
    assert [doc["doc_type"] for doc in history] == ["reversal", "reversal", "write_off", "receipt"]
    assert history[-1]["status"] == "reversed" and history[-1]["reversed_by_number"] == history[0]["doc_number"]
    assert len(as_atelier.get(f"{BASE}/stock/documents", params={"doc_type": "receipt"}).json()) == 1
    pdf = as_atelier.get(f"{BASE}/stock/documents/{receipt['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_inactive_size_cant_be_received_and_history_protects_it(
    as_atelier: TestClient, world: dict, tshirt: dict
) -> None:
    as_atelier.post(f"{BASE}/stock/receipt", json={"lines": [{"article_size_id": tshirt["m"], "quantity": 1}]})
    # A size with stock bookings can't be unticked, and the article can't be deleted.
    only_l = {"code": "TS", "name": "T-shirt", "sizes": [{"size_id": _size_id(world, "L", "men")}]}
    assert as_atelier.put(f"{BASE}/articles/{tshirt['article']}", json=only_l).status_code == 400
    assert as_atelier.delete(f"{BASE}/articles/{tshirt['article']}").status_code == 400
    # An inactive article can't receive new pieces.
    as_atelier.put(
        f"{BASE}/articles/{tshirt['article']}",
        json={"code": "TS", "name": "T-shirt", "active": False,
              "sizes": [{"size_id": _size_id(world, "M", "men")}, {"size_id": _size_id(world, "L", "men")}]},
    )
    refused = as_atelier.post(f"{BASE}/stock/receipt", json={"lines": [{"article_size_id": tshirt["l"], "quantity": 1}]})
    assert refused.json()["detail"].startswith("article_size_inactive|")


def test_shortage_order_needs_and_min_stock(
    as_atelier: TestClient, db_session: Session, world: dict, tshirt: dict
) -> None:
    season = world["season"]
    rw = Festival(name="Rock Werchter", start_date=date(2026, 7, 2), end_date=date(2026, 7, 5), season_id=season.id)
    tw = Festival(name="TW Classic", start_date=date(2026, 6, 20), end_date=date(2026, 6, 20), season_id=season.id)
    db_session.add_all([rw, tw])
    db_session.commit()
    # RW: 20 persons × 1 T-shirt = 20 a day (10 M + 10 L); TW: 6 persons = 6 (3 M + 3 L).
    for festival, persons in ((rw, 20), (tw, 6)):
        as_atelier.put(
            f"{BASE}/reservations/{festival.id}",
            json={"reservations": [{"team_id": world["terras"].id, "persons": persons,
                                    "lines": [{"article_id": tshirt["article"], "quantity_per_person": 1}]}]},
        )
    as_atelier.post(f"{BASE}/stock/receipt", json={"lines": [{"article_size_id": tshirt["m"], "quantity": 4},
                                                              {"article_size_id": tshirt["l"], "quantity": 12}]})
    _put_to_wash(db_session, world, tshirt["m"], 2)

    # Voorbereiden shows the stock next to each estimated size.
    prep = as_atelier.get(f"{BASE}/preparation", params={"festival_id": rw.id}).json()
    sizes = {size["size_name"]: (size["quantity"], size["available"], size["owned"]) for size in prep["articles"][0]["sizes"]}
    assert sizes == {"M": (10, 4, 6), "L": (10, 12, 12)}

    # Te bestellen: highest day need (RW) − owned, only what's short.
    needs = as_atelier.get(f"{BASE}/stock/order-needs", params={"season_id": season.id}).json()
    assert [(line["size_name"], line["needed"], line["festival_name"], line["owned"], line["to_order"]) for line in needs] == [
        ("M", 10, "Rock Werchter", 6, 4)
    ]
    pdf = as_atelier.get(f"{BASE}/stock/order-needs/pdf", params={"season_id": season.id})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # Minimum stock: M has 4 available, its minimum is 5.
    alerts = as_atelier.get(f"{BASE}/stock/min-stock").json()
    assert [(line["size_name"], line["min_stock"], line["available"]) for line in alerts] == [("M", 5, 4)]
    totals = as_atelier.get(f"{BASE}/stock/totals").json()
    assert totals == {"available": 16, "to_wash": 2, "handed_out": 0, "below_min_stock": 1}


def test_rights(client: TestClient, db_session: Session, world: dict, tshirt: dict) -> None:
    # Someone who may only view the Stock screen can't book or see the history.
    role = _make_role(db_session, "Kijker", {"atelier.stock": (True, False, False, False)})
    _make_user(db_session, world, "kijker@example.com", role)
    _login(client, "kijker@example.com")
    assert client.get(f"{BASE}/stock").status_code == 200
    assert client.get(f"{BASE}/stock/min-stock").status_code == 200
    line = {"lines": [{"article_size_id": tshirt["m"], "quantity": 1}]}
    assert client.post(f"{BASE}/stock/receipt", json=line).status_code == 403
    assert client.post(f"{BASE}/stock/wash", json=line).status_code == 403
    assert client.get(f"{BASE}/stock/documents").status_code == 403
    assert client.get(f"{BASE}/stock/order-needs", params={"season_id": world["season"].id}).status_code == 403


def test_service_never_commits_and_never_goes_negative(db_session: Session, world: dict, as_atelier: TestClient, tshirt: dict) -> None:
    user = db_session.scalar(select(User))
    receive(db_session, user, [StockLine(tshirt["m"], 2)])
    with pytest.raises(StockError) as error:
        write_off(db_session, user, [StockLine(tshirt["m"], 3, "available")], reason="lost")
    assert error.value.code == "insufficient_stock"
    db_session.rollback()
    # Nothing was committed by the service: the receipt is gone too.
    assert _stock(as_atelier, tshirt["m"]) == (0, 0, 0)
