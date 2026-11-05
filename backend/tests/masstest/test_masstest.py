# The mass test (backend/masstest): converting last year's Uitgifte/Inname
# list into the load workbook, the solution rules and texts, the report, and
# a full run against the real app (in-memory database) through an httpx
# transport that forwards to the TestClient — what loads, what is skipped
# and logged with which code, that a second run loads nothing twice, that a
# dry run writes nothing, and that back-dated bookings keep their moment and
# send no mail.

from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.mail import OutgoingMail
from app.db.models.atelier_handout import AtelierHandout
from app.db.models.masterdata_role import MasterDataRole
from app.db.models.masterdata_role_permission import MasterDataRolePermission
from app.db.models.masterdata_screen import MasterDataScreen
from app.db.models.masterdata_user_role import MasterDataUserRole
from app.db.models.module import Module
from app.db.models.team_alias import TeamAlias
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_9.screens import sync_screens as sync_masterdata_screens
from app.modules.module_9.team_alias_service import normalize_name
from masstest.convert.atelier_desk import convert_atelier_desk
from masstest.environments import Environment
from masstest.ledger import Ledger
from masstest.load_workbook import ATELIER_DESK, read_sheet, write_sheets
from masstest.messages import translate
from masstest.report import IssueLog, write_report
from masstest.runner import run
from masstest.solutions import propose
from tests.modules.module_5.test_desk import desk  # noqa: F401  (fixture)
from tests.modules.module_5.test_mails import sent  # noqa: F401  (fixture)
from tests.modules.module_5.test_masterdata import as_atelier, world  # noqa: F401  (fixtures)

HEADER = ["datum", "group", "ophaler", "magazijn", "beschrijving", "aantal", "gebroken aantal", "product", "product subtype"]


def _source(path: Path, rows: list[list[object]]) -> Path:
    """An old Uitgifte/Inname list with these rows."""
    workbook = Workbook()
    workbook.active.append(HEADER)
    for row in rows:
        workbook.active.append(row)
    workbook.save(path)
    return path


def _line(moment: str, group: str, person: str, quantity: int, product: str, subtype: str) -> list[object]:
    return [moment, group, person, "Uitleendienst", None, quantity, None, product, subtype]


# --- Converter, rules, texts, report -------------------------------------------------


def test_convert_groups_transactions_and_logs_unreadable_rows(tmp_path: Path) -> None:
    source = _source(tmp_path / "old.xlsx", [
        _line("2026-06-27 08:36:14", "Albertieners vzw  (TOOG 24)", "Veerle De Roock", 1, "VIP T-shirt", "man L"),
        _line("2026-06-27 08:36:14", "Albertieners vzw  (TOOG 24)", "Veerle De Roock", 1, "VIP Schort", "man OneSize"),
        _line("2026-06-19 20:13:26", "123 Rotte pataten vzw", "David Andries", -2, "Test Users schort", "man OneSize"),
        _line("niet-een-datum", "X", "Jo De Wel", 1, "Schort", "man M"),
        _line("2026-06-19 20:13:26", "X", "Madonna", 1, "Schort", "man M"),
        _line("2026-06-19 20:13:26", "X", "Jo De Wel", 0, "Schort", "man M"),
        _line("2026-06-19 20:13:26", "X", "Jo De Wel", 1, "Schort", "kind M"),
    ])
    log = IssueLog("convert")
    columns, rows = convert_atelier_desk(source, log)[ATELIER_DESK]

    # Time order: the return of the 19th first; Veerle's two pieces are one transaction.
    assert [(row["transaction"], row["action"], row["quantity"]) for row in rows] == [
        ("T00001", "terugbrengen", 2), ("T00002", "ophalen", 1), ("T00002", "ophalen", 1)
    ]
    veerle = rows[1]
    assert (veerle["first_name"], veerle["last_name"], veerle["team"], veerle["fit"], veerle["size"]) == (
        "Veerle", "De Roock", "Albertieners vzw (TOOG 24)", "men", "L"
    )
    assert (veerle["booked_at"], veerle["day"], veerle["source_row"]) == ("2026-06-27 08:36:14", "2026-06-27", 2)
    assert [issue.code for issue in log.issues] == ["date_invalid", "name_required", "quantity_invalid", "fit_unknown"]
    assert log.issues[0].source_rows == "5" and "ophaler=Jo De Wel" in log.issues[0].source_values

    # The load workbook round-trips.
    path = write_sheets(tmp_path / "load.xlsx", {ATELIER_DESK: (columns, rows)})
    assert [row["transaction"] for row in read_sheet(path, ATELIER_DESK)] == ["T00001", "T00002", "T00002"]
    assert read_sheet(path, "Nope") is None


