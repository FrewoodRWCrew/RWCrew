# StockMaster's access rights: the same custom-roles-with-per-screen-
# permissions system as the other modules (see tests/modules/module_8/
# test_roles.py) — module access first, then view/create/edit/delete per
# screen.

from fastapi.testclient import TestClient

from tests.modules.module_4.conftest import BASE, StockWorld, book, login, make_role


def test_user_without_module_access_is_refused(client: TestClient, world: StockWorld, make_user) -> None:
    make_user("outsider@example.com", world.full_role, access=False)
    login(client, "outsider@example.com")

    assert client.get(f"{BASE}/me/permissions").status_code == 403
    assert client.get(f"{BASE}/stock").status_code == 403


def test_super_admin_without_module_access_is_refused(client: TestClient, world: StockWorld, make_user) -> None:
    # Being super admin doesn't open a module by itself (same rule as every module).
    make_user("admin@example.com", None, access=False, super_admin=True)
    login(client, "admin@example.com")

    assert client.get(f"{BASE}/me/permissions").status_code == 403


def test_my_permissions_follow_the_role(client: TestClient, world: StockWorld, make_user, db_session) -> None:
    reader = make_role(db_session, "Lezer", {"stockmaster.stock": (True, False, False, False)})
    make_user("reader@example.com", reader)
    login(client, "reader@example.com")

    permissions = client.get(f"{BASE}/me/permissions").json()

    assert permissions["viewable_screen_keys"] == ["stockmaster.stock"]
    assert permissions["creatable_screen_keys"] == []


def test_booking_needs_the_matching_create_right(client: TestClient, world: StockWorld, make_user, db_session) -> None:
    # Viewing the stock isn't enough to book in.
    reader = make_role(db_session, "Lezer", {"stockmaster.stock": (True, False, False, False)})
    make_user("reader@example.com", reader)
    login(client, "reader@example.com")

    response = book(client, world, "book_in", [(world.lader.id, 5)])

    assert response.status_code == 403


def test_order_needs_create_right_may_book_in(client: TestClient, world: StockWorld, make_user, db_session) -> None:
    buyer = make_role(db_session, "Aankoop", {"stockmaster.orderneeds": (True, True, False, False)})
    make_user("buyer@example.com", buyer)
    login(client, "buyer@example.com")

    assert book(client, world, "book_in", [(world.lader.id, 5)]).status_code == 201
    # ...but not load a kar.
    assert book(client, world, "kar_load", [(world.lader.id, 1)], kar_id=world.k101.id).status_code == 403


def test_roles_and_users_screens(as_warehouse: TestClient, world: StockWorld) -> None:
    screens = as_warehouse.get(f"{BASE}/screens").json()
    assert [screen["key"] for screen in screens][:3] == ["stockmaster.kpi", "stockmaster.stock", "stockmaster.kars"]

    created = as_warehouse.post(f"{BASE}/roles", json={"name": "Planner"})
    assert created.status_code == 201

    users = as_warehouse.get(f"{BASE}/users").json()
    assert [user["email"] for user in users] == ["magazijnier@example.com"]
