# The mass test's command line (run from backend/ with the backend venv):
#
#   .venv/Scripts/python -m masstest convert <old list.xlsx> --kind atelier-desk --out <folder>/load.xlsx
#   .venv/Scripts/python -m masstest run --env local --load <folder>/load.xlsx --out <folder> [--dry-run]
#   .venv/Scripts/python -m masstest screens <folder>/<env>/<…>-screens.json --env local --out <folder>
#
# The account: --email (or MASSTEST_EMAIL); the password is asked, or read
# from MASSTEST_PASSWORD, and never stored. Output folders must lie outside
# the repo (the lists hold personal data). Production needs
# --confirm-production, a dry run on production the same day and a typed
# confirmation that a database dump was made.

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from masstest.convert import CONVERTERS
from masstest.environments import ENVIRONMENTS
from masstest.ledger import Ledger
from masstest.load_workbook import write_sheets
from masstest.report import BLOCKER, ERROR, IssueLog, report_path, write_report
from masstest.runner import run

REPO_ROOT = Path(__file__).resolve().parents[2]


def _outside_repo(path: Path) -> Path:
    """Refuse a path inside the repo: reports and load workbooks hold personal data."""
    resolved = path.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        sys.exit(f"{path} lies inside the repo; choose a folder outside it (personal data must not end up in git).")
    return resolved


def _convert(args: argparse.Namespace) -> None:
    """Old list → load workbook (+ a report of the rows that couldn't be read)."""
    out = _outside_repo(Path(args.out))
    log = IssueLog("convert", module=args.kind)
    sheets = CONVERTERS[args.kind](Path(args.source), log)
    write_sheets(out, sheets)
    for name, (_columns, rows) in sheets.items():
        print(f"{name}: {len(rows)} row(s), {len({row.get('transaction') for row in rows})} transaction(s) -> {out}")
    if log.issues:
        path = write_report(log, out.with_name(f"{out.stem}-convert-issues.xlsx"), header={"Source": Path(args.source).name})
        print(f"{len(log.issues)} row problem(s): {path}")


def _confirm_production(args: argparse.Namespace, out_dir: Path) -> None:
    """Production: explicit flag, a dry run there today, and a typed confirmation."""
    if not args.confirm_production:
        sys.exit("Production needs --confirm-production.")
    if args.dry_run:
        return
    if not Ledger(out_dir / "prod" / "ledger.json").dry_run_today():
        sys.exit("Do a dry run on production first today (--dry-run).")
    try:
        dump = input("Was a database dump of production made just now? Type 'yes': ").strip().lower()
        sure = input("Type PRODUCTION to load the data into production: ").strip()
    except EOFError:
        sys.exit("Production needs an interactive confirmation.")
    if dump != "yes" or sure != "PRODUCTION":
        sys.exit("Not confirmed; nothing was sent.")


def _run(args: argparse.Namespace) -> None:
    """Send the load workbook to one environment and write the report."""
    env = ENVIRONMENTS[args.env]
    out_dir = _outside_repo(Path(args.out))
    if env.is_production:
        _confirm_production(args, out_dir)
    email = args.email or os.environ.get("MASSTEST_EMAIL") or input("Email: ").strip()
    password = os.environ.get("MASSTEST_PASSWORD") or getpass.getpass(f"Password for {email} on {env.key}: ")
    path, log = run(env, Path(args.load), out_dir, email, password, dry_run=args.dry_run, only=args.only)
    for summary in log.summaries.values():
        print(f"{summary.step}: {summary.total} transaction(s), loaded {summary.loaded}, skipped (ledger) "
              f"{summary.skipped_ledger}, checked {summary.checked}, with an error {summary.errors}")
    counts: dict[str, int] = {}
    for issue in log.issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    print(f"Issues: {counts or 'none'} -> {path}")
    if log.has_blocker:
        sys.exit(2)


def _screens(args: argparse.Namespace) -> None:
    """The screen check's JSON (scripts/mass-test-screens.mjs) → an issue report."""
    findings = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    log = IssueLog(args.env, module="screens")
    for finding in findings.get("issues", []):
        log.add(
            "screens",
            finding["code"],
            finding["description"],
            severity=ERROR if finding["code"] == "screen_error" else "performance",
            params=[str(value) for value in finding.get("params", [])],
            module=finding.get("module", ""),
            request=finding.get("url", ""),
            text=finding.get("text", ""),
        )
    if findings.get("blocker"):
        log.add("screens", "login_failed", findings["blocker"], severity=BLOCKER)
    out_dir = _outside_repo(Path(args.out))
    header = {"Environment": args.env, "Screens checked": str(findings.get("checked", 0)), "Source": Path(args.findings).name}
    path = write_report(log, report_path(out_dir, args.env, "screens-issues"), header=header)
    print(f"{len(log.issues)} screen issue(s) -> {path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="masstest", description="Load last year's lists and log every issue.")
    commands = parser.add_subparsers(dest="command", required=True)

    convert = commands.add_parser("convert", help="old list → load workbook")
    convert.add_argument("source")
    convert.add_argument("--kind", choices=sorted(CONVERTERS), required=True)
    convert.add_argument("--out", required=True, help="the load workbook to write (.xlsx, outside the repo)")
    convert.set_defaults(handler=_convert)

    run_parser = commands.add_parser("run", help="send a load workbook to an environment")
    run_parser.add_argument("--env", choices=sorted(ENVIRONMENTS), required=True)
    run_parser.add_argument("--load", required=True)
    run_parser.add_argument("--out", required=True, help="folder for the ledger and reports (outside the repo)")
    run_parser.add_argument("--email")
    run_parser.add_argument("--dry-run", action="store_true", help="look everything up, write nothing")
    run_parser.add_argument("--only", nargs="*", help="only these sheets (e.g. AtelierDesk)")
    run_parser.add_argument("--confirm-production", action="store_true")
    run_parser.set_defaults(handler=_run)

    screens = commands.add_parser("screens", help="screen-check JSON → issue report")
    screens.add_argument("findings")
    screens.add_argument("--env", choices=sorted(ENVIRONMENTS), required=True)
    screens.add_argument("--out", required=True)
    screens.set_defaults(handler=_screens)

    args = parser.parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
