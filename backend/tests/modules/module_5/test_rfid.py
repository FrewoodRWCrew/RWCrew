# Atelier's RFID pieces (the Raspberry Pi app): Tags koppelen (read tags
# become pieces of an article size), resolving read tags, Ophalen with a tag
# per piece (it must be exactly that size and not out) and Terugbrengen by
# the tags read (the open lines carry the EPC). Also the Pi's own way in:
# the same rights, through a Bearer token.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.db.models.rfid_tag import RfidTag
from tests.modules.module_5.test_desk import DAY, _pick_up, _stock, desk  # noqa: F401  (fixture)
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    _make_role,
    _make_user,
    as_atelier,
    world,
)


def _assign(client: TestClient, epcs: list[str], article_size_id: int, replace: bool = False):
    return client.post(f"{BASE}/rfid/assign", json={"epcs": epcs, "article_size_id": article_size_id, "replace": replace})


def _resolve(client: TestClient, epcs: list[str]) -> dict[str, dict]:
    return {tag["epc"]: tag for tag in client.post(f"{BASE}/rfid/resolve", json={"epcs": epcs}).json()}


def _hand_out_by_tag(client: TestClient, world: dict, desk: dict, tags: list[tuple[str, str, int]], first: str = "Jan"):
    """Ophalen with (article, size, tag id) per piece."""
    return client.post(
        f"{BASE}/desk/handouts",
        json={"first_name": first, "last_name": "Peeters", "festival_id": desk["festival"], "team_id": world["terras"].id,
              "day": DAY, "lines": [{"article_id": desk[article], "article_size_id": desk[size], "rfid_tag_id": tag_id}
                                    for article, size, tag_id in tags]},
    )


def test_assign_and_resolve(as_atelier: TestClient, db_session: Session, world: dict, desk: dict) -> None:
    linked = _assign(as_atelier, [" E200A1 ", "E200A2", "E200A1"], desk["m"])
    assert linked.status_code == 200
    # Trimmed and each EPC once; new tags are registered in TagScan's registry.
    assert [(tag["epc"], tag["state"], tag["size_name"]) for tag in linked.json()] == [
        ("E200A1", "piece", "M"), ("E200A2", "piece", "M")
    ]
    # Tags koppelen's list counts the tagged pieces per size.
    articles = {article["name"]: article for article in as_atelier.get(f"{BASE}/rfid/articles").json()}
    assert [(size["size_name"], size["tagged"]) for size in articles["T-shirt"]["sizes"]] == [("M", 2), ("L", 0)]

    # Another article size only with "replace"; a StockMaster product's tag never.
    assert _assign(as_atelier, ["E200A2"], desk["l"]).json()["detail"] == "tag_other_piece|E200A2|T-shirt M"
    assert _assign(as_atelier, ["E200A2"], desk["l"], replace=True).json()[0]["size_name"] == "L"
    product = Product(name="Bekers")
    db_session.add(product)
    db_session.flush()
    db_session.add(RfidTag(epc_uid="KAR-TAG", status="active", assigned_product_id=product.id))
    db_session.commit()
    assert _assign(as_atelier, ["KAR-TAG"], desk["m"]).json()["detail"] == "tag_not_atelier|KAR-TAG"

    resolved = _resolve(as_atelier, ["E200A1", "KAR-TAG", "NEW-TAG"])
    assert {epc: tag["state"] for epc, tag in resolved.items()} == {
        "E200A1": "piece", "KAR-TAG": "not_atelier", "NEW-TAG": "unknown"
    }
    assert resolved["E200A1"]["open_line_id"] is None


def test_hand_out_and_return_by_tag(as_atelier: TestClient, world: dict, desk: dict) -> None:
    tags = {tag["epc"]: tag["rfid_tag_id"] for tag in _assign(as_atelier, ["TS-1", "TS-2"], desk["m"]).json()}
    apron = _assign(as_atelier, ["SCH-1"], desk["apron_size"]).json()[0]["rfid_tag_id"]

    handout = _hand_out_by_tag(as_atelier, world, desk, [("tshirt", "m", tags["TS-1"]), ("apron", "apron_size", apron)])
    assert handout.status_code == 201
    assert _stock(as_atelier, desk["m"]) == (2, 0, 1)
    # The tag now says who has the piece; the person's open lines carry the EPC.
    out = _resolve(as_atelier, ["TS-1", "TS-2"])
    assert (out["TS-1"]["person_name"], out["TS-2"]["person_name"]) == ("Jan Peeters", None)
    person = as_atelier.get(f"{BASE}/desk/persons", params={"q": "jan peeters"}).json()[0]
    assert sorted(line["epc"] for line in person["open_lines"]) == ["SCH-1", "TS-1"]

    # Terugbrengen by the tags read: the matching open lines come back.
    returned = as_atelier.post(
        f"{BASE}/desk/persons/{person['id']}/return", json={"line_ids": [out["TS-1"]["open_line_id"]]}
    )
    assert returned.status_code == 200
    assert _resolve(as_atelier, ["TS-1"])["TS-1"]["open_line_id"] is None
    assert _stock(as_atelier, desk["m"]) == (2, 1, 0)


