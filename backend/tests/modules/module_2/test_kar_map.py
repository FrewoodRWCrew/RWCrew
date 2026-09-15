# Tests for the read-only Kar Map screen (see kartracker.py's
# KarMapResponse and module_2/router.py's list_kar_map): a combined
# Kar/Afleverlocatie/Distributiepunt payload, gated by its own
# "kartracker.karmap" permission, independent of the underlying masterdata
# screens' own view permissions.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.kartracker_zone import KarTrackerZone
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


def _create_zone(db_session: Session, *, name: str = "Zone A") -> KarTrackerZone:
    zone = KarTrackerZone(name=name)
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)
    return zone


def _create_distributiepunt(
    db_session: Session,
    *,
    name: str = "Distributiepunt A",
    latitude: float | None = None,
    longitude: float | None = None,
) -> KarTrackerDistributiepunt:
    distributiepunt = KarTrackerDistributiepunt(name=name, latitude=latitude, longitude=longitude)
    db_session.add(distributiepunt)
    db_session.commit()
    db_session.refresh(distributiepunt)
    return distributiepunt


def test_user_without_karmap_permission_cannot_view_it(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    # Has view access to the CRUD screen but not the new map screen — the
    # two permissions must stay independent of each other.
    role = create_role_with_permissions(
        db_session, name="Kar Viewer", screen_key="kartracker.karmanagement", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    response = client.get("/api/modules/module-2/kar-map")

    assert response.status_code == 403


def test_kar_map_returns_all_three_layers_including_rows_without_coordinates(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")

    kar_status = _create_kar_status(db_session, name="In gebruik")
    product = _create_product(db_session)
    team = _create_team(db_session, name="Scouts Wezemaal")
    zone = _create_zone(db_session)
    distributiepunt_located = _create_distributiepunt(
        db_session, name="Distributiepunt Located", latitude=50.9, longitude=4.5
    )
    distributiepunt_unlocated = _create_distributiepunt(db_session, name="Distributiepunt Unlocated")

    kar_located = KarTrackerKar(
        kar_nummer="B001",
        status_id=kar_status.id,
        team_id=team.id,
        transport_type_id=product.id,
        last_latitude=51.05,
        last_longitude=3.72,
    )
    kar_unlocated = KarTrackerKar(
        kar_nummer="B002",
        status_id=kar_status.id,
        team_id=None,
        transport_type_id=product.id,
    )
    db_session.add_all([kar_located, kar_unlocated])

    afleverlocatie_located = KarTrackerAfleverlocatie(
        name="Afleverlocatie Located",
        zone_id=zone.id,
        distributiepunt_id=distributiepunt_located.id,
        latitude=51.0,
        longitude=3.7,
    )
    afleverlocatie_unlocated = KarTrackerAfleverlocatie(
        name="Afleverlocatie Unlocated",
        zone_id=zone.id,
        distributiepunt_id=distributiepunt_located.id,
    )
    db_session.add_all([afleverlocatie_located, afleverlocatie_unlocated])
    db_session.commit()

    response = client.get("/api/modules/module-2/kar-map")

    assert response.status_code == 200
    body = response.json()

    assert len(body["karren"]) == 2
    assert len(body["afleverlocaties"]) == 2
    assert len(body["distributiepunten"]) == 2

    karren_by_nummer = {row["kar_nummer"]: row for row in body["karren"]}
    assert karren_by_nummer["B001"]["status_name"] == "In gebruik"
    assert karren_by_nummer["B001"]["team_name"] == "Scouts Wezemaal"
    assert karren_by_nummer["B001"]["latitude"] == 51.05
    assert karren_by_nummer["B001"]["longitude"] == 3.72
    assert karren_by_nummer["B002"]["team_name"] is None
    assert karren_by_nummer["B002"]["latitude"] is None
    assert karren_by_nummer["B002"]["longitude"] is None

    afleverlocaties_by_name = {row["name"]: row for row in body["afleverlocaties"]}
    assert afleverlocaties_by_name["Afleverlocatie Located"]["zone_name"] == "Zone A"
    assert afleverlocaties_by_name["Afleverlocatie Located"]["distributiepunt_name"] == "Distributiepunt Located"
    assert afleverlocaties_by_name["Afleverlocatie Located"]["latitude"] == 51.0
    assert afleverlocaties_by_name["Afleverlocatie Unlocated"]["latitude"] is None
    assert afleverlocaties_by_name["Afleverlocatie Unlocated"]["longitude"] is None

    distributiepunten_by_name = {row["name"]: row for row in body["distributiepunten"]}
    assert distributiepunten_by_name["Distributiepunt Located"]["latitude"] == 50.9
    assert distributiepunten_by_name["Distributiepunt Located"]["longitude"] == 4.5
    assert distributiepunten_by_name["Distributiepunt Unlocated"]["latitude"] is None
    assert distributiepunten_by_name["Distributiepunt Unlocated"]["longitude"] is None
