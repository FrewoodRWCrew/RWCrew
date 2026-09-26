# Tests for the read-only Kar Planning report (see kartracker.py's
# KarPlanningResponse and module_2/router.py's list_kar_planning): a join
# across KarManagement and its status/team/transport-type lookups, gated by
# its own "kartracker.karplanning" permission, independent of
# "kartracker.karmanagement" itself.

import re
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.kartracker_kar_afleverlocatie import KarTrackerKarAfleverlocatie
from app.db.models.kartracker_kar_status import KarTrackerKarStatus
from app.db.models.kartracker_leverdatum import KarTrackerLeverdatum
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.db.models.product import Product
from app.db.models.team import Team
from app.modules.module_2.karblad_pdf import KarbladData, KarbladFestival, build_karbladen_pdf, build_request_url
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)
from tests.modules.module_2.test_plan_kar import _create_festival, _create_location, _create_season


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
    report = response.json()
    # No season requested -> no festival columns.
    assert report["festivals"] == []
    rows = report["rows"]
    assert [row["kar_nummer"] for row in rows] == ["B001", "B002"]

    row_b001 = rows[0]
    assert row_b001["status_name"] == "In gebruik"
    assert row_b001["team_name"] == "Scouts Wezemaal"
    assert row_b001["transport_type_name"] == "Aanhangwagen"
    assert row_b001["geolocation"] == "51.05, 3.72"
    assert row_b001["afleverlocaties"] == {}

    row_b002 = rows[1]
    assert row_b002["team_name"] is None
    assert row_b002["geolocation"] is None


