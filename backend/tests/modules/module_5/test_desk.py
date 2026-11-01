# Atelier's counter desk (block 4): Ophalen (one piece per package article,
# size picked at the desk, available → handed out) and Terugbrengen (handed
# out → to wash, partial allowed), the rules (package only, first + family
# name = the person, email required but not unique, unique bracelet number,
# no second piece of an article while one is out), "Uitgifte annuleren", the
# open list, the persons-vs-reservation count, the KPI tiles and the rights.

from datetime import date
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.db.models.festival import Festival
from app.db.models.team_responsible import TeamResponsible

# The block-1 fixtures and helpers (module, seasons, teams, sizes, a user with every right).
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    _create_article,
    _login,
    _make_role,
    _make_user,
    _size_id,
    as_atelier,
    world,
)

DAY = "2026-07-03"


@pytest.fixture()
def desk(as_atelier: TestClient, db_session: Session, world: dict) -> dict:
    """Rock Werchter (2–5 July); terras (2 persons) gets a T-shirt (M/L men) and
    an apron (OneSize); a cap is not in the package; stock received."""
    rw = Festival(name="Rock Werchter", start_date=date(2026, 7, 2), end_date=date(2026, 7, 5), season_id=world["season"].id)
    db_session.add(rw)
    db_session.commit()
    tshirt = _create_article(as_atelier, "TS", name="T-shirt", size_ids=[_size_id(world, "M", "men"), _size_id(world, "L", "men")])
    apron = _create_article(as_atelier, "SCH", name="Schort", size_ids=[_size_id(world, "OneSize", "unisex")])
    cap = _create_article(as_atelier, "CAP", name="Pet", size_ids=[_size_id(world, "OneSize", "unisex")])
    as_atelier.put(
        f"{BASE}/reservations/{rw.id}",
        json={"reservations": [{"team_id": world["terras"].id, "persons": 2,
                                "lines": [{"article_id": tshirt["id"], "quantity_per_person": 1},
                                          {"article_id": apron["id"], "quantity_per_person": 1}]}]},
    )
    sizes = {"m": tshirt["sizes"][0]["id"], "l": tshirt["sizes"][1]["id"], "apron_size": apron["sizes"][0]["id"], "cap_size": cap["sizes"][0]["id"]}
    as_atelier.post(
        f"{BASE}/stock/receipt",
        json={"lines": [{"article_size_id": sizes["m"], "quantity": 3}, {"article_size_id": sizes["apron_size"], "quantity": 5},
                        {"article_size_id": sizes["cap_size"], "quantity": 5}]},
    )
    return {"festival": rw.id, "tshirt": tshirt["id"], "apron": apron["id"], "cap": cap["id"], **sizes}


def _pick_up(
    client: TestClient,
    world: dict,
    desk: dict,
    lines: list[tuple[str, str]],
    first: str = "Jan",
    last: str = "Peeters",
    email: str = "Jan@Example.com",
    bracelet: str | None = None,
):
    return client.post(
        f"{BASE}/desk/handouts",
        json={"first_name": first, "last_name": last, "email": email, "bracelet_number": bracelet,
              "festival_id": desk["festival"], "team_id": world["terras"].id, "day": DAY,
              "lines": [{"article_id": desk[article], "article_size_id": desk[size]} for article, size in lines]},
    )


def _stock(client: TestClient, article_size_id: int) -> tuple[int, int, int]:
    for article in client.get(f"{BASE}/stock").json():
        for size in article["sizes"]:
            if size["article_size_id"] == article_size_id:
                return size["available"], size["to_wash"], size["handed_out"]
    raise AssertionError("article size not on the stock overview")


