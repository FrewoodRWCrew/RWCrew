# These tests check KarTracker's Karlijst phase: the KarStatussen lookup
# and the KarManagement fleet registry itself. Both are gated by their own
# screen keys ("kartracker.karstatuses"/"kartracker.karmanagement") through
# the same custom-roles system tested in test_roles.py, so here we focus on
# CRUD behaviour and the cross-module transport-type foreign key (into
# module-9's MasterData_product table) instead of re-proving the whole
# permission system from scratch.

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)


def _create_kar_status(db_session: Session, *, name: str = "Terug in Magazijn") -> KarTrackerKarStatus:
    kar_status = KarTrackerKarStatus(name=name)
    db_session.add(kar_status)
    db_session.commit()
    db_session.refresh(kar_status)
    return kar_status


def _create_product(db_session: Session, *, name: str = "Box") -> Product:
    product = Product(name=name)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _create_team(db_session: Session, *, name: str = "Scouts Wezemaal") -> Team:
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _login_as_admin(client: TestClient, db_session: Session) -> Module:
    """Set up and log in as a super admin with KarTracker access — the
    common starting point for most of these tests, which focus on the new
    endpoints' own behaviour rather than re-testing permission gating.
    """
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")
    return module


# --- KarStatussen CRUD -------------------------------------------------------


def test_create_and_list_kar_statuses(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)

    create_response = client.post("/api/modules/module-2/kar-statuses", json={"name": "In gebruik"})
    assert create_response.status_code == 201

    list_response = client.get("/api/modules/module-2/kar-statuses")
    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.json()] == ["In gebruik"]


def test_creating_a_kar_status_with_a_duplicate_name_is_rejected(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    _create_kar_status(db_session, name="In gebruik")

    response = client.post("/api/modules/module-2/kar-statuses", json={"name": "In gebruik"})

    assert response.status_code == 409


def test_deleting_a_kar_status_still_used_by_a_kar_is_rejected(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    db_session.add(KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, transport_type_id=product.id))
    db_session.commit()

    response = client.delete(f"/api/modules/module-2/kar-statuses/{kar_status.id}")

    assert response.status_code == 400


def test_deleting_an_unused_kar_status_succeeds(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)

    response = client.delete(f"/api/modules/module-2/kar-statuses/{kar_status.id}")

    assert response.status_code == 204


# --- KarManagement CRUD ------------------------------------------------------


def test_create_kar_succeeds_with_valid_lookup_ids(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    team = _create_team(db_session)

    response = client.post(
        "/api/modules/module-2/karren",
        json={
            "kar_nummer": "B001",
            "status_id": kar_status.id,
            "team_id": team.id,
            "transport_type_id": product.id,
            "last_latitude": 50.970128,
            "last_longitude": 4.686067,
            "last_recorded_at": "2026-07-06T00:00:00Z",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["kar_nummer"] == "B001"
    assert body["team_id"] == team.id


def test_create_kar_with_unknown_team_id_returns_404(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)

    response = client.post(
        "/api/modules/module-2/karren",
        json={"kar_nummer": "B001", "status_id": kar_status.id, "team_id": 9999, "transport_type_id": product.id},
    )

    assert response.status_code == 404


def test_create_kar_without_a_team_succeeds(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)

    response = client.post(
        "/api/modules/module-2/karren",
        json={"kar_nummer": "B001", "status_id": kar_status.id, "transport_type_id": product.id},
    )

    assert response.status_code == 201
    assert response.json()["team_id"] is None


def test_create_kar_with_unknown_status_id_returns_404(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    product = _create_product(db_session)

    response = client.post(
        "/api/modules/module-2/karren",
        json={"kar_nummer": "B001", "status_id": 9999, "transport_type_id": product.id},
    )

    assert response.status_code == 404


def test_create_kar_with_unknown_transport_type_id_returns_404(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)

    response = client.post(
        "/api/modules/module-2/karren",
        json={"kar_nummer": "B001", "status_id": kar_status.id, "transport_type_id": 9999},
    )

    assert response.status_code == 404


def test_creating_a_kar_with_a_duplicate_kar_nummer_is_rejected(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    db_session.add(KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, transport_type_id=product.id))
    db_session.commit()

    response = client.post(
        "/api/modules/module-2/karren",
        json={"kar_nummer": "B001", "status_id": kar_status.id, "transport_type_id": product.id},
    )

    assert response.status_code == 409


def test_update_kar_changes_its_fields(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session, name="Terug in Magazijn")
    other_status = _create_kar_status(db_session, name="In gebruik")
    product = _create_product(db_session)
    kar = KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, transport_type_id=product.id)
    db_session.add(kar)
    db_session.commit()
    db_session.refresh(kar)

    response = client.put(
        f"/api/modules/module-2/karren/{kar.id}",
        json={"kar_nummer": "B001", "status_id": other_status.id, "transport_type_id": product.id},
    )

    assert response.status_code == 200
    assert response.json()["status_id"] == other_status.id


def test_delete_kar_removes_it(client: TestClient, db_session: Session) -> None:
    _login_as_admin(client, db_session)
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    kar = KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, transport_type_id=product.id)
    db_session.add(kar)
    db_session.commit()
    db_session.refresh(kar)

    response = client.delete(f"/api/modules/module-2/karren/{kar.id}")

    assert response.status_code == 204
    assert db_session.get(KarTrackerKar, kar.id) is None


# --- permission gating, specific to the new screens --------------------------


def test_user_without_karmanagement_permission_cannot_view_karren(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Roles Only", screen_key="kartracker.roles", can_view=True)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    response = client.get("/api/modules/module-2/karren")

    assert response.status_code == 403


def test_user_with_karmanagement_view_only_cannot_create_a_kar(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(
        db_session, name="Kar Viewer", screen_key="kartracker.karmanagement", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    login(client, "member@example.com")

    list_response = client.get("/api/modules/module-2/karren")
    assert list_response.status_code == 200

    create_response = client.post(
        "/api/modules/module-2/karren",
        json={"kar_nummer": "B001", "status_id": kar_status.id, "transport_type_id": product.id},
    )
    assert create_response.status_code == 403
