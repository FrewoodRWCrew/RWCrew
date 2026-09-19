# Tests for the ground-plan upload (PUT /groundplan in module_2/router.py):
# an image within the size limit is stored, an oversized one is rejected.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.module_2.router import MAX_GROUNDPLAN_IMAGE_BYTES
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import create_kartracker_module, create_user, grant_module_access, login

BOUNDS = {"sw_latitude": "50.0", "sw_longitude": "4.0", "ne_latitude": "51.0", "ne_longitude": "5.0"}


def _login_super_admin(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")


def test_groundplan_accepts_image_within_limit(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)

    response = client.put(
        "/api/modules/module-2/groundplan",
        data=BOUNDS,
        files={"image": ("plan.png", b"\x89PNG-small", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["has_image"] is True


def test_groundplan_rejects_oversized_image(client: TestClient, db_session: Session) -> None:
    _login_super_admin(client, db_session)

    response = client.put(
        "/api/modules/module-2/groundplan",
        data=BOUNDS,
        files={"image": ("plan.png", b"x" * (MAX_GROUNDPLAN_IMAGE_BYTES + 1), "image/png")},
    )

    assert response.status_code == 400
    assert "8 MB" in response.json()["detail"]