def test_context_teams_and_pick_up(as_atelier: TestClient, world: dict, desk: dict) -> None:
    teams = as_atelier.get(f"{BASE}/desk/teams", params={"festival_id": desk["festival"]}).json()
    assert teams == [{"team_id": world["terras"].id, "team_name": "RW terras", "persons": 2}]
    context = as_atelier.get(
        f"{BASE}/desk/context", params={"festival_id": desk["festival"], "team_id": world["terras"].id, "day": DAY}
    ).json()
    assert [article["name"] for article in context["articles"]] == ["Schort", "T-shirt"]
    assert [(size["size_name"], size["available"]) for size in context["articles"][1]["sizes"]] == [("M", 3), ("L", 0)]
    assert (context["persons_reserved"], context["served_today"]) == (2, 0)
    assert context["team_responsibles"] == []

    response = _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")])
    assert response.status_code == 201
    handout = response.json()
    # The email is stored lowercase; the hand-out has one line per article.
    assert (handout["person_name"], handout["email"], handout["status"], len(handout["lines"])) == (
        "Jan Peeters", "jan@example.com", "open", 2
    )
    assert _stock(as_atelier, desk["m"]) == (2, 0, 1)
    assert as_atelier.get(
        f"{BASE}/desk/context", params={"festival_id": desk["festival"], "team_id": world["terras"].id, "day": DAY}
    ).json()["served_today"] == 1


def test_pick_up_rules(as_atelier: TestClient, world: dict, desk: dict) -> None:
    def detail(response) -> str:
        return response.json()["detail"]

    assert detail(_pick_up(as_atelier, world, desk, [("tshirt", "m")], email="geen-email")) == "email_invalid"
    assert detail(_pick_up(as_atelier, world, desk, [("cap", "cap_size")])).startswith("not_in_package|")
    assert detail(_pick_up(as_atelier, world, desk, [("tshirt", "apron_size")])).startswith("size_required|")
    assert detail(_pick_up(as_atelier, world, desk, [("tshirt", "m"), ("tshirt", "l")])) == "article_twice"
    # No L in stock.
    assert detail(_pick_up(as_atelier, world, desk, [("tshirt", "l")])).startswith("insufficient_stock|")

    # Jan has his T-shirt: he can't get another one before returning it (same
    # person = same first + family name, whatever the case or spaces).
    assert _pick_up(as_atelier, world, desk, [("tshirt", "m")]).status_code == 201
    again = _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")], first="JAN", last=" peeters ")
    assert detail(again) == "article_still_out|T-shirt"
    # ... but he can pick up the apron he doesn't have yet (with a new email: the latest one is kept).
    assert _pick_up(as_atelier, world, desk, [("apron", "apron_size")], email="jan.p@example.com").status_code == 201
    persons = as_atelier.get(f"{BASE}/desk/persons", params={"q": "jan pee"}).json()
    assert len(persons) == 1 and {line["article_name"] for line in persons[0]["open_lines"]} == {"T-shirt", "Schort"}
    assert persons[0]["email"] == "jan.p@example.com"
    lookup = as_atelier.get(f"{BASE}/desk/persons/lookup", params={"first_name": "jan", "last_name": "PEETERS"}).json()
    assert lookup["id"] == persons[0]["id"]
    assert as_atelier.get(f"{BASE}/desk/persons/lookup", params={"first_name": "Jan", "last_name": "Janssens"}).json() is None

    # A day outside the festival is refused.
    outside = as_atelier.post(
        f"{BASE}/desk/handouts",
        json={"first_name": "An", "last_name": "Claes", "email": "an@example.com", "festival_id": desk["festival"],
              "team_id": world["terras"].id,
              "day": "2026-07-09", "lines": [{"article_id": desk["apron"], "article_size_id": desk["apron_size"]}]},
    )
    assert detail(outside) == "day_not_in_festival"