def test_rules_texts_and_report(tmp_path: Path) -> None:
    rule = propose("not_in_package", ["Pet"], {"team": "RW terras", "festival": "Rock Werchter"})
    assert rule.category == "data"
    assert "Add article Pet to the package of team RW terras for Rock Werchter" in rule.solution
    assert propose("brand_new_code").category == "bug"
    assert translate("atelier", "article_still_out|T-shirt") == "T-shirt is nog niet teruggebracht — eerst terugbrengen."
    assert translate("atelier", "nonsense|x") == "nonsense|x"

    log = IssueLog("local", module="atelier")
    log.add("AtelierDesk", "team_unknown", "Group '=X' matches no team.", params=["=X"], source_rows="3")
    path = write_report(log, tmp_path / "r.xlsx", header={"Environment": "local"})
    sheet = load_workbook(path)["Issues"]
    assert [cell.value for cell in sheet[2]][:3] == ["MT-local-0001", "error", "data"]
    # A value that looks like a formula stays text.
    assert sheet.cell(row=2, column=13).value == "Group '=X' matches no team."
    assert load_workbook(path).sheetnames == ["Issues", "Summary", "Timings"]


# --- A full run against the app ----------------------------------------------------------


def _bridge(client: TestClient) -> httpx.MockTransport:
    """An httpx transport that sends the runner's requests to the TestClient
    (its own cookie jar is cleared: the runner's client keeps the session)."""

    def handle(request: httpx.Request) -> httpx.Response:
        client.cookies.clear()
        headers = {key: value for key, value in request.headers.items() if key.lower() not in ("host", "content-length")}
        response = client.request(request.method, request.url.raw_path.decode(), content=request.content, headers=headers)
        return httpx.Response(response.status_code, headers=response.headers.multi_items(), content=response.content)

    return httpx.MockTransport(handle)


@pytest.fixture()
def loader(as_atelier: TestClient, db_session: Session, world: dict, desk: dict) -> dict:
    """The Atelier user becomes the mass-test account: super admin, with
    MasterData access and Teams view; RW terras also goes by '123 Rotte pataten'."""
    sync_masterdata_screens(db_session)
    masterdata = Module(key="module-9", name="MasterData", sort_order=9)
    db_session.add(masterdata)
    db_session.flush()
    user = db_session.scalar(select(User).where(User.email == "atelier@example.com"))
    user.is_super_admin = True
    db_session.add(UserModuleAccess(user_id=user.id, module_id=masterdata.id))
    role = MasterDataRole(name="Teams lezen")
    db_session.add(role)
    db_session.flush()
    screen = db_session.scalar(select(MasterDataScreen).where(MasterDataScreen.key == "masterdata.teams"))
    db_session.add(MasterDataRolePermission(role_id=role.id, screen_id=screen.id, can_view=True))
    db_session.add(MasterDataUserRole(user_id=user.id, role_id=role.id))
    db_session.add(TeamAlias(team_id=world["terras"].id, alias="123 Rotte pataten", alias_key=normalize_name("123 Rotte pataten")))
    db_session.commit()
    return desk


