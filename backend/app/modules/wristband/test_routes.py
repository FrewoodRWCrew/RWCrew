# The Test-scan endpoints, added to the routers of every module that offers the
# screen (Scans, Atelier, Walkies) with register_scan_test_routes — the same
# idea as app/help/routes.py. Each module passes its own right, so a test
# can be triggered from any of them with that module's roles; the message
# goes through exactly the same processing as the wristband company's webhook,
# without its token, marked as a test.

from collections.abc import Callable

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.wristband_scan import WristbandScan
from app.db.models.wristband_scanner import WristbandScanner
from app.modules.wristband.scan_service import TEST, process_message
from app.modules.wristband.visibility import counter_rules, visible_at
from app.schemas.wristband import (
    ScanLogEntry,
    ScannerResponse,
    ScanResponse,
    TeamSummaryResponse,
    TestScanRequest,
    TestScanResponse,
)


def scan_log_entries(db: Session, scans: list[WristbandScan]) -> list[ScanLogEntry]:
    """Scans for a log: the row plus the counters where each one waits."""
    rules = counter_rules(db)
    return [
        ScanLogEntry.model_validate(scan, from_attributes=True).model_copy(update={"visible_at": visible_at(scan, rules)})
        for scan in scans
    ]


def register_scan_test_routes(router: APIRouter, *, require_view: Callable, require_send: Callable) -> None:
    """Add /wristband-test/{scanners,teams,log,send} to a module's router."""

    @router.get("/wristband-test/scanners", response_model=list[ScannerResponse])
    def list_test_scanners(db: Session = Depends(get_db), _user: User = Depends(require_view)) -> list[WristbandScanner]:
        """Every scanner that ever sent a message (the form's "existing scanner")."""
        return list(db.scalars(select(WristbandScanner).order_by(WristbandScanner.device_id)).all())

    @router.get("/wristband-test/teams", response_model=list[TeamSummaryResponse])
    def list_test_teams(db: Session = Depends(get_db), _user: User = Depends(require_view)) -> list[Team]:
        """The MasterData teams, for the Test-scan form's team dropdown."""
        return list(db.scalars(select(Team).where(Team.active.is_(True)).order_by(Team.name)).all())

    @router.get("/wristband-test/log", response_model=list[ScanLogEntry])
    def list_test_log(
        limit: int = Query(default=200, ge=1, le=1000),
        db: Session = Depends(get_db),
        _user: User = Depends(require_view),
    ) -> list[ScanLogEntry]:
        """The latest received messages (all statuses), newest first, with the raw message."""
        scans = db.scalars(select(WristbandScan).order_by(WristbandScan.id.desc()).limit(limit)).all()
        return scan_log_entries(db, list(scans))

    @router.post("/wristband-test/send", response_model=TestScanResponse)
    def send_test_scan(
        payload: TestScanRequest,
        db: Session = Depends(get_db),
        _user: User = Depends(require_send),
    ) -> TestScanResponse:
        """Send a message through the webhook's processing (no token check),
        marked as a test; it appears live on the counters where the team has
        reservations."""
        result = process_message(db, payload.raw, source=TEST, check_token=None)
        db.commit()
        team = db.get(Team, result.scan.team_id) if result.scan.team_id else None
        return TestScanResponse(
            scan=ScanResponse.model_validate(result.scan),
            http_status=result.http_status,
            team_name_matched=team.name if team else None,
            visible_at=visible_at(result.scan, counter_rules(db)),
        )
