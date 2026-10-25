# Atelier's masterdata (block 1): sizes (name + fit), articles with their
# sizes, the per-season team packages (incl. "copy from last season"), the
# KPI counts and the XLSX import/export — plus the per-screen rights.

import io

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.atelier_role import AtelierRole
from app.db.models.atelier_role_permission import AtelierRolePermission
from app.db.models.atelier_screen import AtelierScreen
from app.db.models.atelier_size import AtelierSize
from app.db.models.atelier_user_role import AtelierUserRole
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_5.screens import SCREEN_DEFINITIONS, sync_screens

BASE = "/api/modules/module-5"
EVERYTHING = (True, True, True, True)


def _make_role(db: Session, name: str, grants: dict[str, tuple[bool, bool, bool, bool]]) -> AtelierRole:
    """A role with (view, create, edit, delete) per screen key."""
    role = AtelierRole(name=name)
    db.add(role)
    db.flush()
    screens = {screen.key: screen for screen in db.scalars(select(AtelierScreen)).all()}
    for key, (can_view, can_create, can_edit, can_delete) in grants.items():
        db.add(
            AtelierRolePermission(
                role_id=role.id, screen_id=screens[key].id,
                can_view=can_view, can_create=can_create, can_edit=can_edit, can_delete=can_delete,
            )
        )
    db.commit()
    return role


@pytest.fixture()
def world(db_session: Session) -> dict:
    """The module, two seasons, two teams and the seeded-like sizes."""
    sync_screens(db_session)
    module = Module(key="module-5", name="Atelier", sort_order=5)
    previous = Season(name="2025", periode_open=False)
    season = Season(name="2026", periode_open=True)
    terras = Team(name="RW terras")
    vip = Team(name="VIP")
    old_team = Team(name="Oude ploeg", active=False)
    sizes = [
        AtelierSize(name="M", fit="men", sort_order=30),
        AtelierSize(name="M", fit="women", sort_order=30),
        AtelierSize(name="L", fit="men", sort_order=40),
        AtelierSize(name="OneSize", fit="unisex", sort_order=100),
    ]
    db_session.add_all([module, previous, season, terras, vip, old_team, *sizes])
    db_session.commit()
    return {"module": module, "previous": previous, "season": season, "terras": terras, "vip": vip, "sizes": sizes}


