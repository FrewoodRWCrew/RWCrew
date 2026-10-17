# Kar laden's manual requests (app/modules/module_4/manual_request_service.py):
# products added with "Manueel product toevoegen" are stored per season and
# kar, add up, can be removed, follow the Kar laden right and the season lock,
# and stay after the product is loaded.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.modules.module_4.conftest import BASE, StockWorld, book, login, make_role


def _add(client: TestClient, world: StockWorld, kar_id: int, product_id: int, quantity: int, season_id: int | None = None):
    """POST one manual request; returns the response."""
    return client.post(
        f"{BASE}/kars/{kar_id}/manual-requests",
        json={"season_id": season_id or world.season.id, "product_id": product_id, "quantity": quantity},
    )


def _manual(client: TestClient, kar_id: int, season_id: int) -> dict[str, int]:
    """{product name: quantity} of a kar's manual requests on its detail."""
    detail = client.get(f"{BASE}/kars/{kar_id}", params={"season_id": season_id}).json()
    return {request["name"]: request["quantity"] for request in detail["manual_requests"]}


def test_manual_requests_add_up_and_can_be_removed(as_warehouse: TestClient, world: StockWorld) -> None:
    response = _add(as_warehouse, world, world.k101.id, world.tape.id, 2)
    assert response.status_code == 201
    assert [(item["name"], item["quantity"]) for item in response.json()] == [("Tape", 2)]

    # Adding the same product again adds up; it gets no (empty) kar line of its own.
    _add(as_warehouse, world, world.k101.id, world.tape.id, 3)
    assert _manual(as_warehouse, world.k101.id, world.season.id) == {"Tape": 5}
    detail = as_warehouse.get(f"{BASE}/kars/{world.k101.id}", params={"season_id": world.season.id}).json()
    assert "Tape" not in {line["name"] for line in detail["lines"]}

    # Another kar or season doesn't see it.
    assert _manual(as_warehouse, world.k043.id, world.season.id) == {}
    assert _manual(as_warehouse, world.k101.id, world.closed_season.id) == {}

    request_id = response.json()[0]["id"]
    assert as_warehouse.delete(f"{BASE}/kars/{world.k101.id}/manual-requests/{request_id}").status_code == 204
    assert _manual(as_warehouse, world.k101.id, world.season.id) == {}
    # Removing it twice, or through another kar, is refused.
    assert as_warehouse.delete(f"{BASE}/kars/{world.k043.id}/manual-requests/{request_id}").status_code == 404


def test_manual_request_stays_after_loading(as_warehouse: TestClient, world: StockWorld) -> None:
    book(as_warehouse, world, "book_in", [(world.tape.id, 10)])
    _add(as_warehouse, world, world.k101.id, world.tape.id, 2)

    def progress() -> tuple[int, int, int, int]:
        """The kar header's "x/y producten" and "x/y stuks"."""
        kar = as_warehouse.get(f"{BASE}/kars/{world.k101.id}", params={"season_id": world.season.id}).json()["kar"]
        return (kar["loaded_product_count"], kar["required_product_count"], kar["loaded_toward_required"], kar["required_total"])

    # The manual request counts in the kar's loading progress.
    assert progress() == (0, 1, 0, 2)

    assert book(as_warehouse, world, "kar_load", [(world.tape.id, 2)], kar_id=world.k101.id).status_code == 201

    assert _manual(as_warehouse, world.k101.id, world.season.id) == {"Tape": 2}
    assert progress() == (1, 1, 2, 2)
    # The overview's kar cards count it the same way.
    card = next(kar for kar in as_warehouse.get(f"{BASE}/kars", params={"season_id": world.season.id}).json() if kar["kar_id"] == world.k101.id)
    assert (card["loaded_product_count"], card["required_product_count"]) == (1, 1)


def test_manual_request_rules(as_warehouse: TestClient, world: StockWorld) -> None:
    # A blocked product can't be asked for, and the quantity must be at least 1.
    assert _add(as_warehouse, world, world.k101.id, world.blocked.id, 1).json()["detail"] == "product_blocked|Oude kabel"
    assert _add(as_warehouse, world, world.k101.id, world.tape.id, 0).status_code == 422
    # Closed season: locked (the role has no "closedseason" right).
    closed = _add(as_warehouse, world, world.k101.id, world.tape.id, 1, season_id=world.closed_season.id)
    assert closed.status_code == 403
    assert closed.json()["detail"] == "season_closed"


def test_manual_requests_need_the_kar_laden_right(
    client: TestClient, world: StockWorld, make_user, db_session: Session
) -> None:
    viewer = make_role(db_session, "Kijker", {"stockmaster.kars": (True, False, False, False)})
    make_user("kijker@example.com", viewer)
    login(client, "kijker@example.com")

    assert _add(client, world, world.k101.id, world.tape.id, 1).status_code == 403
