# StockMaster's booking rules (app/modules/module_4/stock_service.py): free
# stock and kar stock side by side, never negative, kar departures and
# returns, counts, undo, the season lock — and every booking stored under
# the logged-in user.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.stockmaster_movement import StockMasterMovement
from tests.modules.module_4.conftest import BASE, StockWorld, book, stock_of


def _ten_laders_spread(client: TestClient, world: StockWorld) -> None:
    """The design's example: 10 in stock — 5 free, 2 in K101, 3 in K043."""
    assert book(client, world, "book_in", [(world.lader.id, 10)], reference="LEV-1").status_code == 201
    assert book(client, world, "kar_load", [(world.lader.id, 2)], kar_id=world.k101.id).status_code == 201
    assert book(client, world, "kar_load", [(world.lader.id, 3)], kar_id=world.k043.id).status_code == 201


def test_product_in_free_stock_and_several_kars(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)

    row = stock_of(as_warehouse, world.lader.id)

    assert (row["free"], row["in_kars"], row["total"]) == (5, 5, 10)
    assert {(kar["kar_nummer"], kar["quantity"]) for kar in row["kars"]} == {("K101", 2), ("K043", 3)}
    assert row["bin_label"] == "Hal A · B-12"


def test_stock_can_never_go_negative(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)

    response = book(as_warehouse, world, "kar_unload", [(world.lader.id, 4)], kar_id=world.k043.id)

    assert response.status_code == 400
    assert response.json()["detail"] == "insufficient_stock|Walkie-lader|3|K043"
    # Nothing of the refused booking was kept.
    assert stock_of(as_warehouse, world.lader.id)["free"] == 5