def test_hand_out_tag_rules(as_atelier: TestClient, world: dict, desk: dict) -> None:
    tags = {tag["epc"]: tag["rfid_tag_id"] for tag in _assign(as_atelier, ["TS-1", "TS-2"], desk["m"]).json()}
    apron = _assign(as_atelier, ["SCH-1"], desk["apron_size"]).json()[0]["rfid_tag_id"]

    # The tag must be a piece of exactly the line's size.
    wrong = _hand_out_by_tag(as_atelier, world, desk, [("tshirt", "m", apron)])
    assert wrong.json()["detail"] == "tag_size_mismatch|SCH-1|Schort OneSize"
    # One tag can't be two pieces.
    twice = _hand_out_by_tag(as_atelier, world, desk, [("tshirt", "m", tags["TS-1"]), ("apron", "apron_size", tags["TS-1"])])
    assert twice.json()["detail"] == "tag_twice"
    # A piece that is out with someone can't go out again.
    assert _hand_out_by_tag(as_atelier, world, desk, [("tshirt", "m", tags["TS-1"])]).status_code == 201
    taken = _hand_out_by_tag(as_atelier, world, desk, [("tshirt", "m", tags["TS-1"])], first="Piet")
    assert taken.json()["detail"] == "tag_out|TS-1|Jan Peeters"
    # ... nor be linked to another piece while out.
    assert _assign(as_atelier, ["TS-1"], desk["l"], replace=True).json()["detail"] == "tag_out|TS-1|Jan Peeters"
    # Without tags the desk works as before.
    assert _pick_up(as_atelier, world, desk, [("apron", "apron_size")], first="An").status_code == 201


def test_rights_and_bearer_token(client: TestClient, db_session: Session, world: dict, desk: dict) -> None:
    # The fixtures logged in with every right through cookies: drop them, the Pi has none.
    client.cookies.clear()
    # A desk worker (view + create on the desk) may resolve but not link tags.
    role = _make_role(db_session, "Balie", {"atelier.desk": (True, True, False, False)})
    _make_user(db_session, world, "balie@example.com", role)
    tokens = client.post("/api/auth/token", json={"email": "balie@example.com", "password": "password123"}).json()
    # The Pi app sends its token as a Bearer header: same rights as on the website.
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.post(f"{BASE}/rfid/resolve", json={"epcs": ["X"]}, headers=headers).status_code == 200
    assert client.get(f"{BASE}/rfid/articles", headers=headers).status_code == 403
    assert client.post(f"{BASE}/rfid/assign", json={"epcs": ["X"], "article_size_id": desk["m"]}, headers=headers).status_code == 403
    permissions = client.get(f"{BASE}/me/permissions", headers=headers).json()
    assert permissions["creatable_screen_keys"] == ["atelier.desk"]
    # Without a token nothing.
    assert client.post(f"{BASE}/rfid/resolve", json={"epcs": ["X"]}).status_code == 401


def test_tagscan_shows_the_piece_and_keeps_it_apart(client: TestClient, as_atelier: TestClient, db_session: Session,
                                                     world: dict, desk: dict) -> None:
    # A tag linked on the Pi shows its Atelier piece on TagScan's TagManagement.
    from tests.modules.module_1.test_tags import (
        _create_tagscan_module,
        _grant_module_access,
        _grant_tag_management_permission,
    )
    from app.db.models.user import User
    from app.modules.module_1.screens import sync_screens as sync_tagscan_screens

    tag_id = _assign(as_atelier, ["TS-1"], desk["m"]).json()[0]["rfid_tag_id"]
    sync_tagscan_screens(db_session)
    user = db_session.query(User).filter_by(email="atelier@example.com").one()
    _grant_module_access(db_session, user, _create_tagscan_module(db_session))
    _grant_tag_management_permission(db_session, user, can_view=True, can_edit=True)
    tags = {tag["epc_uid"]: tag for tag in client.get("/api/modules/module-1/tags").json()}
    assert tags["TS-1"]["atelier_piece"] == "T-shirt M"

    # ... and can't also get a StockMaster product or kar there.
    product = Product(name="Bekers")
    db_session.add(product)
    db_session.commit()
    refused = client.put(f"/api/modules/module-1/tags/{tag_id}", json={"epc_uid": "TS-1", "assigned_product_id": product.id})
    assert (refused.status_code, refused.json()["detail"]) == (400, "tag_is_atelier_piece")
    kept = client.put(f"/api/modules/module-1/tags/{tag_id}", json={"epc_uid": "TS-1", "notes_1": "zoom"})
    assert (kept.status_code, kept.json()["atelier_piece"]) == (200, "T-shirt M")