def test_partial_and_full_return(as_atelier: TestClient, world: dict, desk: dict) -> None:
    handout = _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")]).json()
    tshirt_line = next(line["id"] for line in handout["lines"] if line["article_name"] == "T-shirt")
    apron_line = next(line["id"] for line in handout["lines"] if line["article_name"] == "Schort")

    # The T-shirt comes back: to wash; the pick-up stays open with the apron out.
    partial = as_atelier.post(f"{BASE}/desk/handouts/{handout['id']}/return", json={"line_ids": [tshirt_line]}).json()
    assert partial["status"] == "open"
    assert _stock(as_atelier, desk["m"]) == (2, 1, 0)
    open_list = as_atelier.get(f"{BASE}/desk/open", params={"festival_id": desk["festival"]}).json()
    assert [[line["article_name"] for line in row["lines"]] for row in open_list] == [["Schort"]]
    # Returning the same piece twice is refused.
    again = as_atelier.post(f"{BASE}/desk/handouts/{handout['id']}/return", json={"line_ids": [tshirt_line]})
    assert again.json()["detail"] == "already_returned"

    # The apron comes back too: the pick-up is closed and no longer open.
    done = as_atelier.post(f"{BASE}/desk/handouts/{handout['id']}/return", json={"line_ids": [apron_line]}).json()
    assert done["status"] == "returned"
    assert as_atelier.get(f"{BASE}/desk/open").json() == []
    # Now Jan can pick up a T-shirt again.
    assert _pick_up(as_atelier, world, desk, [("tshirt", "m")]).status_code == 201

    # The desk's stock bookings can't be undone on Boekingen.
    hand_out_doc = next(doc for doc in as_atelier.get(f"{BASE}/stock/documents").json() if doc["doc_type"] == "hand_out")
    assert as_atelier.post(f"{BASE}/stock/documents/{hand_out_doc['id']}/reverse", json={}).json()["detail"] == "use_desk"


