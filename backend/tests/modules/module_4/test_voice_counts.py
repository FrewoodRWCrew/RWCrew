# Tests for StockMaster's voice counts (the phone's "Spraaktelling"): saving a
# kar's count, merging a product said twice, the checks on kar/product/
# quantity/season, the screen rights, cancelling and the CSV download.

from fastapi.testclient import TestClient

from tests.modules.module_4.conftest import BASE, StockWorld, login, make_role


def save(client: TestClient, world: StockWorld, lines: list[tuple[int, int, str | None]], **fields):
    """POST one voice count of kar K101 (Ophalen) in the open season."""
    payload = {
        "season_id": fields.pop("season_id", world.season.id),
        "kar_id": fields.pop("kar_id", world.k101.id),
        "direction": fields.pop("direction", "pickup"),
        "lines": [{"product_id": line[0], "quantity": line[1], "spoken_text": line[2]} for line in lines],
    }
    return client.post(f"{BASE}/voice-counts", json=payload)


def test_lookups_list_kars_and_unblocked_products(as_warehouse: TestClient, world: StockWorld) -> None:
    body = as_warehouse.get(f"{BASE}/voice-count/lookups").json()
    assert [kar["kar_nummer"] for kar in body["kars"]] == ["K043", "K101"]
    names = [product["name"] for product in body["products"]]
    assert "Tape" in names and "Walkie-lader" in names
    assert "Oude kabel" not in names  # blocked


def test_save_merges_a_product_said_twice(as_warehouse: TestClient, world: StockWorld) -> None:
    response = save(
        as_warehouse,
        world,
        [(world.tape.id, 20, "twintig rollen tape"), (world.lader.id, 2, None), (world.tape.id, 3, "plus drie tape")],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["kar_nummer"] == "K101"
    assert body["direction"] == "pickup"
    assert body["status"] == "new"
    assert body["created_by_name"] == "Magazijnier"
    assert body["total_quantity"] == 25
    tape = next(line for line in body["lines"] if line["product_id"] == world.tape.id)
    assert tape["quantity"] == 23
    assert tape["spoken_text"] == "twintig rollen tape · plus drie tape"


def test_save_does_not_change_stock(as_warehouse: TestClient, world: StockWorld) -> None:
    save(as_warehouse, world, [(world.tape.id, 5, None)], direction="return")
    rows = as_warehouse.get(f"{BASE}/stock").json()
    assert all(row["product_id"] != world.tape.id or row["total"] == 0 for row in rows)


def test_save_refuses_bad_input(as_warehouse: TestClient, world: StockWorld) -> None:
    assert save(as_warehouse, world, []).status_code == 422
    assert save(as_warehouse, world, [(world.tape.id, 0, None)]).status_code == 422
    assert save(as_warehouse, world, [(world.tape.id, 1, None)], direction="other").status_code == 422
    unknown_kar = save(as_warehouse, world, [(world.tape.id, 1, None)], kar_id=99999)
    assert unknown_kar.status_code == 404 and unknown_kar.json()["detail"] == "kar_not_found|99999"
    unknown_product = save(as_warehouse, world, [(99999, 1, None)])
    assert unknown_product.status_code == 404 and unknown_product.json()["detail"] == "product_not_found|99999"
    # Nothing half-saved after a refusal.
    assert as_warehouse.get(f"{BASE}/voice-counts", params={"season_id": world.season.id}).json() == []


def test_closed_season_is_refused(as_warehouse: TestClient, world: StockWorld) -> None:
    response = save(as_warehouse, world, [(world.tape.id, 1, None)], season_id=world.closed_season.id)
    assert response.status_code == 403 and response.json()["detail"] == "season_closed"


def test_list_detail_cancel_and_csv(as_warehouse: TestClient, world: StockWorld) -> None:
    first = save(as_warehouse, world, [(world.tape.id, 4, "vier tape")]).json()
    second = save(as_warehouse, world, [(world.lader.id, 1, None)], kar_id=world.k043.id, direction="return").json()

    listed = as_warehouse.get(f"{BASE}/voice-counts", params={"season_id": world.season.id}).json()
    assert [item["id"] for item in listed] == [second["id"], first["id"]]
    assert as_warehouse.get(f"{BASE}/voice-counts/{first['id']}").json()["lines"][0]["quantity"] == 4

    csv_response = as_warehouse.get(f"{BASE}/voice-counts/{first['id']}/csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    rows = csv_response.text.lstrip("﻿").strip().splitlines()
    assert rows[0].startswith("kar;direction;")
    assert rows[1].startswith("K101;pickup;") and ";Tape;4;vier tape" in rows[1]

    cancelled = as_warehouse.post(f"{BASE}/voice-counts/{first['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_by_name"] == "Magazijnier"
    again = as_warehouse.post(f"{BASE}/voice-counts/{first['id']}/cancel")
    assert again.status_code == 400 and again.json()["detail"] == f"voice_count_not_new|{first['id']}"

    assert as_warehouse.get(f"{BASE}/voice-counts/99999").status_code == 404


def test_rights_follow_the_voice_count_screen(
    client: TestClient, db_session, world: StockWorld, make_user
) -> None:
    # Only "create" on the voice count screen: may count on the phone, not see the list.
    counter_role = make_role(db_session, "Teller", {"stockmaster.voicecount": (False, True, False, False)})
    make_user("teller@example.com", counter_role)
    login(client, "teller@example.com")
    assert client.get(f"{BASE}/voice-count/lookups").status_code == 200
    created = save(client, world, [(world.tape.id, 1, None)])
    assert created.status_code == 201
    assert client.get(f"{BASE}/voice-counts", params={"season_id": world.season.id}).status_code == 403
    assert client.post(f"{BASE}/voice-counts/{created.json()['id']}/cancel").status_code == 403

    # No right on the screen at all: nothing.
    other_role = make_role(db_session, "Kijker", {"stockmaster.stock": (True, False, False, False)})
    make_user("kijker@example.com", other_role)
    login(client, "kijker@example.com")
    assert client.get(f"{BASE}/voice-count/lookups").status_code == 403
    assert save(client, world, [(world.tape.id, 1, None)]).status_code == 403
