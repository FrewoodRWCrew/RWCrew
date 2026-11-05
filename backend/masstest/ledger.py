# The ledger of one environment: which transactions of the load workbook were
# already loaded there (so a second run skips them: no duplicates), and on
# which days a dry run was done (production needs one the same day).

import hashlib
import json
from datetime import date, datetime
from pathlib import Path


def transaction_key(step: str, source_file: str, rows: list[dict]) -> str:
    """A stable key for one transaction: its step, source file and the
    values of its rows (the source row numbers are left out, so inserting a
    line above it in the source doesn't load it twice)."""
    payload = json.dumps(
        [step, Path(source_file).name, [{k: v for k, v in row.items() if k != "source_row"} for row in rows]],
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


class Ledger:
    """<out>/<env>/ledger.json, saved after every change (a run that stops
    halfway keeps what it already loaded)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            self.data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}
        self.data.setdefault("done", {})
        self.data.setdefault("dry_runs", [])

    def is_done(self, key: str) -> bool:
        return key in self.data["done"]

    def mark_done(self, key: str, result: dict) -> None:
        """Remember a loaded transaction and what the API gave back."""
        self.data["done"][key] = {"at": datetime.now().isoformat(timespec="seconds"), **result}
        self._save()

    def mark_dry_run(self) -> None:
        today = date.today().isoformat()
        if today not in self.data["dry_runs"]:
            self.data["dry_runs"].append(today)
            self._save()

    def dry_run_today(self) -> bool:
        return date.today().isoformat() in self.data["dry_runs"]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
