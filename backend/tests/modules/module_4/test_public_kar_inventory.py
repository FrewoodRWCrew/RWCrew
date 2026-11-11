# Tests for StockMaster's public "Kar inventaris" (no login: the kar's lock code
# opens it) and the staff screen "Kar inventarissen".

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.stockmaster_balance import StockMasterBalance
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.stockmaster_movement import StockMasterMovement
from app.modules.module_4.public_kar_inventory_router import reset_limiters
from app.core.security import create_access_token
from tests.modules.module_4.conftest import BASE, StockWorld, book, login, make_role

PUBLIC = "/api/public/stockmaster/kar-inventory"


@pytest.fixture(autouse=True)
def _fresh_limiters():
    """Every test starts without counted tries (the limiters live in memory)."""
    reset_limiters()
    yield
    reset_limiters()


@pytest.fixture()
def coded(db_session: Session, world: StockWorld) -> StockWorld:
    """K043 gets lock code 3618, K101 none."""
    world.k043.kar_code = "3618"
    db_session.commit()
    return world


def unlock(client: TestClient, kar: str = "K043", code: str = "3618"):
    """POST the lock code."""
    return client.post(f"{PUBLIC}/unlock", json={"kar_nummer": kar, "code": code})


def opened(client: TestClient, kar: str = "K043", code: str = "3618") -> dict:
    """Headers with the token of an unlocked kar."""
    response = unlock(client, kar, code)
    assert response.status_code == 200, response.text
    return {"X-Kar-Inventory-Token": response.json()["token"]}


def _stock_rows(db: Session) -> tuple[int, int, int]:
    """How many documents, movements and balance rows exist."""
    return (
        db.scalar(select(func.count()).select_from(StockMasterDocument)),
        db.scalar(select(func.count()).select_from(StockMasterMovement)),
        db.scalar(select(func.count()).select_from(StockMasterBalance)),
    )


def _send_out_k043(client: TestClient, world: StockWorld) -> None:
    """K043 leaves with 6 tape and 2 laders, then gets 2 tape delivered at the festival."""
    assert book(client, world, "book_in", [(world.tape.id, 20), (world.lader.id, 5)]).status_code == 201
    assert book(client, world, "kar_load", [(world.tape.id, 6), (world.lader.id, 2)], kar_id=world.k043.id).status_code == 201
    assert book(client, world, "kar_dispatch", kar_id=world.k043.id).status_code == 201
    assert book(client, world, "kar_load", [(world.tape.id, 2)], kar_id=world.k043.id).status_code == 201


def test_unlock_needs_the_right_code(client: TestClient, coded: StockWorld) -> None:
    # Right code, kar number in any case and with spaces.
    response = unlock(client, " k043 ", " 3618 ")
    assert response.status_code == 200
    assert response.json()["kar_nummer"] == "K043"

    # Wrong code and unknown kar give the same answer.
    assert unlock(client, code="1234").json()["detail"] == "wrong_code"
    assert unlock(client, kar="K999").json()["detail"] == "wrong_code"

    # A kar without a lock code can't be opened.
    assert unlock(client, kar="K101").json()["detail"] == "no_code"


def test_kar_is_locked_after_five_wrong_codes(client: TestClient, coded: StockWorld) -> None:
    for _ in range(4):
        assert unlock(client, code="0000").json()["detail"] == "wrong_code"
    fifth = unlock(client, code="0000")
    assert fifth.status_code == 429
    assert fifth.json()["detail"].startswith("too_many_tries|")
    # Even the right code waits now.
    assert unlock(client).status_code == 429


def test_token_is_required_and_only_this_kind(client: TestClient, db_session: Session, coded: StockWorld) -> None:
    assert client.get(PUBLIC).status_code == 401
    assert client.get(PUBLIC, headers={"X-Kar-Inventory-Token": "nonsense"}).json()["detail"] == "token_invalid"
    # A normal login token doesn't open a kar.
    login_token = create_access_token(1)
    assert client.get(PUBLIC, headers={"X-Kar-Inventory-Token": login_token}).status_code == 401

    # Changing the lock code ends open sessions.
    headers = opened(client)
    assert client.get(PUBLIC, headers=headers).status_code == 200
    coded.k043.kar_code = "9999"
    db_session.commit()
    assert client.get(PUBLIC, headers=headers).status_code == 401


def test_list_is_what_left_with_the_kar(as_warehouse: TestClient, coded: StockWorld) -> None:
    _send_out_k043(as_warehouse, coded)
    context = as_warehouse.get(PUBLIC, headers=opened(as_warehouse)).json()
    assert context["kar_is_out"] is True
    assert context["team_name"] == "Chiro Werchter"
    assert context["season_name"] == "2026"
    # Kar vertrekt plus the follow-up delivery.
    assert {line["name"]: line["expected"] for line in context["lines"]} == {"Tape": 8, "Walkie-lader": 2}
    assert context["history"] == []


def test_list_is_the_kar_contents_in_the_warehouse(as_warehouse: TestClient, coded: StockWorld) -> None:
    book(as_warehouse, coded, "book_in", [(coded.tape.id, 10)])
    book(as_warehouse, coded, "kar_load", [(coded.tape.id, 3)], kar_id=coded.k043.id)
    context = as_warehouse.get(PUBLIC, headers=opened(as_warehouse)).json()
    assert context["kar_is_out"] is False
    assert {line["name"]: line["expected"] for line in context["lines"]} == {"Tape": 3}