def test_booking_is_stored_under_the_logged_in_user(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    response = book(as_warehouse, world, "book_in", [(world.lader.id, 3)])

    body = response.json()
    assert body["created_by_name"] == "Magazijnier"
    assert body["doc_number"].startswith("SM-") and body["doc_number"].endswith(f"{body['id']:05d}")
    movement = db_session.scalar(select(StockMasterMovement).where(StockMasterMovement.document_id == body["id"]))
    assert movement.created_by_name == "Magazijnier"
    assert movement.bin_snapshot == "Hal A · B-12"


def test_kar_to_kar_move(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)

    response = book(as_warehouse, world, "kar_load", [(world.lader.id, 1)], kar_id=world.k101.id, from_kar_id=world.k043.id)

    assert response.status_code == 201
    kars = {kar["kar_nummer"]: kar["quantity"] for kar in stock_of(as_warehouse, world.lader.id)["kars"]}
    assert kars == {"K101": 3, "K043": 2}


def test_book_out_needs_a_reason_and_works_from_a_kar(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)

    assert book(as_warehouse, world, "book_out", [(world.lader.id, 1)]).json()["detail"] == "reason_required"
    response = book(
        as_warehouse, world, "book_out", [(world.lader.id, 1)], kar_id=world.k043.id, reason_id=world.reason_used.id
    )

    assert response.status_code == 201
    assert response.json()["reason_name"] == "Verbruikt"
    assert stock_of(as_warehouse, world.lader.id)["total"] == 9


def test_blocked_product_cannot_be_booked_in(as_warehouse: TestClient, world: StockWorld) -> None:
    response = book(as_warehouse, world, "book_in", [(world.blocked.id, 1)])

    assert response.json()["detail"] == "product_blocked|Oude kabel"


def test_dispatch_books_the_contents_out_and_return_books_back_in(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)
    book(as_warehouse, world, "book_in", [(world.tape.id, 20)])
    book(as_warehouse, world, "kar_load", [(world.tape.id, 6)], kar_id=world.k043.id)

    dispatch = book(as_warehouse, world, "kar_dispatch", kar_id=world.k043.id, festival_id=world.festival.id)
    assert dispatch.status_code == 201
    assert dispatch.json()["team_name"] == "Chiro Werchter"  # defaulted from KarTracker
    assert stock_of(as_warehouse, world.lader.id)["total"] == 7

    # While out, the kar can't be loaded.
    refused = book(as_warehouse, world, "kar_load", [(world.lader.id, 1)], kar_id=world.k043.id)
    assert refused.json()["detail"] == "kar_out|K043"
    detail = as_warehouse.get(f"{BASE}/kars/{world.k043.id}", params={"season_id": world.season.id}).json()
    assert detail["kar"]["is_out"] is True
    assert {line["name"]: line["quantity"] for line in detail["dispatched"]} == {"Walkie-lader": 3, "Tape": 6}

    # Back: 3 laders into the kar, 2 tape straight to free stock, 4 tape used.
    back = book(
        as_warehouse, world, "kar_return",
        [(world.lader.id, 3, "kar"), (world.tape.id, 2, "free")], kar_id=world.k043.id,
    )
    assert back.status_code == 201
    lader = stock_of(as_warehouse, world.lader.id)
    tape = stock_of(as_warehouse, world.tape.id)
    assert lader["total"] == 10 and {kar["kar_nummer"]: kar["quantity"] for kar in lader["kars"]}["K043"] == 3
    assert (tape["free"], tape["in_kars"]) == (16, 0)

    # The KPI counts the 4 tape that didn't come back as consumed by the team.
    kpi = as_warehouse.get(f"{BASE}/dashboard", params={"season_id": world.season.id}).json()
    assert kpi["consumption_per_team"] == [{"name": "Chiro Werchter", "quantity": 4}]
    assert kpi["kars_out"] == 0


def test_count_books_only_the_differences(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)
    book(as_warehouse, world, "book_in", [(world.tape.id, 20)])

    nothing = book(as_warehouse, world, "count", [(world.lader.id, 5), (world.tape.id, 20)])
    assert nothing.json()["detail"] == "no_differences"

    response = book(
        as_warehouse, world, "count", [(world.lader.id, 4), (world.tape.id, 22)], reason_id=world.reason_count.id
    )
    assert response.status_code == 201
    assert response.json()["line_count"] == 2
    assert stock_of(as_warehouse, world.lader.id)["free"] == 4
    assert stock_of(as_warehouse, world.tape.id)["free"] == 22


def test_undo_books_the_opposite_once(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    _ten_laders_spread(as_warehouse, world)
    load = book(as_warehouse, world, "kar_load", [(world.lader.id, 1)], kar_id=world.k101.id).json()

    undo = as_warehouse.post(f"{BASE}/bookings/{load['id']}/reverse", json={})
    assert undo.status_code == 201
    assert undo.json()["reversal_of_number"] == load["doc_number"]
    assert stock_of(as_warehouse, world.lader.id)["free"] == 5

    original = db_session.get(StockMasterDocument, load["id"])
    db_session.refresh(original)
    assert original.status == "reversed"
    assert as_warehouse.post(f"{BASE}/bookings/{load['id']}/reverse", json={}).json()["detail"] == "already_reversed"


def test_undo_of_a_departure_brings_the_contents_back(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)
    dispatch = book(as_warehouse, world, "kar_dispatch", kar_id=world.k101.id).json()

    assert as_warehouse.post(f"{BASE}/bookings/{dispatch['id']}/reverse", json={}).status_code == 201

    assert stock_of(as_warehouse, world.lader.id)["total"] == 10
    kar = as_warehouse.get(f"{BASE}/kars/{world.k101.id}").json()["kar"]
    assert kar["is_out"] is False


def test_closed_season_is_locked(as_warehouse: TestClient, world: StockWorld) -> None:
    response = book(as_warehouse, world, "book_in", [(world.lader.id, 1)], season_id=world.closed_season.id)

    assert response.status_code == 403
    assert response.json()["detail"] == "season_closed"


def test_minimum_stock_alert_for_consumables(as_warehouse: TestClient, world: StockWorld) -> None:
    assert as_warehouse.get(f"{BASE}/alerts").json() == {"below_minimum_count": 1}

    book(as_warehouse, world, "book_in", [(world.tape.id, 10)])

    assert as_warehouse.get(f"{BASE}/alerts").json() == {"below_minimum_count": 0}


def test_requirements_drive_progress_and_order_needs(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)
    saved = as_warehouse.put(
        f"{BASE}/requirements",
        json={
            "season_id": world.season.id,
            "kar_id": world.k101.id,
            "lines": [{"product_id": world.lader.id, "quantity": 4}, {"product_id": world.tape.id, "quantity": 30}],
        },
    )
    assert saved.status_code == 200
    assert {row["product_name"]: row["in_kar"] for row in saved.json()} == {"Walkie-lader": 2, "Tape": 0}

    kars = as_warehouse.get(f"{BASE}/kars", params={"season_id": world.season.id}).json()
    k101 = next(kar for kar in kars if kar["kar_nummer"] == "K101")
    assert (k101["loaded_toward_required"], k101["required_total"]) == (2, 34)

    needs = {row["name"]: row for row in as_warehouse.get(f"{BASE}/order-needs", params={"season_id": world.season.id}).json()}
    assert needs["Walkie-lader"]["to_order"] == 0  # 4 needed, 10 in stock
    assert needs["Tape"]["to_order"] == 30


def test_requirements_change_needs_the_matching_right(client: TestClient, world: StockWorld, make_user, db_session) -> None:
    from tests.modules.module_4.conftest import login, make_role

    adder = make_role(db_session, "Toevoeger", {"stockmaster.requirements": (True, True, False, False)})
    make_user("adder@example.com", adder)
    login(client, "adder@example.com")
    url = f"{BASE}/requirements"
    base = {"season_id": world.season.id, "kar_id": world.k101.id}

    assert client.put(url, json={**base, "lines": [{"product_id": world.lader.id, "quantity": 2}]}).status_code == 200
    # Changing the quantity needs "edit", removing the line needs "delete".
    assert client.put(url, json={**base, "lines": [{"product_id": world.lader.id, "quantity": 3}]}).status_code == 403
    assert client.put(url, json={**base, "lines": []}).status_code == 403


def test_count_sheet_and_history_filters(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)

    sheet = as_warehouse.get(f"{BASE}/count-sheet", params={"warehouse_id": world.warehouse.id, "bin_from": "B"}).json()
    assert [(line["name"], line["expected"]) for line in sheet] == [("Walkie-lader", 5), ("Oude kabel", 0)]
    kar_sheet = as_warehouse.get(f"{BASE}/count-sheet", params={"kar_id": world.k043.id}).json()
    assert [(line["name"], line["expected"]) for line in kar_sheet] == [("Walkie-lader", 3)]

    history = as_warehouse.get(f"{BASE}/bookings", params={"kar_id": world.k043.id}).json()
    assert history["total"] == 1 and history["items"][0]["doc_type"] == "kar_load"


def test_every_pdf_renders(as_warehouse: TestClient, world: StockWorld) -> None:
    _ten_laders_spread(as_warehouse, world)
    as_warehouse.put(
        f"{BASE}/requirements",
        json={"season_id": world.season.id, "kar_id": world.k101.id, "lines": [{"product_id": world.lader.id, "quantity": 4}]},
    )
    dispatch = book(as_warehouse, world, "kar_dispatch", kar_id=world.k043.id).json()
    booking = as_warehouse.get(f"{BASE}/bookings").json()["items"][-1]

    urls = [
        f"{BASE}/kars/{world.k101.id}/load-list/pdf?season_id={world.season.id}",
        f"{BASE}/bookings/{dispatch['id']}/pdf",
        f"{BASE}/bookings/{booking['id']}/pdf?locale=en",
        f"{BASE}/order-needs/pdf?season_id={world.season.id}",
        f"{BASE}/count-sheet/pdf?warehouse_id={world.warehouse.id}",
        f"{BASE}/count-sheet/pdf?kar_id={world.k101.id}",
    ]
    for url in urls:
        response = as_warehouse.get(url)
        assert response.status_code == 200, url
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")


def test_product_and_kar_with_stock_cannot_be_deleted(
    client: TestClient, world: StockWorld, make_user, db_session: Session
) -> None:
    from app.db.models.module import Module
    from app.db.models.user_module_access import UserModuleAccess
    from tests.modules.module_4.conftest import login

    # A super admin with access to StockMaster, MasterData and KarTracker.
    admin = make_user("admin@example.com", None, super_admin=True)
    for key, name, order in (("module-9", "MasterData", 9), ("module-2", "KarTracker", 2)):
        module = Module(key=key, name=name, sort_order=order)
        db_session.add(module)
        db_session.flush()
        db_session.add(UserModuleAccess(user_id=admin.id, module_id=module.id))
    db_session.commit()
    login(client, "admin@example.com")
    _ten_laders_spread(client, world)

    product_delete = client.delete(f"/api/modules/module-9/products/{world.lader.id}")
    kar_delete = client.delete(f"/api/modules/module-2/karren/{world.k101.id}")

    assert product_delete.status_code == 400
    assert kar_delete.status_code == 400
