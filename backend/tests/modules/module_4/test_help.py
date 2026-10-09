# StockMaster's help manual endpoint (GET /help/pdf): module access is
# needed, and a topic of a screen the user can't view is refused.

from fastapi.testclient import TestClient

from tests.modules.module_4.conftest import BASE, StockWorld, login, make_role


def _assert_pdf(response) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_full_manual_and_one_topic(as_warehouse: TestClient) -> None:
    _assert_pdf(as_warehouse.get(f"{BASE}/help/pdf"))
    _assert_pdf(as_warehouse.get(f"{BASE}/help/pdf", params={"locale": "en", "topic": "kar-load"}))


def test_help_needs_module_access(client: TestClient, world: StockWorld, make_user) -> None:
    make_user("outsider@example.com", world.full_role, access=False)
    login(client, "outsider@example.com")

    assert client.get(f"{BASE}/help/pdf").status_code == 403


def test_topic_of_a_hidden_screen_is_not_found(client: TestClient, world: StockWorld, make_user, db_session) -> None:
    reader = make_role(db_session, "Lezer", {"stockmaster.stock": (True, False, False, False)})
    make_user("reader@example.com", reader)
    login(client, "reader@example.com")

    _assert_pdf(client.get(f"{BASE}/help/pdf"))
    _assert_pdf(client.get(f"{BASE}/help/pdf", params={"topic": "book-in"}))
    assert client.get(f"{BASE}/help/pdf", params={"topic": "kar-load"}).status_code == 404
