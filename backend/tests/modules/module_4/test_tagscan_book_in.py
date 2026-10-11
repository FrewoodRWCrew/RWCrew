# Inboeken from a TagScan scan (app/modules/module_4/tagscan_book_in.py):
# waiting "Book In" lines become basket lines per scanned file (one piece
# per distinct tag, of the tag's product), lines with an unknown tag or a
# tag without product are problems, and the booking marks the lines it
# came from "loaded" in the same transaction — never twice.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.rfid_tag import RfidTag
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from tests.modules.module_4.conftest import BASE, StockWorld, book, login, make_role, stock_of


def _scan(db: Session, filename: str, rows: list[tuple[str, str]]) -> TagHeaderData:
    """A scanned file with (epc, action) lines, all still waiting."""
    header = TagHeaderData(filename=filename, line_count=len(rows))
    db.add(header)
    db.flush()
    for number, (epc, action) in enumerate(rows, start=2):
        db.add(TagLineData(header_data_id=header.id, line_number=number, epc=epc, action=action, status="no_match"))
    db.commit()
    return header


def _tag(db: Session, epc: str, product_id: int | None) -> None:
    """A registered tag, with or without a product."""
    db.add(RfidTag(epc_uid=epc, status="active", assigned_product_id=product_id))
    db.commit()


def _line_ids(db: Session, header: TagHeaderData) -> dict[str, int]:
    """The file's line ids by EPC."""
    return {line.epc: line.id for line in db.scalars(select(TagLineData).where(TagLineData.header_data_id == header.id))}


def test_waiting_lines_become_basket_lines_per_file(as_warehouse: TestClient, db_session: Session, world: StockWorld) -> None:
    _tag(db_session, "E1", world.lader.id)
    _tag(db_session, "E2", world.lader.id)
    _tag(db_session, "E3", world.tape.id)
    _tag(db_session, "E4", None)
    header = _scan(
        db_session,
        "levering.csv",
        [
            ("E1", "Book In"),
            ("E2", " book in "),   # any case / spaces
            ("E1", "Book In"),     # same tag read twice → one piece
            ("E3", "book_in"),
            ("E4", "Book In"),     # tag without product
            ("E9", "Book In"),     # unknown tag
            ("E3", "Assignment"),  # another action: not offered here
        ],
    )

    assert as_warehouse.get(f"{BASE}/tagscan-book-in/count").json() == {"count": 6}
    files = as_warehouse.get(f"{BASE}/tagscan-book-in").json()

    assert len(files) == 1
    file = files[0]
    assert file["header_data_id"] == header.id
    assert file["filename"] == "levering.csv"
    assert file["lines"] == [
        {"product_id": world.lader.id, "quantity": 2},
        {"product_id": world.tape.id, "quantity": 1},
    ]
    assert [problem["detail"] for problem in file["problems"]] == ["no_product|E4", "unknown_tag|E9"]
    assert len(file["line_ids"]) == 4


def test_booking_marks_the_scan_lines_loaded(as_warehouse: TestClient, db_session: Session, world: StockWorld) -> None:
    _tag(db_session, "E1", world.lader.id)
    header = _scan(db_session, "levering.csv", [("E1", "Book In"), ("E9", "Book In")])
    file = as_warehouse.get(f"{BASE}/tagscan-book-in").json()[0]

    response = book(as_warehouse, world, "book_in", [(world.lader.id, 1)], tagscan_line_ids=file["line_ids"])

    assert response.status_code == 201
    assert stock_of(as_warehouse, world.lader.id)["free"] == 1
    db_session.expire_all()
    ids = _line_ids(db_session, header)
    booked = db_session.get(TagLineData, ids["E1"])
    assert booked.process_status == "loaded"
    assert booked.process_comment == f"Booked in: {response.json()['doc_number']}"
    # The problem line keeps waiting, so the file does too.
    assert db_session.get(TagLineData, ids["E9"]).process_status == "new"
    assert db_session.get(TagHeaderData, header.id).process_status == "new"
    document = db_session.scalar(select(StockMasterDocument))
    assert (document.source, document.tagscan_header_id) == ("tagscan", header.id)
    assert as_warehouse.get(f"{BASE}/tagscan-book-in/count").json() == {"count": 1}


def test_the_same_scan_lines_cant_be_booked_twice(as_warehouse: TestClient, db_session: Session, world: StockWorld) -> None:
    _tag(db_session, "E1", world.lader.id)
    _scan(db_session, "levering.csv", [("E1", "Book In")])
    line_ids = as_warehouse.get(f"{BASE}/tagscan-book-in").json()[0]["line_ids"]
    assert book(as_warehouse, world, "book_in", [(world.lader.id, 1)], tagscan_line_ids=line_ids).status_code == 201

    second = book(as_warehouse, world, "book_in", [(world.lader.id, 1)], tagscan_line_ids=line_ids)

    assert second.status_code == 400
    assert second.json()["detail"] == "tagscan_already_booked"
    # The refused booking wrote nothing.
    assert stock_of(as_warehouse, world.lader.id)["free"] == 1


def test_cancel_a_problem_line_with_a_reason(as_warehouse: TestClient, db_session: Session, world: StockWorld) -> None:
    header = _scan(db_session, "levering.csv", [("E9", "Book In"), ("E8", "Assignment")])
    ids = _line_ids(db_session, header)

    assert as_warehouse.post(f"{BASE}/tagscan-book-in/lines/{ids['E9']}/cancel", json={"comment": ""}).status_code == 422
    # Only waiting "Book In" lines can be cancelled here.
    assert as_warehouse.post(f"{BASE}/tagscan-book-in/lines/{ids['E8']}/cancel", json={"comment": "x"}).status_code == 404
    response = as_warehouse.post(f"{BASE}/tagscan-book-in/lines/{ids['E9']}/cancel", json={"comment": "Vreemde tag"})

    assert response.status_code == 204
    db_session.expire_all()
    line = db_session.get(TagLineData, ids["E9"])
    assert (line.process_status, line.process_comment) == ("cancelled", "Vreemde tag")
    assert as_warehouse.get(f"{BASE}/tagscan-book-in").json() == []


def test_count_needs_module_access_but_list_needs_book_in(
    client: TestClient, db_session: Session, world: StockWorld, make_user
) -> None:
    _scan(db_session, "levering.csv", [("E9", "Book In")])
    viewer = make_role(db_session, "Kijker", {"stockmaster.stock": (True, False, False, False)})
    make_user("kijker@example.com", viewer)
    login(client, "kijker@example.com")

    assert client.get(f"{BASE}/tagscan-book-in/count").json() == {"count": 1}
    assert client.get(f"{BASE}/tagscan-book-in").status_code == 403