def test_kar_planning_adds_one_afleverlocatie_column_per_active_festival_of_the_season(
    client: TestClient, db_session: Session
) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")

    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    team = _create_team(db_session, name="Scouts Wezemaal")
    other_team = _create_team(db_session, name="Chiro Leuven")

    season = _create_season(db_session, name="2026")
    other_season = _create_season(db_session, name="2025")
    # Created out of order to prove the columns are sorted by start date.
    late = _create_festival(db_session, season_id=season.id, name="Late Fest", start_date="2026-08-01")
    early = _create_festival(db_session, season_id=season.id, name="Early Fest", start_date="2026-06-01")
    inactive = _create_festival(
        db_session, season_id=season.id, name="Closed Fest", start_date="2026-07-01", active=False
    )
    old = _create_festival(db_session, season_id=other_season.id, name="Old Fest", start_date="2025-07-01")

    poort = _create_location(db_session, name="Poort 1")
    poort.description = "Hoofdingang"
    db_session.commit()
    camping = _create_location(db_session, name="Camping", active=False)
    # `team` has a plan for both active festivals (one on a since-deactivated
    # location), the inactive festival and the other season's festival;
    # `other_team` has nothing planned.
    db_session.add_all(
        [
            KarTrackerKarAfleverlocatie(
                season_id=season.id, festival_id=early.id, team_id=team.id, afleverlocatie_id=poort.id
            ),
            KarTrackerKarAfleverlocatie(
                season_id=season.id, festival_id=late.id, team_id=team.id, afleverlocatie_id=camping.id
            ),
            KarTrackerKarAfleverlocatie(
                season_id=season.id, festival_id=inactive.id, team_id=team.id, afleverlocatie_id=poort.id
            ),
            KarTrackerKarAfleverlocatie(
                season_id=other_season.id, festival_id=old.id, team_id=team.id, afleverlocatie_id=poort.id
            ),
        ]
    )
    db_session.add_all(
        [
            KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, team_id=team.id, transport_type_id=product.id),
            KarTrackerKar(
                kar_nummer="B002", status_id=kar_status.id, team_id=other_team.id, transport_type_id=product.id
            ),
            KarTrackerKar(kar_nummer="B003", status_id=kar_status.id, team_id=None, transport_type_id=product.id),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/modules/module-2/kar-planning?season_id={season.id}")

    assert response.status_code == 200
    report = response.json()
    # Only the season's active festivals, earliest first.
    assert report["festivals"] == [
        {"id": early.id, "name": "Early Fest"},
        {"id": late.id, "name": "Late Fest"},
    ]
    by_kar = {row["kar_nummer"]: row["afleverlocaties"] for row in report["rows"]}
    # JSON object keys are strings. A location with a description is shown as
    # "name — description", one without as just its name.
    assert by_kar["B001"] == {str(early.id): "Poort 1 — Hoofdingang", str(late.id): "Camping"}
    assert by_kar["B002"] == {}
    assert by_kar["B003"] == {}


# --- Print (karbladen PDF) ---


def _page_count(pdf_bytes: bytes) -> int:
    """Number of page objects in a PDF (`/Type /Page`, but not `/Type /Pages`)."""
    return len(re.findall(rb"/Type /Page(?!s)", pdf_bytes))


def _print_payload(season_id: int, kar_ids: list[int]) -> dict:
    return {"season_id": season_id, "kar_ids": kar_ids, "site_url": "https://rwcrew.eu", "locale": "nl"}


def test_print_returns_one_pdf_page_per_selected_kar(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    team = _create_team(db_session)

    season = _create_season(db_session, name="Rock Werchter 2026")
    festival = _create_festival(db_session, season_id=season.id, name="Rock Werchter", start_date="2026-07-02")
    poort = _create_location(db_session, name="Poort 1")
    db_session.add_all(
        [
            KarTrackerKarAfleverlocatie(
                season_id=season.id, festival_id=festival.id, team_id=team.id, afleverlocatie_id=poort.id
            ),
            KarTrackerLeverdatum(
                festival_id=festival.id, delivery_date=date(2026, 6, 20), pickup_date=date(2026, 7, 6)
            ),
        ]
    )
    # A kar with a planned team, one without a team, and one that isn't selected.
    kars = [
        KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, team_id=team.id, transport_type_id=product.id),
        KarTrackerKar(kar_nummer="B002", status_id=kar_status.id, team_id=None, transport_type_id=product.id),
        KarTrackerKar(kar_nummer="B003", status_id=kar_status.id, team_id=team.id, transport_type_id=product.id),
    ]
    db_session.add_all(kars)
    db_session.commit()

    response = client.post(
        "/api/modules/module-2/kar-planning/print", json=_print_payload(season.id, [kars[0].id, kars[1].id])
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert _page_count(response.content) == 2


def test_print_rejects_unknown_season_and_empty_selection(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    admin = create_user(db_session, email="admin@example.com", is_super_admin=True)
    grant_module_access(db_session, admin, module)
    login(client, "admin@example.com")
    kar_status = _create_kar_status(db_session)
    product = _create_product(db_session)
    season = _create_season(db_session)
    kar = KarTrackerKar(kar_nummer="B001", status_id=kar_status.id, team_id=None, transport_type_id=product.id)
    db_session.add(kar)
    db_session.commit()

    unknown_season = client.post("/api/modules/module-2/kar-planning/print", json=_print_payload(9999, [kar.id]))
    no_karren = client.post("/api/modules/module-2/kar-planning/print", json=_print_payload(season.id, [9999]))
    empty_selection = client.post("/api/modules/module-2/kar-planning/print", json=_print_payload(season.id, []))

    assert unknown_season.status_code == 404
    assert no_karren.status_code == 404
    assert empty_selection.status_code == 422


def test_user_without_karplanning_permission_cannot_print(client: TestClient, db_session: Session) -> None:
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="member@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(
        db_session, name="Kar Viewer", screen_key="kartracker.karmanagement", can_view=True
    )
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "member@example.com")

    response = client.post("/api/modules/module-2/kar-planning/print", json=_print_payload(1, [1]))

    assert response.status_code == 403


def test_request_url_prefills_known_fields_and_skips_blanks() -> None:
    url = build_request_url("https://rwcrew.eu/", "nl", 7, "B051", "Inside Merch A-terrein", "INSI_39")
    assert url == (
        "https://rwcrew.eu/nl/intervention-request?"
        "team_id=7&cart_number=B051&delivery_location=Inside+Merch+A-terrein&zone=INSI_39"
    )

    # A kar without a team or plan only carries its number.
    assert build_request_url("https://rwcrew.eu", "en", None, "B002", None, None) == (
        "https://rwcrew.eu/en/intervention-request?cart_number=B002"
    )


def test_karblad_pdf_handles_many_festivals_and_non_latin1_text() -> None:
    festivals = [KarbladFestival(name=f"Fest {index}", zone_name="Z", location="Poort — Ł") for index in range(6)]
    kar = KarbladData(kar_nummer="B001", team_name="Chiro Łódź", transport_type="Box", festivals=festivals)

    pdf = build_karbladen_pdf([kar, kar], "Rock Werchter 2026", "en")

    assert pdf.startswith(b"%PDF")
    assert _page_count(pdf) == 2