def _make_user(db: Session, world: dict, email: str, role: AtelierRole | None) -> User:
    """A user with Atelier access and the given role."""
    user = User(email=email, hashed_password=hash_password("password123"), display_name=email)
    db.add(user)
    db.flush()
    db.add(UserModuleAccess(user_id=user.id, module_id=world["module"].id))
    if role is not None:
        db.add(AtelierUserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


def _login(client: TestClient, email: str) -> None:
    assert client.post("/api/auth/login", json={"email": email, "password": "password123"}).status_code == 200


@pytest.fixture()
def as_atelier(client: TestClient, db_session: Session, world: dict) -> TestClient:
    """Logged in with every Atelier right."""
    role = _make_role(db_session, "Atelier", {definition.key: EVERYTHING for definition in SCREEN_DEFINITIONS})
    _make_user(db_session, world, "atelier@example.com", role)
    _login(client, "atelier@example.com")
    return client


def _size_id(world: dict, name: str, fit: str) -> int:
    return next(size.id for size in world["sizes"] if size.name == name and size.fit == fit)


def _create_article(client: TestClient, code: str = "TS-ZW", size_ids: list[int] = (), **fields) -> dict:
    payload = {"code": code, "name": fields.pop("name", f"T-shirt {code}"), "sizes": [{"size_id": i} for i in size_ids], **fields}
    response = client.post(f"{BASE}/articles", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- Sizes -------------------------------------------------------------------


def test_sizes_are_grouped_by_fit_and_unique_per_fit(as_atelier: TestClient) -> None:
    sizes = as_atelier.get(f"{BASE}/sizes").json()
    assert [(size["name"], size["fit"]) for size in sizes] == [
        ("M", "women"), ("M", "men"), ("L", "men"), ("OneSize", "unisex"),
    ]

    # "XL" for Women is new; a second "m" for Men is refused (case ignored).
    assert as_atelier.post(f"{BASE}/sizes", json={"name": "XL", "fit": "women", "sort_order": 50}).status_code == 201
    assert as_atelier.post(f"{BASE}/sizes", json={"name": "m", "fit": "men"}).status_code == 409
    # An unknown fit is a validation error.
    assert as_atelier.post(f"{BASE}/sizes", json={"name": "S", "fit": "kids"}).status_code == 422


def test_size_used_by_an_article_cant_be_deleted(as_atelier: TestClient, world: dict) -> None:
    m_men = _size_id(world, "M", "men")
    _create_article(as_atelier, size_ids=[m_men])

    assert as_atelier.delete(f"{BASE}/sizes/{m_men}").status_code == 400
    assert as_atelier.delete(f"{BASE}/sizes/{_size_id(world, 'L', 'men')}").status_code == 204


# --- Articles -----------------------------------------------------------------


def test_article_with_sizes_create_update_and_unique_code(as_atelier: TestClient, world: dict) -> None:
    m_men, l_men, m_women = _size_id(world, "M", "men"), _size_id(world, "L", "men"), _size_id(world, "M", "women")
    article = _create_article(as_atelier, size_ids=[l_men, m_men], colour="Zwart", cost="7.5")
    # Sizes come back in the size list's order, whatever order they were sent in.
    assert [row["size_id"] for row in article["sizes"]] == [m_men, l_men]
    assert article["has_image"] is False

    # The update replaces the size list: L (men) goes, M (women) comes.
    response = as_atelier.put(
        f"{BASE}/articles/{article['id']}",
        json={"code": "TS-ZW", "name": "T-shirt zwart", "sizes": [{"size_id": m_women}, {"size_id": m_men, "min_stock": 5}]},
    )
    assert response.status_code == 200
    assert [(row["size_id"], row["min_stock"]) for row in response.json()["sizes"]] == [(m_women, None), (m_men, 5)]

    # Codes are unique, ignoring case.
    assert as_atelier.post(f"{BASE}/articles", json={"code": "ts-zw", "name": "Dubbel"}).status_code == 409
    # The same size twice is refused.
    duplicate = {"code": "HD", "name": "Hoodie", "sizes": [{"size_id": m_men}, {"size_id": m_men}]}
    assert as_atelier.post(f"{BASE}/articles", json=duplicate).status_code == 400


def test_inactive_size_cant_be_added_but_stays_on_an_article(as_atelier: TestClient, world: dict) -> None:
    m_men, l_men = _size_id(world, "M", "men"), _size_id(world, "L", "men")
    article = _create_article(as_atelier, size_ids=[m_men])
    as_atelier.put(f"{BASE}/sizes/{m_men}", json={"name": "M", "fit": "men", "sort_order": 30, "active": False})
    as_atelier.put(f"{BASE}/sizes/{l_men}", json={"name": "L", "fit": "men", "sort_order": 40, "active": False})

    # M stays (already on the article), L can't be ticked any more.
    keep = {"code": "TS-ZW", "name": "T-shirt", "sizes": [{"size_id": m_men}]}
    assert as_atelier.put(f"{BASE}/articles/{article['id']}", json=keep).status_code == 200
    add = {"code": "TS-ZW", "name": "T-shirt", "sizes": [{"size_id": m_men}, {"size_id": l_men}]}
    assert as_atelier.put(f"{BASE}/articles/{article['id']}", json=add).status_code == 400


def test_article_picture_upload_view_and_remove(as_atelier: TestClient) -> None:
    article = _create_article(as_atelier)
    png = b"\x89PNG\r\n\x1a\nfake"
    response = as_atelier.put(f"{BASE}/articles/{article['id']}/image", files={"image": ("a.png", png, "image/png")})
    assert response.status_code == 200 and response.json()["has_image"] is True
    assert as_atelier.get(f"{BASE}/articles/{article['id']}/image").content == png

    gif = {"image": ("a.gif", b"GIF89a", "image/gif")}
    assert as_atelier.put(f"{BASE}/articles/{article['id']}/image", files=gif).status_code == 400
    assert as_atelier.delete(f"{BASE}/articles/{article['id']}/image").json()["has_image"] is False
    assert as_atelier.get(f"{BASE}/articles/{article['id']}/image").status_code == 404


def test_masterdata_stats(as_atelier: TestClient, world: dict) -> None:
    _create_article(as_atelier, "TS", size_ids=[_size_id(world, "M", "men"), _size_id(world, "L", "men")])
    _create_article(as_atelier, "OLD", active=False, size_ids=[_size_id(world, "M", "men")])

    assert as_atelier.get(f"{BASE}/masterdata-stats").json() == {
        "articles_active": 1,
        "articles_inactive": 1,
        "sizes_active": 4,
        "article_sizes_active": 2,
    }


# --- Rights -------------------------------------------------------------------------


def test_each_screen_needs_its_own_right(client: TestClient, db_session: Session, world: dict) -> None:
    # A role that may only view Artikelen: it sees articles and sizes (for
    # the form), but can't create, and can't open reservations or imports.
    role = _make_role(db_session, "Kijker", {"atelier.articles": (True, False, False, False)})
    _make_user(db_session, world, "kijker@example.com", role)
    _login(client, "kijker@example.com")

    assert client.get(f"{BASE}/articles").status_code == 200
    assert client.get(f"{BASE}/sizes").status_code == 200
    assert client.post(f"{BASE}/articles", json={"code": "X", "name": "X"}).status_code == 403
    assert client.post(f"{BASE}/sizes", json={"name": "S", "fit": "men"}).status_code == 403
    assert client.get(f"{BASE}/sizes/export").status_code == 403
    assert client.get(f"{BASE}/masterdata-stats").status_code == 403
    # The seasons list is open to every Atelier user.
    assert [season["name"] for season in client.get(f"{BASE}/seasons").json()] == ["2025", "2026"]


# --- XLSX import/export -----------------------------------------------------------


def _xlsx(header: list[str], rows: list[list]) -> bytes:
    workbook = Workbook()
    workbook.active.append(header)
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _upload(client: TestClient, path: str, content: bytes) -> list[dict]:
    response = client.post(f"{BASE}/{path}-import", files={"file": ("data.xlsx", content)})
    assert response.status_code == 200, response.text
    return response.json()["results"]


def test_xlsx_imports_and_round_trip(as_atelier: TestClient, world: dict) -> None:
    # Sizes: Dutch fit names are accepted; a duplicate and a bad fit are row errors.
    results = _upload(
        as_atelier, "sizes",
        _xlsx(["id", "name", "fit", "sort_order", "active"], [[None, "S", "Heren", 20, "ja"], [None, "M", "men", 30, None], [None, "XS", "kids", 10, None]]),
    )
    assert [row["outcome"] for row in results] == ["created", "error", "error"]

    # Articles, then their sizes by natural key.
    results = _upload(as_atelier, "articles", _xlsx(["id", "code", "name", "cost"], [[None, "TS", "T-shirt", "7,50"]]))
    assert results[0]["outcome"] == "created"
    results = _upload(
        as_atelier, "article-sizes",
        _xlsx(["article_code", "size", "fit", "min_stock"], [["ts", "M", "men", 10], ["TS", "M", "men", 10], ["TS", "XXXL", "men", None]]),
    )
    assert [row["outcome"] for row in results] == ["created", "unchanged", "error"]
    # Columns left out of the file keep their value: renaming via id leaves the price alone.
    article_id = as_atelier.get(f"{BASE}/articles").json()[0]["id"]
    assert _upload(as_atelier, "articles", _xlsx(["id", "code", "name"], [[article_id, "TS", "T-shirt crew"]]))[0]["outcome"] == "updated"
    article = as_atelier.get(f"{BASE}/articles").json()[0]
    assert (article["name"], article["cost"]) == ("T-shirt crew", 7.5)

    # Every template is just the header row.
    template = as_atelier.get(f"{BASE}/articles-import/template")
    rows = list(load_workbook(io.BytesIO(template.content)).active.iter_rows(values_only=True))
    assert rows == [("id", "code", "name", "description", "colour", "cost", "is_tag_managed", "active")]
