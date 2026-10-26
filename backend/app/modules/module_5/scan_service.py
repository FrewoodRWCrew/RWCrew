# Atelier's wristband scans (block 5). When a worker scans their wristband
# at the Atelier counter, the wristband company posts a JSON message to our
# webhook (scan_webhook_router.py); the Test-scan screen sends the same kind
# of message (until the real connection exists, from May 2027). Both go
# through process_message() here, which logs EVERY message in Atelier_scan
# — refused and ignored ones too, so the settings screen shows what really
# arrives — registers the scanner (data.device.id) and matches the team.
# The desk screen of that scanner then picks the "new" scan up and fills in
# the person. The only writer of Atelier_scan and Atelier_scanner (apart
# from a scanner's label on the settings screen). Never commits.
#
# The message (example from the wristband company):
#   {"data": {"attending_group": {"id": "25029", "name": "YFU Vlaanderen"},
#             "device": {"id": 14734, "name": "SUN0410", "uuid": "..."},
#             "id": "557087",                       <- the wristband number
#             "person": {"first_name": "Anaïs", "last_name": "Wydaeghe"},
#             "profile": {"id": "1076", "name": "Vrijwilliger The Hive"}},
#    "event": "crew_participation",
#    "token": "..."}                                <- the shared secret
# Optional extras, if they ever come: data.person.email (or data.email) and
# data.person.size (or data.size), e.g. "M".

import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.atelier_scan import AtelierScan
from app.db.models.atelier_scanner import AtelierScanner
from app.db.models.team import Team

# The only event the counter acts on.
CREW_PARTICIPATION = "crew_participation"

# Scan statuses.
NEW = "new"
USED = "used"
DISMISSED = "dismissed"
IGNORED = "ignored"
REFUSED = "refused"

# Sources.
WEBHOOK = "webhook"
TEST = "test"

# How long a new scan waits on the desk screen.
DESK_WINDOW = timedelta(minutes=15)


@dataclass
class ProcessResult:
    """What happened to a message, for the webhook's HTTP answer and the Test-scan screen."""

    scan: AtelierScan
    # HTTP status for the webhook (200 accepted/ignored, 400 unreadable, 401 bad token).
    http_status: int


def _text(value: object, limit: int) -> str | None:
    """A field as trimmed text (numbers too), None when empty."""
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text[:limit] or None


def _get(data: dict, *path: str) -> object:
    """data[path[0]][path[1]]..., None when any step is missing."""
    current: object = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def match_team(db: Session, name: str | None) -> Team | None:
    """Our MasterData team with this name, ignoring case and extra spaces."""
    if not name:
        return None
    wanted = " ".join(name.lower().split())
    team = db.scalar(select(Team).where(func.lower(Team.name) == wanted).limit(1))
    if team is not None:
        return team
    # Extra spaces inside the stored name: compare normalized in Python.
    return next(
        (team for team in db.scalars(select(Team)).all() if " ".join(team.name.lower().split()) == wanted),
        None,
    )


def _register_scanner(db: Session, device_id: str, device_name: str | None) -> AtelierScanner:
    """The scanner of this device, created on its first message; its name and
    "last seen" are kept up to date."""
    scanner = db.scalar(select(AtelierScanner).where(AtelierScanner.device_id == device_id))
    if scanner is None:
        scanner = AtelierScanner(device_id=device_id)
        db.add(scanner)
    if device_name:
        scanner.device_name = device_name
    scanner.last_seen_at = datetime.now(timezone.utc)
    db.flush()
    return scanner


def process_message(db: Session, raw: str, *, source: str, expected_token: str | None) -> ProcessResult:
    """Log one message and, when it's a valid crew scan, make it a "new" scan
    for its scanner. `expected_token` is checked for the webhook (an empty
    configured token refuses everything); None (the Test-scan screen) skips it."""
    scan = AtelierScan(source=source, status=REFUSED, raw=raw[:100_000], received_at=datetime.now(timezone.utc))
    db.add(scan)

    try:
        message = json.loads(raw)
    except ValueError:
        message = None
    if not isinstance(message, dict):
        scan.status_detail = "unreadable"
        db.flush()
        return ProcessResult(scan, 400)

    data = message.get("data") if isinstance(message.get("data"), dict) else {}
    scan.event = _text(message.get("event"), 100)
    scan.device_id = _text(_get(data, "device", "id"), 100)
    scan.device_name = _text(_get(data, "device", "name"), 255)
    scan.wristband_number = _text(data.get("id"), 100)
    scan.first_name = _text(_get(data, "person", "first_name"), 255)
    scan.last_name = _text(_get(data, "person", "last_name"), 255)
    scan.team_name = _text(_get(data, "attending_group", "name"), 255)
    scan.profile_name = _text(_get(data, "profile", "name"), 255)
    scan.email = _text(_get(data, "person", "email") or data.get("email"), 255)
    scan.size = _text(_get(data, "person", "size") or data.get("size"), 50)

    # The token: compared in constant time; no configured token = nothing is accepted.
    if expected_token is not None:
        token = _text(message.get("token"), 500) or ""
        if not expected_token or not hmac.compare_digest(token, expected_token):
            scan.status_detail = "bad_token"
            db.flush()
            return ProcessResult(scan, 401)

    if scan.event != CREW_PARTICIPATION:
        scan.status = IGNORED
        scan.status_detail = "other_event"
        db.flush()
        return ProcessResult(scan, 200)
    if not scan.device_id or not scan.first_name or not scan.last_name:
        scan.status_detail = "missing_fields"
        db.flush()
        return ProcessResult(scan, 400)

    _register_scanner(db, scan.device_id, scan.device_name)
    team = match_team(db, scan.team_name)
    scan.team_id = team.id if team else None
    scan.status = NEW
    db.flush()
    return ProcessResult(scan, 200)


def waiting_scans(db: Session, device_id: str | None) -> list[AtelierScan]:
    """The "new" scans of a scanner (None = of every scanner) from the last
    DESK_WINDOW, newest first."""
    since = datetime.now(timezone.utc) - DESK_WINDOW
    query = select(AtelierScan).where(AtelierScan.status == NEW, AtelierScan.received_at >= since)
    if device_id is not None:
        query = query.where(AtelierScan.device_id == device_id)
    return list(db.scalars(query.order_by(AtelierScan.id.desc())).all())


def mark_used(db: Session, scan: AtelierScan, person_id: int) -> None:
    """A desk transaction used the scan (for this person)."""
    scan.status = USED
    scan.used_at = datetime.now(timezone.utc)
    scan.person_id = person_id
    db.flush()


def dismiss(scan: AtelierScan) -> None:
    """The desk dismissed the scan ("Negeren")."""
    if scan.status == NEW:
        scan.status = DISMISSED
