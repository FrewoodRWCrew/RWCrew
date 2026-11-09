# StockMaster on the RWCrew Pi: linking tags to products, resolving read
# EPCs, bookings with tags (quantities = tags + untagged pieces), the last
# known place of every tag, the contradiction rules, Kar vertrekt with
# corrections, Kar terug, Telling, reversals and the Tag-historiek.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_size import AtelierSize
from app.db.models.module import Module
from app.db.models.rfid_tag import RfidTag
from app.db.models.stockmaster_movement_tag import StockMasterMovementTag
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from tests.modules.module_4.conftest import BASE, StockWorld, book, login, make_role, stock_of

READER = {"name": "Pi Magazijn", "location": "Hal A"}


def link(client: TestClient, product_id: int, epcs: list[str], **extra) -> object:
    """Tags koppelen."""
    return client.post(f"{BASE}/rfid/assign", json={"epcs": epcs, "product_id": product_id, "reader": READER, **extra})


def pi_book(client: TestClient, world: StockWorld, action: str, epcs: list[str] = (), **fields) -> object:
    """One booking with tags, as the Pi sends it."""
    payload = {"action": action, "season_id": world.season.id, "epcs": list(epcs), "reader": READER, **fields}
    return client.post(f"{BASE}/rfid/bookings", json=payload)


def tag(db: Session, epc: str) -> RfidTag:
    """The tag row of an EPC, fresh from the database."""
    db.expire_all()
    return db.scalar(select(RfidTag).where(RfidTag.epc_uid == epc))


def lader_tags(n: int) -> list[str]:
    """n made-up EPCs for walkie-laders."""
    return [f"E2L{index:03d}" for index in range(n)]


# --- Linking and resolving -------------------------------------------------