def _load_workbook(tmp_path: Path) -> Path:
    """Last year's list as the desk fixture's world knows it, with one row per
    kind of problem; converted into the load workbook."""
    source = _source(tmp_path / "uitgifte.xlsx", [
        # Jan picks up a T-shirt and an apron (by alias, odd spacing) and brings the T-shirt back.
        _line("2026-07-03 10:00:00", "123 rotte  pataten", "Jan Peeters", 1, "T-shirt", "man M"),
        _line("2026-07-03 10:00:00", "123 rotte  pataten", "Jan Peeters", 1, "Schort", "unisex OneSize"),
        _line("2026-07-03 13:00:00", "RW terras", "Jan Peeters", -1, "T-shirt", "man M"),
        # Returned once more than picked up.
        _line("2026-07-03 14:00:00", "RW terras", "Jan Peeters", -1, "T-shirt", "man M"),
        # Two pieces in one row.
        _line("2026-07-03 11:00:00", "RW terras", "An Smets", 2, "T-shirt", "man M"),
        # Unknown team, article, size; no festival that day.
        _line("2026-07-03 12:00:00", "Onbekende ploeg", "Piet Pieters", 1, "T-shirt", "man M"),
        _line("2026-07-03 12:30:00", "RW terras", "Tom Tas", 1, "Sokken", "man M"),
        _line("2026-07-03 12:40:00", "RW terras", "Tom Tas", 1, "T-shirt", "vrouw XS"),
        _line("2026-08-01 09:00:00", "RW terras", "Tom Tas", 1, "T-shirt", "man M"),
        # Refused by the desk: not in the package / no stock.
        _line("2026-07-03 15:00:00", "RW terras", "Lies Claes", 1, "Pet", "unisex OneSize"),
        _line("2026-07-03 16:00:00", "RW terras", "Lies Claes", 1, "T-shirt", "man L"),
    ])
    log = IssueLog("convert")
    return write_sheets(tmp_path / "load.xlsx", convert_atelier_desk(source, log))


def test_full_run_loads_logs_and_never_duplicates(
    client: TestClient, db_session: Session, loader: dict, tmp_path: Path, sent: list[OutgoingMail]
) -> None:
    env = Environment("local", "http://testserver", "http://testserver")
    load = _load_workbook(tmp_path)
    out = tmp_path / "out"

    # A dry run looks everything up but writes nothing.
    report, log = run(env, load, out, "atelier@example.com", "password123", dry_run=True, transport=_bridge(client))
    assert db_session.scalar(select(func.count()).select_from(AtelierHandout)) == 0
    assert Ledger(out / "local" / "ledger.json").dry_run_today()
    assert report.name.endswith("-dry-run-issues.xlsx")

    report, log = run(env, load, out, "atelier@example.com", "password123", transport=_bridge(client))
    codes = sorted(issue.code for issue in log.issues if issue.category != "performance")
    assert codes == sorted([
        "return_not_open", "quantity_not_one", "team_unknown", "article_unknown", "size_unknown",
        "festival_not_found", "not_in_package", "insufficient_stock",
    ])
    summary = log.summaries[ATELIER_DESK]
    assert summary.loaded == 2  # Jan's pick-up and his first return
    refused = next(issue for issue in log.issues if issue.code == "not_in_package")
    assert (refused.http_status, refused.text) == (400, "Pet zit niet in het pakket van deze ploeg.")
    assert "Add article Pet to the package of team RW terras" in refused.solution
    assert refused.source_values.startswith("datum=2026-07-03 15:00:00")

    # The pick-up keeps its real moment (10:00 Belgian = 08:00 UTC) and nobody got a mail.
    handout = db_session.scalar(select(AtelierHandout))
    created = handout.created_at.replace(tzinfo=timezone.utc) if handout.created_at.tzinfo is None else handout.created_at
    assert created == datetime(2026, 7, 3, 8, 0, tzinfo=timezone.utc)
    assert sent == []
    assert load_workbook(report)["Issues"].max_row == len(log.issues) + 1

    # A second run loads nothing again; the refused rows are refused again.
    _report, again = run(env, load, out, "atelier@example.com", "password123", transport=_bridge(client))
    assert db_session.scalar(select(func.count()).select_from(AtelierHandout)) == 1
    assert again.summaries[ATELIER_DESK].loaded == 0
    assert again.summaries[ATELIER_DESK].skipped_ledger == 2


def test_run_stops_before_writing_without_the_rights(
    client: TestClient, db_session: Session, loader: dict, tmp_path: Path
) -> None:
    user = db_session.scalar(select(User).where(User.email == "atelier@example.com"))
    user.is_super_admin = False
    db_session.commit()
    env = Environment("local", "http://testserver", "http://testserver")
    _report, log = run(env, _load_workbook(tmp_path), tmp_path / "out", "atelier@example.com", "password123",
                       transport=_bridge(client))
    assert [issue.code for issue in log.issues] == ["not_super_admin"]
    assert log.has_blocker
    assert db_session.scalar(select(func.count()).select_from(AtelierHandout)) == 0

    _report, log = run(env, _load_workbook(tmp_path), tmp_path / "out", "atelier@example.com", "wrong",
                       transport=_bridge(client))
    assert [issue.code for issue in log.issues] == ["login_failed"]