def test_cancel_only_while_nothing_returned(as_atelier: TestClient, world: dict, desk: dict) -> None:
    first = _pick_up(as_atelier, world, desk, [("tshirt", "m")]).json()
    cancelled = as_atelier.post(f"{BASE}/desk/handouts/{first['id']}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert _stock(as_atelier, desk["m"]) == (3, 0, 0)
    # A cancelled pick-up doesn't count as served.
    context = as_atelier.get(
        f"{BASE}/desk/context", params={"festival_id": desk["festival"], "team_id": world["terras"].id, "day": DAY}
    ).json()
    assert context["served_today"] == 0

    second = _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")]).json()
    as_atelier.post(f"{BASE}/desk/handouts/{second['id']}/return", json={"line_ids": [second["lines"][0]["id"]]})
    assert as_atelier.post(f"{BASE}/desk/handouts/{second['id']}/cancel").json()["detail"] == "cannot_cancel"


def test_kpi_and_rights(client: TestClient, as_atelier: TestClient, db_session: Session, world: dict, desk: dict) -> None:
    _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")])
    stats = as_atelier.get(f"{BASE}/desk/stats").json()
    assert (stats["still_out"], stats["persons_with_open"]) == (2, 1)

    # Someone who may only view Openstaand can't hand out or search persons.
    as_atelier.post("/api/auth/logout")
    role = _make_role(db_session, "Kijker", {"atelier.open": (True, False, False, False)})
    _make_user(db_session, world, "kijker@example.com", role)
    _login(client, "kijker@example.com")
    assert client.get(f"{BASE}/desk/open").status_code == 200
    assert client.get(f"{BASE}/desk/persons", params={"q": "jan"}).status_code == 403
    assert _pick_up(client, world, desk, [("apron", "apron_size")], first="An").status_code == 403


def test_email_not_unique_and_bracelet_number_unique(as_atelier: TestClient, world: dict, desk: dict) -> None:
    # Two different people may share an email address.
    first = _pick_up(as_atelier, world, desk, [("apron", "apron_size")], first="Jan", email="ploeg@example.com", bracelet="RW-0001")
    second = _pick_up(as_atelier, world, desk, [("apron", "apron_size")], first="Piet", email="ploeg@example.com")
    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["person_id"] != second.json()["person_id"]
    assert first.json()["bracelet_number"] == "RW-0001"

    # The bracelet number belongs to one person only.
    taken = _pick_up(as_atelier, world, desk, [("tshirt", "m")], first="Piet", bracelet="RW-0001")
    assert taken.json()["detail"] == "bracelet_in_use|RW-0001|Jan Peeters"
    # Searching by bracelet number finds its owner; an empty field keeps the number.
    found = as_atelier.get(f"{BASE}/desk/persons", params={"q": "rw-0001"}).json()
    assert [person["name"] for person in found] == ["Jan Peeters"]
    _pick_up(as_atelier, world, desk, [("tshirt", "m")], first="Jan", email="ploeg@example.com")
    found = as_atelier.get(f"{BASE}/desk/persons", params={"q": "rw-0001"}).json()
    assert found[0]["bracelet_number"] == "RW-0001"


def test_pick_up_twice_a_day_and_only_some_articles(as_atelier: TestClient, world: dict, desk: dict) -> None:
    # Only the apron (one package article of two) is fine.
    first = _pick_up(as_atelier, world, desk, [("apron", "apron_size")]).json()
    assert [line["article_name"] for line in first["lines"]] == ["Schort"]
    # The T-shirt can still be picked up the same day: only the apron is out.
    second = _pick_up(as_atelier, world, desk, [("tshirt", "m")])
    assert second.status_code == 201
    # Everything back → the same person picks up the whole package again that day.
    for handout in (first, second.json()):
        as_atelier.post(f"{BASE}/desk/handouts/{handout['id']}/return", json={"line_ids": [line["id"] for line in handout["lines"]]})
    again = _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")])
    assert again.status_code == 201
    persons = as_atelier.get(f"{BASE}/desk/persons", params={"q": "jan peeters"}).json()
    assert len(persons) == 1 and len(persons[0]["open_lines"]) == 2


def test_context_shows_team_responsibles(as_atelier: TestClient, db_session: Session, world: dict, desk: dict) -> None:
    # The team's leads of the festival's season are on the desk context; other seasons' and teams' are not.
    db_session.add_all([
        TeamResponsible(season_id=world["season"].id, team_id=world["terras"].id, name="Piet", email="piet@example.com",
                        phone="0470 11 22 33", comments="Ploegbaas"),
        TeamResponsible(season_id=world["previous"].id, team_id=world["terras"].id, name="Oud", email="oud@example.com",
                        phone="1"),
        TeamResponsible(season_id=world["season"].id, team_id=world["vip"].id, name="Vip", email="vip@example.com",
                        phone="2"),
    ])
    db_session.commit()
    context = as_atelier.get(
        f"{BASE}/desk/context", params={"festival_id": desk["festival"], "team_id": world["terras"].id, "day": DAY}
    ).json()
    assert context["team_responsibles"] == [
        {"name": "Piet", "email": "piet@example.com", "phone": "0470 11 22 33", "comments": "Ploegbaas"}
    ]


def test_return_status_masterdata_and_issues(as_atelier: TestClient, world: dict, desk: dict) -> None:
    # The list: a name exists once (ignoring case).
    created = as_atelier.post(f"{BASE}/return-statuses", json={"name": " Beschadigd "})
    assert created.status_code == 201 and created.json()["name"] == "Beschadigd"
    status_id = created.json()["id"]
    assert as_atelier.post(f"{BASE}/return-statuses", json={"name": "beschadigd"}).status_code == 409
    other_id = as_atelier.post(f"{BASE}/return-statuses", json={"name": "Zeer vuil"}).json()["id"]

    handout = _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")]).json()
    tshirt_line = next(line["id"] for line in handout["lines"] if line["article_name"] == "T-shirt")
    apron_line = next(line["id"] for line in handout["lines"] if line["article_name"] == "Schort")
    return_url = f"{BASE}/desk/persons/{handout['person_id']}/return"
    before = _stock(as_atelier, desk["m"])

    # An inactive status isn't offered and is refused, without booking anything.
    assert as_atelier.put(f"{BASE}/return-statuses/{other_id}", json={"name": "Zeer vuil", "active": False}).status_code == 200
    assert [row["name"] for row in as_atelier.get(f"{BASE}/desk/return-statuses").json()] == ["Beschadigd"]
    refused = as_atelier.post(return_url, json={"line_ids": [tshirt_line], "line_statuses": {str(tshirt_line): other_id}})
    assert refused.json()["detail"] == "return_status_invalid"
    # So is a status on a piece that isn't coming back.
    refused = as_atelier.post(return_url, json={"line_ids": [tshirt_line], "line_statuses": {str(apron_line): status_id}})
    assert refused.json()["detail"] == "return_status_invalid"
    assert _stock(as_atelier, desk["m"]) == before

    # The status is only a remark: the piece still goes to wash. A piece without one isn't listed.
    returned = as_atelier.post(
        return_url, json={"line_ids": [tshirt_line, apron_line], "line_statuses": {str(tshirt_line): status_id}}
    )
    assert returned.status_code == 200
    assert _stock(as_atelier, desk["m"]) == (2, 1, 0)
    issues = as_atelier.get(f"{BASE}/desk/return-issues", params={"festival_id": desk["festival"]}).json()
    assert [(row["status_name"], row["article_name"], row["person_name"]) for row in issues] == [
        ("Beschadigd", "T-shirt", "Jan Peeters")
    ]
    assert as_atelier.get(f"{BASE}/desk/return-issues", params={"day": "2026-07-04"}).json() == []

    # A used status can't be deleted, an unused one can.
    assert as_atelier.delete(f"{BASE}/return-statuses/{status_id}").status_code == 400
    assert as_atelier.delete(f"{BASE}/return-statuses/{other_id}").status_code == 204


def _sheet_rows(response) -> list[tuple]:
    """The rows of a downloaded workbook."""
    assert response.status_code == 200
    return list(load_workbook(BytesIO(response.content)).active.iter_rows(values_only=True))


def test_excel_downloads(client: TestClient, as_atelier: TestClient, db_session: Session, world: dict, desk: dict) -> None:
    handout = _pick_up(as_atelier, world, desk, [("tshirt", "m"), ("apron", "apron_size")], bracelet="B7").json()
    tshirt_line = next(line["id"] for line in handout["lines"] if line["article_name"] == "T-shirt")
    apron_line = next(line["id"] for line in handout["lines"] if line["article_name"] == "Schort")
    body = {"festival_id": desk["festival"], "day": DAY}

    # Openstaand: only the pieces the screen shows, in the user's language, no email.
    rows = _sheet_rows(as_atelier.post(f"{BASE}/desk/open/export", json={**body, "line_ids": [tshirt_line]}))
    assert rows[0][:3] == ("Ploeg", "Persoon", "Polsband")
    assert [row[4] for row in rows[1:]] == ["T-shirt"]
    assert rows[1][1:4] == ("Jan Peeters", "B7", "03-07-2026")
    assert not any("example.com" in str(cell).lower() for row in rows for cell in row)
    rows = _sheet_rows(as_atelier.post(f"{BASE}/desk/open/export", json={**body, "line_ids": [apron_line], "locale": "en"}))
    assert rows[0][0] == "Team" and [row[4] for row in rows[1:]] == ["Schort"]

    # Retourproblemen.
    status_id = as_atelier.post(f"{BASE}/return-statuses", json={"name": "=Beschadigd"}).json()["id"]
    as_atelier.post(
        f"{BASE}/desk/persons/{handout['person_id']}/return",
        json={"line_ids": [tshirt_line], "line_statuses": {str(tshirt_line): status_id}},
    )
    rows = _sheet_rows(as_atelier.post(f"{BASE}/desk/return-issues/export", json={**body, "line_ids": [tshirt_line]}))
    assert rows[0][0] == "Retourstatus"
    # A value that looks like a formula stays text.
    assert rows[1][:2] == ("'=Beschadigd", "T-shirt")
    assert not any("example.com" in str(cell).lower() for row in rows[1:] for cell in row[:9])
    assert len(_sheet_rows(as_atelier.post(f"{BASE}/desk/return-issues/export", json={**body, "line_ids": []}))) == 1

    # Each download needs view on its own screen.
    as_atelier.post("/api/auth/logout")
    role = _make_role(db_session, "Kijker", {"atelier.open": (True, False, False, False)})
    _make_user(db_session, world, "kijker@example.com", role)
    _login(client, "kijker@example.com")
    assert client.post(f"{BASE}/desk/open/export", json={**body, "line_ids": []}).status_code == 200
    assert client.post(f"{BASE}/desk/return-issues/export", json={**body, "line_ids": []}).status_code == 403

