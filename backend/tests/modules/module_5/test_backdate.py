# Back-dated Atelier bookings (`booked_at`), used to load last year's desk
# lists (backend/masstest): only a super admin may send one, never in the
# future; the booking, the pick-up and the return keep that moment (a time
# without a zone is Belgian time), the document number takes its Belgian
# year, the wash statistics follow it, and back-dated desk actions never mail.

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.mail import OutgoingMail
from app.db.models.atelier_handout import AtelierHandout
from app.db.models.atelier_handout_line import AtelierHandoutLine
from app.db.models.atelier_stock_document import AtelierStockDocument
from app.db.models.user import User
from tests.modules.module_5.test_desk import _pick_up, desk  # noqa: F401  (fixture)
from tests.modules.module_5.test_mails import sent  # noqa: F401  (fixture)
from tests.modules.module_5.test_masterdata import (  # noqa: F401  (fixtures)
    BASE,
    as_atelier,
    world,
)


@pytest.fixture()
def as_super_admin(as_atelier: TestClient, db_session: Session) -> TestClient:
    """The logged-in Atelier user (every right) is also super admin."""
    user = db_session.scalar(select(User).where(User.email == "atelier@example.com"))
    user.is_super_admin = True
    db_session.commit()
    return as_atelier


def _utc(moment: datetime) -> datetime:
    """A stored moment as aware UTC (SQLite hands it back without a zone)."""
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def _back_dated_pick_up(client: TestClient, world: dict, desk: dict, booked_at: str):
    """Jan picks up a T-shirt, booked at `booked_at`."""
    return client.post(
        f"{BASE}/desk/handouts",
        json={"first_name": "Jan", "last_name": "Peeters", "email": "jan@example.com",
              "festival_id": desk["festival"], "team_id": world["terras"].id, "day": "2026-07-03",
              "lines": [{"article_id": desk["tshirt"], "article_size_id": desk["m"]}], "booked_at": booked_at},
    )


def test_only_a_super_admin_and_never_in_the_future(
    as_atelier: TestClient, db_session: Session, world: dict, desk: dict
) -> None:
    refused = _back_dated_pick_up(as_atelier, world, desk, "2026-07-03T10:15:00")
    assert (refused.status_code, refused.json()["detail"]) == (403, "backdate_not_allowed")
    receipt = as_atelier.post(
        f"{BASE}/stock/receipt",
        json={"lines": [{"article_size_id": desk["m"], "quantity": 1}], "booked_at": "2026-06-01T09:00:00"},
    )
    assert (receipt.status_code, receipt.json()["detail"]) == (403, "backdate_not_allowed")

    user = db_session.scalar(select(User).where(User.email == "atelier@example.com"))
    user.is_super_admin = True
    db_session.commit()
    future = _back_dated_pick_up(as_atelier, world, desk, "2999-07-03T10:15:00")
    assert (future.status_code, future.json()["detail"]) == (400, "backdate_in_future")


def test_pick_up_and_return_keep_their_moment_and_send_no_mail(
    as_super_admin: TestClient, db_session: Session, world: dict, desk: dict, sent: list[OutgoingMail]
) -> None:
    # 10:15 Belgian summer time = 08:15 UTC.
    handout = _back_dated_pick_up(as_super_admin, world, desk, "2026-07-03T10:15:00")
    assert handout.status_code == 201
    handout = handout.json()
    stored = db_session.get(AtelierHandout, handout["id"])
    assert _utc(stored.created_at) == datetime(2026, 7, 3, 8, 15, tzinfo=timezone.utc)
    document = db_session.get(AtelierStockDocument, stored.stock_document_id)
    assert _utc(document.created_at) == datetime(2026, 7, 3, 8, 15, tzinfo=timezone.utc)

    response = as_super_admin.post(
        f"{BASE}/desk/persons/{handout['person_id']}/return",
        json={"line_ids": [handout["lines"][0]["id"]], "booked_at": "2026-07-03T23:40:00+02:00"},
    )
    assert response.status_code == 200
    line = db_session.get(AtelierHandoutLine, handout["lines"][0]["id"])
    assert _utc(line.returned_at) == datetime(2026, 7, 3, 21, 40, tzinfo=timezone.utc)
    returned = db_session.get(AtelierStockDocument, line.return_document_id)
    assert _utc(returned.created_at) == datetime(2026, 7, 3, 21, 40, tzinfo=timezone.utc)
    # Last year's people get no mail; a normal pick-up still mails.
    assert sent == []
    assert _pick_up(as_super_admin, world, desk, [("apron", "apron_size")]).status_code == 201
    assert len(sent) == 1


def test_document_number_year_and_wash_stats_follow_the_moment(
    as_super_admin: TestClient, db_session: Session, world: dict, desk: dict
) -> None:
    # 00:30 on 1 January in Belgium is still 31 December in UTC: the Belgian year counts.
    receipt = as_super_admin.post(
        f"{BASE}/stock/receipt",
        json={"lines": [{"article_size_id": desk["m"], "quantity": 2}], "booked_at": "2026-01-01T00:30:00"},
    ).json()
    assert receipt["doc_number"].startswith("AT-2026-")

    # A piece comes back (to wash) and is washed back-dated on 4 July: the
    # wash statistics show it on that festival day.
    handout = _back_dated_pick_up(as_super_admin, world, desk, "2026-07-03T10:00:00").json()
    as_super_admin.post(
        f"{BASE}/desk/persons/{handout['person_id']}/return",
        json={"line_ids": [handout["lines"][0]["id"]], "booked_at": "2026-07-03T22:00:00"},
    )
    washed = as_super_admin.post(
        f"{BASE}/stock/wash",
        json={"lines": [{"article_size_id": desk["m"], "quantity": 1}], "booked_at": "2026-07-04T09:00:00"},
    )
    assert washed.status_code == 201
    stats = as_super_admin.get(f"{BASE}/stock/wash-stats", params={"season_id": world["season"].id}).json()
    assert stats["festivals"][0]["days"] == [{"day": "2026-07-04", "pieces": 1}]
