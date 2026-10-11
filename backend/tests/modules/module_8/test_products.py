# Tests for the Ploeg Wizard's Products step (step 4): the kar needs of the
# team's kars, stored in StockMaster's StockMaster_kar_requirement through
# module_4/requirement_service.py, but gated by Altsien Select's own rights,
# team scope and season lock.

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.season import Season
from app.db.models.stockmaster_kar_requirement import StockMasterKarRequirement
from tests.modules.module_8.conftest import AltsienWorld, ProductsWorld, login

BASE = "/api/modules/module-8"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _save(client: TestClient, world: AltsienWorld, kar_id: int, lines: list[dict], team_id: int | None = None):
    """PUT a kar's complete list of needs through the wizard."""
    return client.put(
        f"{BASE}/wizard/{team_id or world.own_team.id}/products/requirements",
        json={"season_id": world.season.id, "kar_id": kar_id, "lines": lines},
    )


def _complete(client: TestClient, world: AltsienWorld):
    """Try to mark the Products step as done."""
    return client.post(f"{BASE}/wizard/{world.own_team.id}/steps/products/complete?season_id={world.season.id}")


def test_save_and_read_a_kars_needs(as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld) -> None:
    saved = _save(
        as_kernlid,
        world,
        products_world.own_kar.id,
        [
            {"product_id": products_world.lader.id, "quantity": 2, "comment": "Voor de bar"},
            {"product_id": products_world.tape.id, "quantity": 5},
        ],
    )
    assert saved.status_code == 200
    assert [(row["product_name"], row["quantity"]) for row in saved.json()] == [("Tape", 5), ("Walkie-lader", 2)]

    read = as_kernlid.get(
        f"{BASE}/wizard/{world.own_team.id}/products/requirements"
        f"?season_id={world.season.id}&kar_id={products_world.own_kar.id}"
    )
    assert read.json() == saved.json()
    assert read.json()[1]["comment"] == "Voor de bar"
    assert read.json()[1]["bin_label"] == "Hal A · B-12"


def test_kars_and_catalog_are_limited_to_the_team(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld
) -> None:
    _save(as_kernlid, world, products_world.own_kar.id, [{"product_id": products_world.tape.id, "quantity": 3}])

    kars = as_kernlid.get(f"{BASE}/wizard/{world.own_team.id}/products/kars?season_id={world.season.id}").json()
    assert sorted(kar["kar_nummer"] for kar in kars) == ["K101", "K102"]
    assert next(kar for kar in kars if kar["kar_nummer"] == "K101")["required_total"] == 3

    catalog = as_kernlid.get(f"{BASE}/wizard/{world.own_team.id}/products/catalog")
    assert {product["name"] for product in catalog.json()} == {"Walkie-lader", "Tape"}


def test_a_kar_of_another_team_is_not_found(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld
) -> None:
    response = _save(as_kernlid, world, products_world.other_kar.id, [{"product_id": products_world.tape.id, "quantity": 1}])
    assert response.status_code == 404


def test_a_team_out_of_scope_is_not_found(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld
) -> None:
    response = _save(
        as_kernlid,
        world,
        products_world.other_kar.id,
        [{"product_id": products_world.tape.id, "quantity": 1}],
        team_id=world.other_team.id,
    )
    assert response.status_code == 404
    assert as_kernlid.get(f"{BASE}/wizard/{world.other_team.id}/products/catalog").status_code == 404


def test_a_closed_season_refuses_changes(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld, db_session: Session
) -> None:
    season = db_session.get(Season, world.season.id)
    season.periode_open = False
    db_session.commit()

    response = _save(as_kernlid, world, products_world.own_kar.id, [{"product_id": products_world.tape.id, "quantity": 1}])
    assert response.status_code == 403


def test_view_only_users_cannot_save(
    client: TestClient, world: AltsienWorld, products_world: ProductsWorld, make_user, db_session: Session
) -> None:
    from tests.modules.module_8.conftest import _role

    viewer = _role(db_session, "Kijker", {"altsienselect.wizard": (True, False, False, False)})
    db_session.commit()
    make_user("viewer@example.com", viewer, [world.own_team])
    login(client, "viewer@example.com")

    url = f"{BASE}/wizard/{world.own_team.id}/products/requirements?season_id={world.season.id}&kar_id={products_world.own_kar.id}"
    assert client.get(url).status_code == 200
    response = _save(client, world, products_world.own_kar.id, [{"product_id": products_world.tape.id, "quantity": 1}])
    assert response.status_code == 403


