# Tests for KarTracker's ground plans (the /groundplans endpoints in
# module_2/router.py): several plans can be added, listed, updated (with or
# without a new image) and deleted, and the image upload is validated.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.modules.module_2.router import MAX_GROUNDPLAN_IMAGE_BYTES
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)

URL = "/api/modules/module-2/groundplans"
BOUNDS = {"sw_latitude": "50.0", "sw_longitude": "4.0", "ne_latitude": "51.0", "ne_longitude": "5.0"}
PNG = ("plan.png", b"\x89PNG-small", "image/png")


def _login_super_admin(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")


def _create(client: TestClient, name: str, image=PNG, **bounds: str):
    return client.post(URL, data={"name": name, **BOUNDS, **bounds}, files={"image": image})


def test_multiple_groundplans_can_be_created_and_listed(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)

    first = _create(client, "Zone Zuid")
    second = _create(client, "Zone Noord", image=("noord.jpg", b"jpeg-bytes", "image/jpeg"), sw_latitude="50.5")

    assert first.status_code == 201
    assert second.status_code == 201
    listed = client.get(URL).json()
    # Ordered by name.
    assert [plan["name"] for plan in listed] == ["Zone Noord", "Zone Zuid"]
    assert listed[0]["sw_latitude"] == 50.5

    image = client.get(f"{URL}/{second.json()['id']}/image")
    assert image.status_code == 200
    assert image.content == b"jpeg-bytes"
    assert image.headers["content-type"] == "image/jpeg"


def test_groundplan_rejects_oversized_image(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)

    response = _create(client, "Te groot", image=("plan.png", b"x" * (MAX_GROUNDPLAN_IMAGE_BYTES + 1), "image/png"))

    assert response.status_code == 400
    assert "8 MB" in response.json()["detail"]


def test_groundplan_rejects_non_image_file(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)

    response = _create(client, "PDF", image=("plan.pdf", b"%PDF", "application/pdf"))

    assert response.status_code == 400


def test_groundplan_rejects_inverted_bounds(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)

    response = _create(client, "Omgekeerd", sw_latitude="52.0")

    assert response.status_code == 400


def test_groundplan_update_without_image_keeps_the_old_image(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    plan_id = _create(client, "Oud").json()["id"]

    response = client.put(f"{URL}/{plan_id}", data={"name": "Nieuw", **BOUNDS, "ne_longitude": "6.0"})

    assert response.status_code == 200
    assert response.json()["name"] == "Nieuw"
    assert response.json()["ne_longitude"] == 6.0
    assert client.get(f"{URL}/{plan_id}/image").content == PNG[1]


def test_groundplan_delete_removes_it(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)
    plan_id = _create(client, "Weg").json()["id"]

    assert client.delete(f"{URL}/{plan_id}").status_code == 204
    assert client.get(f"{URL}/{plan_id}/image").status_code == 404
    assert client.get(URL).json() == []


def test_groundplan_view_only_user_cannot_create(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(
        db_session, name="Grondplan Viewer", screen_key="kartracker.groundplan", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    assert client.get(URL).status_code == 200
    assert _create(client, "Niet toegestaan").status_code == 403
