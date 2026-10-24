# These tests check the "update instead of reject" rule of the Zones,
# Distributiepunten and Afleverlocaties tiles on KarTracker's "Data Upload/
# Download" screen. They call the import functions directly (the endpoints
# around them only add the "kartracker.dataupload" permission check, which
# test_kar_import.py already covers): a name that already exists (ignoring
# case) updates the record, filled-in cells overwrite, empty cells keep the
# saved value, and a name repeated in one file is an error.

import io

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.kartracker_afleverlocatie import KarTrackerAfleverlocatie
from app.db.models.kartracker_distributiepunt import KarTrackerDistributiepunt
from app.db.models.kartracker_zone import KarTrackerZone
from app.modules.module_2.afleverlocatie_import import import_afleverlocaties_from_xlsx
from app.modules.module_2.distributiepunt_import import import_distributiepunten_from_xlsx
from app.modules.module_2.zone_import import import_zones_from_xlsx


def _build_xlsx(header: list[str], rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _create_zone(db_session: Session, name: str = "Zone A") -> KarTrackerZone:
    zone = KarTrackerZone(name=name)
    db_session.add(zone)
    db_session.commit()
    return zone


def _create_distributiepunt(db_session: Session, name: str = "DP 1", **fields) -> KarTrackerDistributiepunt:
    distributiepunt = KarTrackerDistributiepunt(name=name, **fields)
    db_session.add(distributiepunt)
    db_session.commit()
    return distributiepunt


def test_zone_import_leaves_an_existing_name_unchanged(db_session: Session) -> None:
    _create_zone(db_session, "Zone A")

    results = import_zones_from_xlsx(db_session, _build_xlsx(["name"], [["zone a"], ["Zone B"], ["Zone B"]]))

    assert [result.outcome for result in results] == ["unchanged", "created", "error"]
    # "zone a" matched "Zone A" instead of becoming a second zone.
    assert db_session.scalar(select(func.count()).select_from(KarTrackerZone)) == 2


def test_distributiepunt_import_updates_filled_cells_and_keeps_empty_ones(db_session: Session) -> None:
    _create_distributiepunt(db_session, "DP 1", latitude=50.9, longitude=4.8, terrein_positie="Noord")

    results = import_distributiepunten_from_xlsx(
        db_session,
        _build_xlsx(["name", "latitude", "longitude", "terrein_positie"], [["dp 1", 51.0, None, None]]),
    )

    assert [result.outcome for result in results] == ["updated"]
    db_session.expire_all()
    distributiepunt = db_session.scalar(select(KarTrackerDistributiepunt))
    assert distributiepunt.name == "DP 1"  # the saved spelling is kept
    assert distributiepunt.latitude == 51.0
    assert distributiepunt.longitude == 4.8
    assert distributiepunt.terrein_positie == "Noord"


def test_afleverlocatie_import_updates_and_keeps_active_when_blank(db_session: Session) -> None:
    zone = _create_zone(db_session, "Zone A")
    other_zone = _create_zone(db_session, "Zone B")
    distributiepunt = _create_distributiepunt(db_session)
    db_session.add(
        KarTrackerAfleverlocatie(
            name="Loc 1",
            description="Achter de tent",
            zone_id=zone.id,
            distributiepunt_id=distributiepunt.id,
            latitude=50.9,
            active=False,
        )
    )
    db_session.commit()

    header = ["name", "description", "zone_name", "distributiepunt_name", "latitude", "active"]
    results = import_afleverlocaties_from_xlsx(
        db_session,
        _build_xlsx(
            header,
            [
                # Existing: new zone + latitude; description and active left empty.
                ["Loc 1", None, "Zone B", None, 51.0, None],
                # New: zone and distributiepunt given, blank active means active.
                ["Loc 2", None, "Zone A", "DP 1", None, None],
                # New without a zone: still required for a new location.
                ["Loc 3", None, None, "DP 1", None, None],
            ],
        ),
    )

    assert [result.outcome for result in results] == ["updated", "created", "error"]
    db_session.expire_all()
    updated = db_session.scalar(select(KarTrackerAfleverlocatie).where(KarTrackerAfleverlocatie.name == "Loc 1"))
    assert updated.zone_id == other_zone.id
    assert updated.latitude == 51.0
    assert updated.description == "Achter de tent"
    assert updated.active is False
    created = db_session.scalar(select(KarTrackerAfleverlocatie).where(KarTrackerAfleverlocatie.name == "Loc 2"))
    assert created.active is True


def test_afleverlocatie_import_reads_terrein_positie_as_a_whole_number(db_session: Session) -> None:
    _create_zone(db_session, "Zone A")
    _create_distributiepunt(db_session)

    header = ["name", "zone_name", "distributiepunt_name", "terrein_positie"]
    results = import_afleverlocaties_from_xlsx(
        db_session,
        _build_xlsx(
            header,
            [
                # Excel may hand over a whole number as a float.
                ["Loc 1", "Zone A", "DP 1", 3.0],
                ["Loc 2", "Zone A", "DP 1", "Noord"],
                ["Loc 3", "Zone A", "DP 1", 0],
            ],
        ),
    )

    assert [result.outcome for result in results] == ["created", "error", "error"]
    created = db_session.scalar(select(KarTrackerAfleverlocatie).where(KarTrackerAfleverlocatie.name == "Loc 1"))
    assert created.terrein_positie == 3