def test_save_logs_the_count_and_never_touches_stock(
    as_warehouse: TestClient, db_session: Session, coded: StockWorld
) -> None:
    _send_out_k043(as_warehouse, coded)
    headers = opened(as_warehouse)
    before = _stock_rows(db_session)
    response = as_warehouse.post(
        PUBLIC,
        headers=headers,
        json={
            "counted_by_name": "  Jan Peeters ",
            "remark": "emmer kapot",
            "lines": [{"product_id": coded.tape.id, "counted": 5}, {"product_id": coded.lader.id, "counted": 2}],
        },
    )
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved["counted_by_name"] == "Jan Peeters"
    assert (saved["total_expected"], saved["total_counted"]) == (10, 7)
    assert {line["product_name"]: (line["expected"], line["counted"]) for line in saved["lines"]} == {
        "Tape": (8, 5),
        "Walkie-lader": (2, 2),
    }
    assert _stock_rows(db_session) == before

    # The history shows it, newest first.
    second = as_warehouse.post(
        PUBLIC,
        headers=headers,
        json={"counted_by_name": "Els", "lines": [{"product_id": coded.tape.id, "counted": 8},
                                                   {"product_id": coded.lader.id, "counted": 2}]},
    )
    assert second.status_code == 201
    history = as_warehouse.get(PUBLIC, headers=headers).json()["history"]
    assert [item["counted_by_name"] for item in history] == ["Els", "Jan Peeters"]


def test_save_checks_its_lines(as_warehouse: TestClient, coded: StockWorld) -> None:
    _send_out_k043(as_warehouse, coded)
    headers = opened(as_warehouse)
    tape = {"product_id": coded.tape.id, "counted": 8}
    lader = {"product_id": coded.lader.id, "counted": 2}

    def save(**body):
        return as_warehouse.post(PUBLIC, headers=headers, json={"counted_by_name": "Jan", **body})

    # Every product on the list needs a count.
    assert save(lines=[tape]).json()["detail"] == "line_missing|Walkie-lader"
    # A product that isn't on the list as a list line: the list changed.
    assert save(lines=[tape, lader, {"product_id": coded.blocked.id, "counted": 1}]).json()["detail"] == "list_changed"
    # The same product twice.
    assert save(lines=[tape, lader], extra=[tape]).json()["detail"].startswith("duplicate_product|")
    # A blocked product can't be added as an extra.
    assert save(lines=[tape, lader], extra=[{"product_id": coded.blocked.id, "counted": 1}]).json()["detail"].startswith(
        "unknown_product|"
    )
    # A name of only spaces.
    assert as_warehouse.post(
        PUBLIC, headers=headers, json={"counted_by_name": "   ", "lines": [tape, lader]}
    ).json()["detail"] == "name_required"
    # Negative counts are refused by the schema.
    assert save(lines=[{"product_id": coded.tape.id, "counted": -1}, lader]).status_code == 422


def test_extra_product_search_and_save(as_warehouse: TestClient, db_session: Session, coded: StockWorld) -> None:
    book(as_warehouse, coded, "book_in", [(coded.tape.id, 10)])
    book(as_warehouse, coded, "kar_load", [(coded.tape.id, 3)], kar_id=coded.k043.id)
    headers = opened(as_warehouse)
    # The whole list (for the screen's own filter) and a search; blocked products never.
    everything = [item["name"] for item in as_warehouse.get(f"{PUBLIC}/products", headers=headers).json()]
    assert everything == ["Tape", "Walkie-lader"]
    names = [item["name"] for item in as_warehouse.get(f"{PUBLIC}/products", headers=headers, params={"q": "la"}).json()]
    assert names == ["Walkie-lader"]
    assert as_warehouse.get(f"{PUBLIC}/products", params={"q": "la"}).status_code == 401

    saved = as_warehouse.post(
        PUBLIC,
        headers=headers,
        json={
            "counted_by_name": "Jan",
            "lines": [{"product_id": coded.tape.id, "counted": 3}],
            "extra": [{"product_id": coded.lader.id, "counted": 1}],
        },
    ).json()
    extra = next(line for line in saved["lines"] if line["is_extra"])
    assert (extra["product_name"], extra["expected"], extra["counted"]) == ("Walkie-lader", 0, 1)


def test_staff_list_detail_export_and_rights(
    client: TestClient, db_session: Session, coded: StockWorld, make_user
) -> None:
    make_user("magazijnier@example.com", coded.full_role)
    login(client, "magazijnier@example.com")
    book(client, coded, "book_in", [(coded.tape.id, 10)])
    book(client, coded, "kar_load", [(coded.tape.id, 3)], kar_id=coded.k043.id)
    headers = opened(client)
    saved = client.post(
        PUBLIC, headers=headers,
        json={"counted_by_name": "=Jan", "lines": [{"product_id": coded.tape.id, "counted": 2}]},
    ).json()

    listed = client.get(f"{BASE}/kar-inventories", params={"season_id": coded.season.id})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [saved["id"]]
    assert client.get(f"{BASE}/kar-inventories/{saved['id']}").json()["kar_nummer"] == "K043"
    assert client.get(f"{BASE}/kar-inventories/999999").status_code == 404
    export = client.post(f"{BASE}/kar-inventories/export", json={"ids": [saved["id"]], "locale": "nl"})
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("application/vnd.openxmlformats")

    # Without "view" on the screen: nothing.
    other = make_role(db_session, "Kijker", {"stockmaster.stock": (True, False, False, False)})
    make_user("kijker@example.com", other)
    login(client, "kijker@example.com")
    assert client.get(f"{BASE}/kar-inventories", params={"season_id": coded.season.id}).status_code == 403
    assert client.post(f"{BASE}/kar-inventories/export", json={"ids": [saved["id"]]}).status_code == 403