def test_invalid_lines_keep_stockmasters_error_codes(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld
) -> None:
    line = {"product_id": products_world.tape.id, "quantity": 1}
    response = _save(as_kernlid, world, products_world.own_kar.id, [line, line])
    assert response.status_code == 400
    assert response.json()["detail"].startswith("duplicate_product")


def test_step_needs_at_least_one_line_and_reopens_when_emptied(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld
) -> None:
    assert _complete(as_kernlid, world).status_code == 400

    _save(as_kernlid, world, products_world.own_kar.id, [{"product_id": products_world.tape.id, "quantity": 1}])
    done = _complete(as_kernlid, world)
    assert done.status_code == 200
    assert "products" in [item["step_key"] for item in done.json()["progress"]]

    # Emptying the only list un-marks the step.
    _save(as_kernlid, world, products_world.own_kar.id, [])
    state = as_kernlid.get(f"{BASE}/wizard/{world.own_team.id}?season_id={world.season.id}").json()
    assert "products" not in [item["step_key"] for item in state["progress"]]


def test_previous_season_lines(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld, db_session: Session
) -> None:
    previous = Season(name="2025", periode_open=False)
    db_session.add(previous)
    db_session.flush()
    db_session.add(
        StockMasterKarRequirement(
            season_id=previous.id, kar_id=products_world.own_kar.id, product_id=products_world.lader.id, quantity=4
        )
    )
    db_session.commit()

    body = as_kernlid.get(
        f"{BASE}/wizard/{world.own_team.id}/products/requirements/previous"
        f"?season_id={world.season.id}&kar_id={products_world.own_kar.id}"
    ).json()
    assert body["season_name"] == "2025"
    assert [(line["product_name"], line["quantity"], line["current_quantity"]) for line in body["lines"]] == [
        ("Walkie-lader", 4, None)
    ]


def test_excel_template_and_import(as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld) -> None:
    assert as_kernlid.get(f"{BASE}/products-import/template").status_code == 200

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["product_id", "product_name", "bin", "quantity"])
    sheet.append([products_world.lader.id, "Walkie-lader", None, 3])
    buffer = io.BytesIO()
    workbook.save(buffer)
    response = as_kernlid.post(f"{BASE}/products-import", files={"file": ("p.xlsx", buffer.getvalue(), XLSX)})

    assert response.status_code == 200
    assert [(line["product_id"], line["quantity"]) for line in response.json()["lines"]] == [(products_world.lader.id, 3)]
    # Nothing is stored by the import itself.
    assert as_kernlid.get(
        f"{BASE}/wizard/{world.own_team.id}/products/requirements"
        f"?season_id={world.season.id}&kar_id={products_world.own_kar.id}"
    ).json() == []


def test_ploegfiche_and_pdf_show_the_needs_per_kar(
    as_kernlid: TestClient, world: AltsienWorld, products_world: ProductsWorld, db_session: Session
) -> None:
    _save(as_kernlid, world, products_world.own_kar.id, [{"product_id": products_world.tape.id, "quantity": 7}])

    state = as_kernlid.get(f"{BASE}/ploegfiche/{world.own_team.id}?season_id={world.season.id}").json()
    by_kar = {kar["kar_nummer"]: kar["lines"] for kar in state["kar_requirements"]}
    assert by_kar["K101"] == [{"product_id": products_world.tape.id, "product_name": "Tape", "quantity": 7, "comment": None}]
    assert by_kar["K102"] == []

    pdf = as_kernlid.get(f"{BASE}/ploegfiche/{world.own_team.id}/pdf?season_id={world.season.id}")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")

    load_list = as_kernlid.get(
        f"{BASE}/wizard/{world.own_team.id}/products/kars/{products_world.own_kar.id}/load-list/pdf?season_id={world.season.id}"
    )
    assert load_list.status_code == 200
    assert load_list.content.startswith(b"%PDF")

    # Written into StockMaster's own table, not a module-8 copy.
    assert db_session.scalars(select(StockMasterKarRequirement.quantity)).all() == [7]
