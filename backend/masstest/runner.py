# One mass-test run on one environment: log in, preflight every step that has
# a sheet in the load workbook (nothing is written when any step is blocked),
# run the steps in order, add the slow endpoints and write the report.

from datetime import datetime
from pathlib import Path

import httpx

from masstest.client import SLOW_CALL_SECONDS, ApiClient
from masstest.environments import Environment
from masstest.ledger import Ledger
from masstest.load_workbook import read_sheet
from masstest.report import BLOCKER, PERFORMANCE, IssueLog, report_path, write_report
from masstest.steps import STEPS

RUN = "run"


def run(
    env: Environment,
    load_path: Path,
    out_dir: Path,
    email: str,
    password: str,
    *,
    dry_run: bool = False,
    only: list[str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> tuple[Path, IssueLog]:
    """Run the load workbook against `env`; gives the report's path and the log."""
    started = datetime.now()
    log = IssueLog(env.key)
    ledger = Ledger(out_dir / env.key / "ledger.json")
    client = ApiClient(env.api_url, transport=transport)
    try:
        _run_steps(client, log, ledger, load_path, email, password, dry_run, only)
    finally:
        client.close()

    # Endpoints that were slow at least once: one performance issue each
    # (not the login: password hashing is slow on purpose).
    for endpoint, durations in sorted(client.timing.calls.items()):
        if endpoint.startswith("POST /api/auth/"):
            continue
        slow = [seconds for seconds in durations if seconds > SLOW_CALL_SECONDS]
        if slow:
            log.add(RUN, "slow_call", f"{len(slow)} of {len(durations)} call(s) to {endpoint} took longer than "
                    f"{SLOW_CALL_SECONDS:g} s (slowest {max(slow):.2f} s).", severity=PERFORMANCE,
                    params=[endpoint, f"{max(slow):.2f}", f"{SLOW_CALL_SECONDS:g}"], request=endpoint)
    if dry_run and not log.has_blocker:
        ledger.mark_dry_run()

    header = {
        "Environment": f"{env.key} ({env.api_url})",
        "Load workbook": load_path.name,
        "Mode": "dry run (nothing written)" if dry_run else "load",
        "Account": email,
        "Started": started.strftime("%Y-%m-%d %H:%M:%S"),
        "Finished": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Issues": str(len(log.issues)),
    }
    path = write_report(log, report_path(out_dir, env.key, "dry-run-issues" if dry_run else "issues"), client.timing, header)
    return path, log


def _run_steps(
    client: ApiClient,
    log: IssueLog,
    ledger: Ledger,
    load_path: Path,
    email: str,
    password: str,
    dry_run: bool,
    only: list[str] | None,
) -> None:
    """Log in, preflight every step with rows, then run them (unless blocked)."""
    login = client.login(email, password)
    if not login.ok:
        code = "network" if login.status == 0 else "login_failed"
        log.add(RUN, code, f"Logging in as {email} failed ({login.status}).", severity=BLOCKER,
                params=[str(login.body)[:200]], request="POST /api/auth/login", http_status=login.status)
        return

    work = []
    for step_class in STEPS:
        if only and step_class.sheet not in only:
            continue
        rows = read_sheet(load_path, step_class.sheet)
        if rows is None:
            continue
        work.append((step_class(), rows))
    if not work:
        log.add(RUN, "column_missing", f"The load workbook has no sheet the runner knows "
                f"({', '.join(step.sheet for step in STEPS)}).", severity=BLOCKER, params=["sheet"])
        return

    # Every preflight first, so a missing right or setting stops the run before any write.
    ready = [step.preflight(client, log) for step, _rows in work]
    if not all(ready):
        return
    for step, rows in work:
        step.run(client, rows, ledger, log, dry_run)