def test_link_registers_new_tags_with_the_product(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    response = link(as_warehouse, world.lader.id, ["E2A", " E2B ", "E2A"])

    assert response.status_code == 200
    assert [row["epc"] for row in response.json()] == ["E2A", "E2B"]
    assert all(row["state"] == "product" and row["product_name"] == "Walkie-lader" for row in response.json())
    row = tag(db_session, "E2A")
    assert row.assigned_product_id == world.lader.id
    assert row.stock_place is None
    assert row.last_reader_id == "Pi Magazijn" and row.last_location == "Hal A"
    db_session.refresh(world.lader)
    assert world.lader.is_tag_managed is True


def test_link_refuses_other_product_unless_replace_and_forgets_the_place(
    as_warehouse: TestClient, world: StockWorld, db_session: Session
) -> None:
    link(as_warehouse, world.lader.id, ["E2A"])
    pi_book(as_warehouse, world, "book_in", ["E2A"])
    assert tag(db_session, "E2A").stock_place == "free"

    refused = link(as_warehouse, world.tape.id, ["E2A"])
    assert refused.status_code == 400
    assert refused.json()["detail"] == "tag_other_product|E2A|Walkie-lader"

    replaced = link(as_warehouse, world.tape.id, ["E2A"], replace=True)
    assert replaced.status_code == 200
    row = tag(db_session, "E2A")
    assert row.assigned_product_id == world.tape.id
    assert row.stock_place is None


def test_link_refuses_atelier_pieces_kar_tags_and_blocked_products(
    as_warehouse: TestClient, world: StockWorld, db_session: Session
) -> None:
    article = AtelierArticle(code="TS", name="T-shirt")
    size = AtelierSize(name="M", fit="unisex")
    db_session.add_all([article, size])
    db_session.flush()
    article_size = AtelierArticleSize(article_id=article.id, size_id=size.id)
    db_session.add(article_size)
    db_session.flush()
    db_session.add_all(
        [
            RfidTag(epc_uid="E2SHIRT", status="active", atelier_article_size_id=article_size.id),
            RfidTag(epc_uid="E2KAR", status="active", kar_id=world.k101.id),
        ]
    )
    db_session.commit()

    assert link(as_warehouse, world.lader.id, ["E2SHIRT"]).json()["detail"] == "tag_is_atelier_piece|E2SHIRT"
    assert link(as_warehouse, world.lader.id, ["E2KAR"]).json()["detail"] == "tag_is_kar|E2KAR|K101"
    assert link(as_warehouse, world.blocked.id, ["E2NEW"]).json()["detail"] == "product_blocked|Oude kabel"


def test_resolve_tells_what_each_epc_is(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    link(as_warehouse, world.lader.id, ["E2A"])
    db_session.add_all(
        [
            RfidTag(epc_uid="E2KAR", status="active", kar_id=world.k101.id),
            RfidTag(epc_uid="E2FREE", status="active"),
            RfidTag(epc_uid="E2LOST", status="lost", assigned_product_id=world.lader.id),
        ]
    )
    db_session.commit()

    rows = as_warehouse.post(f"{BASE}/rfid/resolve", json={"epcs": ["E2A", "E2KAR", "E2FREE", "E2LOST", "E2NONE"]}).json()

    assert [row["state"] for row in rows] == ["product", "kar_tag", "unassigned", "inactive", "unknown"]
    assert rows[1]["kar_nummer"] == "K101" and rows[1]["kar_is_out"] is False


def test_products_list_has_tagged_counts(as_warehouse: TestClient, world: StockWorld) -> None:
    link(as_warehouse, world.lader.id, lader_tags(3))

    rows = as_warehouse.get(f"{BASE}/rfid/products").json()

    assert rows[0]["name"] == "Walkie-lader"
    assert rows[0]["tagged"] == 3 and rows[0]["is_tag_managed"] is True


# --- Simple bookings -------------------------------------------------------


def test_book_in_counts_tags_plus_untagged_pieces(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    link(as_warehouse, world.lader.id, lader_tags(3))

    response = pi_book(
        as_warehouse, world, "book_in", lader_tags(3), lines=[{"product_id": world.tape.id, "quantity": 20}]
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["pieces"] == 23 and body["tags"] == 3
    assert body["document"]["source"] == "pi"
    assert stock_of(as_warehouse, world.lader.id)["free"] == 3
    assert stock_of(as_warehouse, world.tape.id)["free"] == 20
    assert {tag(db_session, epc).stock_place for epc in lader_tags(3)} == {"free"}
    links = db_session.scalars(select(StockMasterMovementTag)).all()
    assert len(links) == 3 and all(link_row.movement_id is not None for link_row in links)


def test_book_in_refuses_a_tag_already_in_stock(as_warehouse: TestClient, world: StockWorld) -> None:
    link(as_warehouse, world.lader.id, ["E2A"])
    pi_book(as_warehouse, world, "book_in", ["E2A"])

    response = pi_book(as_warehouse, world, "book_in", ["E2A"])

    assert response.status_code == 400
    assert response.json()["detail"] == "tag_already_in_stock|E2A"
    assert stock_of(as_warehouse, world.lader.id)["free"] == 1


def test_unknown_and_unlinked_tags_refuse_the_booking(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    db_session.add(RfidTag(epc_uid="E2FREE", status="active"))
    db_session.commit()

    assert pi_book(as_warehouse, world, "book_in", ["E2NONE"]).json()["detail"] == "tag_unknown|E2NONE"
    assert pi_book(as_warehouse, world, "book_in", ["E2FREE"]).json()["detail"] == "tag_no_product|E2FREE"


def test_load_and_unload_move_tags(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    link(as_warehouse, world.lader.id, lader_tags(4))
    pi_book(as_warehouse, world, "book_in", lader_tags(4))

    # The kar's own tag may be read along: it is skipped.
    db_session.add(RfidTag(epc_uid="E2KAR", status="active", kar_id=world.k101.id))
    db_session.commit()
    loaded = pi_book(as_warehouse, world, "kar_load", [*lader_tags(3), "E2KAR"], kar_id=world.k101.id)
    assert loaded.status_code == 201, loaded.text
    row = tag(db_session, lader_tags(1)[0])
    assert row.stock_place == "kar" and row.stock_kar_id == world.k101.id

    # Loading it again, or into another kar, is a clear contradiction.
    again = pi_book(as_warehouse, world, "kar_load", lader_tags(1), kar_id=world.k101.id)
    assert again.json()["detail"] == "tag_already_in_kar|E2L000|K101"
    other = pi_book(as_warehouse, world, "kar_load", lader_tags(1), kar_id=world.k043.id)
    assert other.json()["detail"] == "tag_in_other_kar|E2L000|K101"
    # Unloading from the other kar too.
    wrong = pi_book(as_warehouse, world, "kar_unload", lader_tags(1), kar_id=world.k043.id)
    assert wrong.json()["detail"] == "tag_in_other_kar|E2L000|K101"

    unloaded = pi_book(as_warehouse, world, "kar_unload", lader_tags(2), kar_id=world.k101.id)
    assert unloaded.status_code == 201, unloaded.text
    assert stock_of(as_warehouse, world.lader.id)["free"] == 3
    assert tag(db_session, "E2L000").stock_place == "free"
    assert tag(db_session, "E2L002").stock_place == "kar"


def test_scrap_needs_a_reason_and_writes_tags_off(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    link(as_warehouse, world.lader.id, ["E2A", "E2B"])
    pi_book(as_warehouse, world, "book_in", ["E2A", "E2B"])

    assert pi_book(as_warehouse, world, "book_out", ["E2A"]).json()["detail"] == "reason_required"
    response = pi_book(as_warehouse, world, "book_out", ["E2A"], reason_id=world.reason_used.id)

    assert response.status_code == 201, response.text
    assert tag(db_session, "E2A").stock_place == "written_off"
    assert pi_book(as_warehouse, world, "kar_load", ["E2A"], kar_id=world.k101.id).json()["detail"] == "tag_written_off|E2A"
    # A written-off piece that turns up again can be booked in.
    assert pi_book(as_warehouse, world, "book_in", ["E2A"]).status_code == 201


def test_web_bookings_do_not_move_tags(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    link(as_warehouse, world.lader.id, ["E2A"])
    pi_book(as_warehouse, world, "book_in", ["E2A"])

    assert book(as_warehouse, world, "kar_load", [(world.lader.id, 1)], kar_id=world.k101.id).status_code == 201

    row = tag(db_session, "E2A")
    assert row.stock_place == "free"
    # The place may be out of date: unloading it from the kar on the Pi is fine.
    assert pi_book(as_warehouse, world, "kar_unload", ["E2A"], kar_id=world.k101.id).status_code == 201


# --- Kar vertrekt, Kar terug ------------------------------------------------


def _fill_kar(client: TestClient, world: StockWorld, epcs: list[str], tape: int = 0) -> None:
    """Link + book in + load into K101 (with untagged tape)."""
    link(client, world.lader.id, epcs)
    pi_book(client, world, "book_in", epcs, lines=[{"product_id": world.tape.id, "quantity": 50}])
    lines = [{"product_id": world.tape.id, "quantity": tape}] if tape else []
    assert pi_book(client, world, "kar_load", epcs, kar_id=world.k101.id, lines=lines).status_code == 201


def test_dispatch_corrects_the_kar_then_books_it_out(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    _fill_kar(as_warehouse, world, lader_tags(4), tape=10)
    # One more lader that lies in free stock gets read along (an extra piece).
    link(as_warehouse, world.lader.id, ["E2EXTRA"])
    pi_book(as_warehouse, world, "book_in", ["E2EXTRA"])

    # Read: 2 of the 4 laders + the extra one; 10 tape counted by hand.
    read = [*lader_tags(2), "E2EXTRA"]
    unresolved = pi_book(
        as_warehouse, world, "kar_dispatch", read, kar_id=world.k101.id,
        lines=[{"product_id": world.tape.id, "quantity": 10}],
    )
    assert unresolved.json()["detail"] == "missing_unresolved|Walkie-lader|1"

    response = pi_book(
        as_warehouse, world, "kar_dispatch", read, kar_id=world.k101.id,
        lines=[{"product_id": world.tape.id, "quantity": 10}],
        missing=[
            {"product_id": world.lader.id, "quantity": 1, "destination": "free"},
        ],
    )
    # 4 expected, 3 present → 1 missing: decided "free". The extra one is
    # already counted in present (no extra load needed).
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document"]["doc_type"] == "kar_dispatch"
    assert [doc["doc_type"] for doc in body["corrections"]] == ["kar_unload"]
    assert body["corrections"][0]["comment"] == "Kar vertrekt K101"

    # Kar 4 → 3 (the extra piece counts as present, one went back to free).
    assert stock_of(as_warehouse, world.lader.id)["in_kars"] == 0
    assert stock_of(as_warehouse, world.lader.id)["free"] == 2
    for epc in read:
        row = tag(db_session, epc)
        assert row.stock_place == "out" and row.stock_kar_id == world.k101.id and row.stock_trip_id is not None
    unread = [tag(db_session, epc) for epc in lader_tags(4)[2:]]
    # One unread tag follows the missing piece back to free stock, the other is unknown.
    assert sorted(str(row.stock_place) for row in unread) == ["None", "free"]


def test_dispatch_writes_missing_off_and_loads_extras(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    _fill_kar(as_warehouse, world, lader_tags(2), tape=10)

    no_reason = pi_book(
        as_warehouse, world, "kar_dispatch", lader_tags(2), kar_id=world.k101.id,
        lines=[{"product_id": world.tape.id, "quantity": 14}],
    )
    # 14 tape present, 10 expected: 4 extra loaded from free stock; nothing missing.
    assert no_reason.status_code == 201, no_reason.text
    assert [doc["doc_type"] for doc in no_reason.json()["corrections"]] == ["kar_load"]
    assert stock_of(as_warehouse, world.tape.id)["free"] == 36

    # Next kar: one lader missing and written off — needs a reason.
    assert pi_book(as_warehouse, world, "kar_return", [], kar_id=world.k101.id).status_code == 201
    # Nothing came back; the two laders turn up later and are booked in again.
    assert pi_book(as_warehouse, world, "book_in", ["E2L000", "E2L001"]).status_code == 201
    assert pi_book(as_warehouse, world, "kar_load", ["E2L000", "E2L001"], kar_id=world.k043.id).status_code == 201
    missing = [{"product_id": world.lader.id, "quantity": 1, "destination": "written_off"}]
    refused = pi_book(as_warehouse, world, "kar_dispatch", ["E2L000"], kar_id=world.k043.id, missing=missing)
    assert refused.json()["detail"] == "reason_required"
    done = pi_book(
        as_warehouse, world, "kar_dispatch", ["E2L000"], kar_id=world.k043.id,
        missing=missing, reason_id=world.reason_used.id,
    )
    assert done.status_code == 201, done.text
    assert [doc["doc_type"] for doc in done.json()["corrections"]] == ["book_out"]
    assert tag(db_session, "E2L001").stock_place == "written_off"


def test_dispatch_is_one_transaction(as_warehouse: TestClient, world: StockWorld) -> None:
    _fill_kar(as_warehouse, world, lader_tags(2))
    # An extra piece that isn't in free stock: the load fails, nothing is booked.
    link(as_warehouse, world.lader.id, ["E2GHOST"])
    response = pi_book(
        as_warehouse, world, "kar_dispatch", [*lader_tags(2), "E2GHOST"], kar_id=world.k101.id,
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("insufficient_stock|")
    assert stock_of(as_warehouse, world.lader.id)["in_kars"] == 2


def test_return_puts_tags_back_per_destination(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    _fill_kar(as_warehouse, world, lader_tags(3), tape=10)
    pi_book(
        as_warehouse, world, "kar_dispatch", lader_tags(3), kar_id=world.k101.id,
        lines=[{"product_id": world.tape.id, "quantity": 10}],
    )

    # 2 laders back to free stock, 4 tape back into the kar; one lader stays out.
    response = pi_book(
        as_warehouse, world, "kar_return", lader_tags(2), kar_id=world.k101.id,
        lines=[
            {"product_id": world.lader.id, "quantity": 0, "destination": "free"},
            {"product_id": world.tape.id, "quantity": 4, "destination": "kar"},
        ],
    )

    assert response.status_code == 201, response.text
    assert stock_of(as_warehouse, world.lader.id)["free"] == 2
    assert stock_of(as_warehouse, world.tape.id)["in_kars"] == 4
    assert tag(db_session, "E2L000").stock_place == "free"
    assert tag(db_session, "E2L002").stock_place == "out"


def test_load_into_an_out_kar_is_a_follow_up_delivery(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    _fill_kar(as_warehouse, world, lader_tags(1))
    pi_book(as_warehouse, world, "kar_dispatch", lader_tags(1), kar_id=world.k101.id)
    link(as_warehouse, world.lader.id, ["E2LATE"])
    pi_book(as_warehouse, world, "book_in", ["E2LATE"])

    response = pi_book(as_warehouse, world, "kar_load", ["E2LATE"], kar_id=world.k101.id)

    assert response.status_code == 201, response.text
    row = tag(db_session, "E2LATE")
    assert row.stock_place == "out" and row.stock_trip_id is not None
    # Read again on its way back: a kar return accepts it.
    assert pi_book(as_warehouse, world, "kar_return", ["E2LATE"], kar_id=world.k101.id).status_code == 201


# --- Telling ---------------------------------------------------------------


def test_count_records_places_even_without_differences(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    link(as_warehouse, world.lader.id, lader_tags(3))
    pi_book(as_warehouse, world, "book_in", lader_tags(3))

    same = pi_book(as_warehouse, world, "count", lader_tags(3))
    assert same.status_code == 201, same.text
    assert same.json()["document"]["line_count"] == 0

    # Only 2 read: one piece less; the unread tag's place becomes unknown.
    fewer = pi_book(as_warehouse, world, "count", lader_tags(2), reason_id=world.reason_count.id)
    assert fewer.status_code == 201, fewer.text
    assert stock_of(as_warehouse, world.lader.id)["free"] == 2
    assert tag(db_session, "E2L002").stock_place is None


def test_count_of_a_kar_takes_tags_from_anywhere_and_zero_lines(
    as_warehouse: TestClient, world: StockWorld, db_session: Session
) -> None:
    _fill_kar(as_warehouse, world, lader_tags(2), tape=5)

    response = pi_book(
        as_warehouse, world, "count", lader_tags(2), kar_id=world.k043.id,
        lines=[{"product_id": world.tape.id, "quantity": 0}],
    )

    # K043 held nothing: 2 laders found there (the count is the authority).
    assert response.status_code == 201, response.text
    assert tag(db_session, "E2L000").stock_kar_id == world.k043.id
    assert stock_of(as_warehouse, world.lader.id)["in_kars"] == 4


# --- Reversal, history, rights ---------------------------------------------


def test_reversal_puts_tags_back_unless_they_moved_since(
    as_warehouse: TestClient, world: StockWorld, db_session: Session
) -> None:
    link(as_warehouse, world.lader.id, ["E2A", "E2B"])
    pi_book(as_warehouse, world, "book_in", ["E2A", "E2B"])
    loaded = pi_book(as_warehouse, world, "kar_load", ["E2A", "E2B"], kar_id=world.k101.id).json()["document"]
    pi_book(as_warehouse, world, "kar_unload", ["E2B"], kar_id=world.k101.id)

    # Undoing the load can't take E2B out of the kar any more (it's free now)…
    refused = as_warehouse.post(f"{BASE}/bookings/{loaded['id']}/reverse")
    assert refused.status_code == 400  # insufficient stock in the kar
    # …so undo the unload first, then the load.
    unload_doc = db_session.scalars(select(StockMasterMovementTag).order_by(StockMasterMovementTag.id.desc())).first()
    assert as_warehouse.post(f"{BASE}/bookings/{unload_doc.document_id}/reverse").status_code == 201
    assert tag(db_session, "E2B").stock_place == "kar"
    assert as_warehouse.post(f"{BASE}/bookings/{loaded['id']}/reverse").status_code == 201
    assert {tag(db_session, epc).stock_place for epc in ("E2A", "E2B")} == {"free"}


def test_reversal_of_a_dispatch_brings_tags_back_into_the_kar(
    as_warehouse: TestClient, world: StockWorld, db_session: Session
) -> None:
    _fill_kar(as_warehouse, world, lader_tags(2))
    dispatched = pi_book(as_warehouse, world, "kar_dispatch", lader_tags(2), kar_id=world.k101.id).json()["document"]

    assert as_warehouse.post(f"{BASE}/bookings/{dispatched['id']}/reverse").status_code == 201

    row = tag(db_session, "E2L000")
    assert row.stock_place == "kar" and row.stock_kar_id == world.k101.id and row.stock_trip_id is None


def test_history_lists_every_pi_booking(as_warehouse: TestClient, world: StockWorld) -> None:
    link(as_warehouse, world.lader.id, ["E2A"])
    pi_book(as_warehouse, world, "book_in", ["E2A"])
    pi_book(as_warehouse, world, "kar_load", ["E2A"], kar_id=world.k101.id)

    body = as_warehouse.get(f"{BASE}/rfid/history", params={"epc": "E2A"}).json()

    assert body["product_name"] == "Walkie-lader"
    assert body["place"] == "kar" and body["place_kar_nummer"] == "K101"
    assert [event["doc_type"] for event in body["events"]] == ["kar_load", "book_in"]
    assert body["events"][0]["to_kar_nummer"] == "K101"


def test_tag_management_shows_the_place(as_warehouse: TestClient, world: StockWorld, db_session: Session) -> None:
    link(as_warehouse, world.lader.id, ["E2A"])
    pi_book(as_warehouse, world, "book_in", ["E2A"])
    pi_book(as_warehouse, world, "kar_load", ["E2A"], kar_id=world.k101.id)
    # Tagbeheer (Scans, module-1) for the same user.
    tagscan = Module(key="module-1", name="Scans", sort_order=1)
    db_session.add(tagscan)
    db_session.flush()
    user = db_session.scalar(select(User).where(User.email == "magazijnier@example.com"))
    user.is_super_admin = True
    db_session.add(UserModuleAccess(user_id=user.id, module_id=tagscan.id))
    db_session.commit()

    rows = as_warehouse.get("/api/modules/module-1/tags").json()

    assert rows[0]["epc_uid"] == "E2A"
    assert rows[0]["stock_place"] == "kar" and rows[0]["stock_place_kar"] == "K101"


def test_bookings_need_the_actions_right(client: TestClient, world: StockWorld, make_user, db_session: Session) -> None:
    viewer = make_role(db_session, "Kijker", {"stockmaster.stock": (True, False, False, False), "stockmaster.tags": (True, False, False, False)})
    make_user("kijker@example.com", viewer)
    login(client, "kijker@example.com")

    assert pi_book(client, world, "book_in", ["E2A"]).status_code == 403
    assert link(client, world.lader.id, ["E2A"]).status_code == 403
    assert client.post(f"{BASE}/rfid/resolve", json={"epcs": ["E2A"]}).status_code == 200


def test_pi_bearer_login_can_book(client: TestClient, world: StockWorld, make_user) -> None:
    make_user("pi@example.com", world.full_role)
    token = client.post(
        "/api/auth/token", json={"email": "pi@example.com", "password": "password123", "client": "pi"}
    ).json()["access_token"]
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"{BASE}/rfid/assign", json={"epcs": ["E2A"], "product_id": world.lader.id}, headers=headers
    )

    assert response.status_code == 200
    booked = client.post(
        f"{BASE}/rfid/bookings", json={"action": "book_in", "season_id": world.season.id, "epcs": ["E2A"]}, headers=headers
    )
    assert booked.status_code == 201
    assert booked.json()["document"]["created_by_name"] == "Pi"
