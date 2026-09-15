# Tests for the read-only Kar Planning report (see kartracker.py's
# KarPlanningResponse and module_2/router.py's list_kar_planning): a join
# across KarManagement and its status/team/transport-type lookups, gated by
# its own "kartracker.karplanning" permission, independent of
# "kartracker.karmanagement" itself.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.product import Product
from app.db.models.team import Team
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


def test_user_without_karplanning_permission_cannot_view_it(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    # Has view access to the CRUD screen but not the new report screen —
    # the two permissions must stay independent of each other.
    role = create_role_with_permissions(
        db_session, name="Kar Viewer", screen_key="kartracker.karmanagement", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    response = client.get("/api/modules/module-2/kar-planning")

    assert response.status_code == 403


def test_kar_planning_returns_denormalized_joined_fields(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")

    kar_status = _create_kar_status(db_session, name="In gebruik")
    product = _create_product(db_session, name="Aanhangwagen")
    team = _create_team(db_session, name="Scouts Wezemaal")

    kar_with_team_and_location = KarTrackerKar(
        kar_nummer="B001",
        status_id=kar_status.id,
        team_id=team.id,
        transport_type_id=product.id,
        last_latitude=51.05,
        last_longitude=3.72,
    )
    kar_without_team_or_location = KarTrackerKar(
        kar_nummer="B002",
        status_id=kar_status.id,
        team_id=None,
        transport_type_id=product.id,
    )
    db_session.add_all([kar_with_team_and_location, kar_without_team_or_location])
    db_session.commit()

    response = client.get("/api/modules/module-2/kar-planning")

    assert response.status_code == 200
    rows = response.json()
    assert [row["kar_nummer"] for row in rows] == ["B001", "B002"]

    row_b001 = rows[0]
    assert row_b001["status_name"] == "In gebruik"
    assert row_b001["team_name"] == "Scouts Wezemaal"
    assert row_b001["transport_type_name"] == "Aanhangwagen"
    assert row_b001["geolocation"] == "51.05, 3.72"

    row_b002 = rows[1]
    assert row_b002["team_name"] is None
    assert row_b002["geolocation"] is None
