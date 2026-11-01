# Wristband scans, shared by the modules with a counter (Atelier, later
# Walkies) and shown in the Scans module. When a worker scans their wristband
# the wristband company posts a JSON message to our webhook
# (webhook_router.py); the Test-scan screens send the same kind of message
# (until the real connection exists, from May 2027). Both go through
# process_message() here, which logs EVERY message in Wristband_scan —
# refused and ignored ones too, so the Scans module shows what really arrives
# — saves it as a .json file (json_files.py), registers the scanner
# (data.device.id) and matches the team. The desk screen of that scanner then
# picks the "new" scan up, when the team has reservations in that module (the
# module passes its own teams to waiting_scans), and fills in the person.
# The only writer of Wristband_scan and Wristband_scanner (apart from a
# scanner's label on the Scans module). Never commits.
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

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models.team import Team
from app.db.models.wristband_scan import WristbandScan
from app.db.models.wristband_scanner import WristbandScanner
from app.modules.module_9.team_alias_service import normalize_name, team_by_alias
from app.modules.wristband.json_files import save_message_file

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

# Refused before we know the sender: no file for these, so that anyone posting
# to the public webhook can't fill the disk (the table row is still logged).
NO_FILE_DETAILS = {"unreadable", "bad_token"}


@dataclass
class ProcessResult:
    """What happened to a message, for the webhook's HTTP answer and the Test-scan screen."""

    scan: WristbandScan
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
    """Our MasterData team with this name or alias, ignoring case and extra
    spaces. The name goes first."""
    if not name:
        return None
    wanted = normalize_name(name)
    team = db.scalar(select(Team).where(func.lower(Team.name) == wanted).limit(1))
    if team is not None:
        return team
    # Extra spaces inside the stored name: compare normalized in Python.
    team = next((team for team in db.scalars(select(Team)).all() if normalize_name(team.name) == wanted), None)
    return team or team_by_alias(db, name)


def _register_scanner(db: Session, device_id: str, device_name: str | None) -> WristbandScanner:
    """The scanner of this device, created on its first message; its name and
    "last seen" are kept up to date."""
    scanner = db.scalar(select(WristbandScanner).where(WristbandScanner.device_id == device_id))
    if scanner is None:
        scanner = WristbandScanner(device_id=device_id)
        db.add(scanner)
    if device_name:
        scanner.device_name = device_name
    scanner.last_seen_at = datetime.now(timezone.utc)
    db.flush()
    return scanner


def process_message(db: Session, raw: str, *, source: str, check_token: Callable[[str], bool] | None) -> ProcessResult:
    """Log one message, keep it as a .json file and, when it's a valid crew
    scan, make it a "new" scan for its scanner. `check_token` judges the
    message's token for the webhook (no token generated refuses everything);
    None (the Test-scan screens) skips it."""
    result = _process(db, raw, source=source, check_token=check_token)
    if result.scan.status_detail not in NO_FILE_DETAILS:
        save_message_file(result.scan)
    return result


def _process(db: Session, raw: str, *, source: str, check_token: Callable[[str], bool] | None) -> ProcessResult:
    """Read one message into a Wristband_scan row."""
    scan = WristbandScan(source=source, status=REFUSED, raw=raw[:100_000], received_at=datetime.now(timezone.utc))
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

    # The token (see webhook_token.py): without a generated one nothing is accepted.
    if check_token is not None and not check_token(_text(message.get("token"), 500) or ""):
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


def waiting_scans(db: Session, device_id: str | None, team_ids: set[int]) -> list[WristbandScan]:
    """The "new" scans of a scanner (None = of every scanner) from the last
    DESK_WINDOW that belong at this module's counter, newest first: those of
    `team_ids` (the teams with reservations there), plus scans whose team we
    couldn't match — we can't tell whose worker that is, and they mustn't get
    stuck at the counter."""
    since = datetime.now(timezone.utc) - DESK_WINDOW
    query = select(WristbandScan).where(
        WristbandScan.status == NEW,
        WristbandScan.received_at >= since,
        or_(WristbandScan.team_id.is_(None), WristbandScan.team_id.in_(team_ids)),
    )
    if device_id is not None:
        query = query.where(WristbandScan.device_id == device_id)
    return list(db.scalars(query.order_by(WristbandScan.id.desc())).all())


def mark_used(db: Session, scan: WristbandScan, person_id: int, module_key: str) -> None:
    """A desk transaction of this module used the scan (for this person). One
    status per scan: whichever counter uses it first wins."""
    scan.status = USED
    scan.used_at = datetime.now(timezone.utc)
    scan.used_by_module = module_key
    scan.person_id = person_id
    db.flush()


def dismiss(scan: WristbandScan) -> None:
    """The desk dismissed the scan ("Negeren")."""
    if scan.status == NEW:
        scan.status = DISMISSED
