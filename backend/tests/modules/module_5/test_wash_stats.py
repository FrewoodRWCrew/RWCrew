# Atelier's wash statistics on the KPI page: pieces washed per Belgian day,
# linked to a festival by date (a day after the festival stays in its season,
# in the "no festival" group), undone washes left out, and the KPI right.

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.festival import Festival
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    _login,
    _make_role,
    _make_user,
    as_atelier,
    world,
)
from tests.modules.module_5.test_stock import _put_to_wash, tshirt  # noqa: F401  (fixture)


@pytest.fixture()
def festivals(db_session: Session, world: dict) -> dict:
    """Rock Werchter (2–5 July 2026) in this season, one in the previous season."""
    rw = Festival(name="Rock Werchter", start_date=date(2026, 7, 2), end_date=date(2026, 7, 5), season_id=world["season"].id)
    old = Festival(name="Rock Werchter 2025", start_date=date(2025, 7, 3), end_date=date(2025, 7, 6), season_id=world["previous"].id)
    db_session.add_all([rw, old])
    db_session.commit()
    return {"rw": rw, "old": old}


def _wash(client: TestClient, db_session: Session, article_size_id: int, quantity: int, moment: datetime) -> int:
    """Book a wash through the API and move its booking moment (UTC) to `moment`."""
    document = client.post(
        f"{BASE}/stock/wash", json={"lines": [{"article_size_id": article_size_id, "quantity": quantity}]}
    ).json()
    db_session.get(AtelierStockDocument, document["id"]).created_at = moment
    db_session.commit()
    return document["id"]


def test_wash_stats_per_day_and_festival(
    as_atelier: TestClient, db_session: Session, world: dict, tshirt: dict, festivals: dict
) -> None:
    _put_to_wash(db_session, world, tshirt["m"], 40)
    utc = timezone.utc
    # 3 July: two washes on the same festival day add up.
    _wash(as_atelier, db_session, tshirt["m"], 5, datetime(2026, 7, 3, 9, 0, tzinfo=utc))
    _wash(as_atelier, db_session, tshirt["m"], 2, datetime(2026, 7, 3, 15, 0, tzinfo=utc))
    # 22:30 UTC on 4 July = 00:30 on 5 July in Belgium (summer time).
    _wash(as_atelier, db_session, tshirt["m"], 3, datetime(2026, 7, 4, 22, 30, tzinfo=utc))
    # 7 July: after the festival, still this season, in the "no festival" group.
    _wash(as_atelier, db_session, tshirt["m"], 4, datetime(2026, 7, 7, 10, 0, tzinfo=utc))
    # Last season's festival: not in this season's view.
    _wash(as_atelier, db_session, tshirt["m"], 6, datetime(2025, 7, 4, 10, 0, tzinfo=utc))
    # An undone wash is left out.
    undone = _wash(as_atelier, db_session, tshirt["m"], 9, datetime(2026, 7, 3, 11, 0, tzinfo=utc))
    assert as_atelier.post(f"{BASE}/stock/documents/{undone}/reverse", json={}).status_code == 200

    stats = as_atelier.get(f"{BASE}/stock/wash-stats", params={"season_id": world["season"].id}).json()
    assert stats["total"] == 14
    rw, none = stats["festivals"]
    assert (rw["festival_name"], rw["pieces"]) == ("Rock Werchter", 10)
    assert rw["days"] == [{"day": "2026-07-03", "pieces": 7}, {"day": "2026-07-05", "pieces": 3}]
    assert (none["festival_id"], none["pieces"], none["days"]) == (None, 4, [{"day": "2026-07-07", "pieces": 4}])

    previous = as_atelier.get(f"{BASE}/stock/wash-stats", params={"season_id": world["previous"].id}).json()
    assert previous["total"] == 6
    assert previous["festivals"][0]["festival_name"] == "Rock Werchter 2025"


def test_wash_stats_needs_the_kpi_right(client: TestClient, db_session: Session, world: dict) -> None:
    role = _make_role(db_session, "Wassen", {"atelier.wash": (True, True, False, False)})
    _make_user(db_session, world, "wasser@example.com", role)
    _login(client, "wasser@example.com")
    response = client.get(f"{BASE}/stock/wash-stats", params={"season_id": world["season"].id})
    assert response.status_code == 403
