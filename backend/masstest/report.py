# The mass test's issue log: one line per problem (with a description and a
# proposed solution), a summary per step and the timings per endpoint,
# written as an Excel file per run.

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from masstest.client import Timing
from masstest.solutions import propose

BLOCKER = "blocker"
ERROR = "error"
WARNING = "warning"
PERFORMANCE = "performance"

# Issues sheet: column title and width.
COLUMNS = [
    ("ID", 14), ("Severity", 11), ("Category", 12), ("Module", 10), ("Step", 14), ("Source file", 22),
    ("Source rows", 11), ("Source values", 50), ("Request", 34), ("HTTP", 6), ("Error code", 22),
    ("Text (as on screen)", 45), ("Description", 60), ("Proposed solution", 60), ("Analysis (review)", 50),
    ("Status", 9),
]
SEVERITY_FILL = {
    BLOCKER: "F8B4B4", ERROR: "FCD9B6", WARNING: "FFF2B3", PERFORMANCE: "D6E4FF",
}


@dataclass
class Issue:
    """One problem the run met."""

    id: str
    severity: str
    category: str
    module: str
    step: str
    description: str
    solution: str
    code: str = ""
    text: str = ""
    source_file: str = ""
    source_rows: str = ""
    source_values: str = ""
    request: str = ""
    http_status: int | None = None
    analysis: str = ""
    status: str = "open"


@dataclass
class StepSummary:
    """The counts of one step (transactions loaded, skipped, in error)."""

    step: str
    total: int = 0
    loaded: int = 0
    skipped_ledger: int = 0
    errors: int = 0
    checked: int = 0


@dataclass
class IssueLog:
    """Every issue of one run, numbered MT-<env>-<n>."""

    env: str
    module: str = ""
    issues: list[Issue] = field(default_factory=list)
    summaries: dict[str, StepSummary] = field(default_factory=dict)

    def add(
        self,
        step: str,
        code: str,
        description: str,
        *,
        severity: str = ERROR,
        params: list[str] | None = None,
        context: dict | None = None,
        **extra: object,
    ) -> Issue:
        """Log an issue; its category and proposed solution come from the
        code's rule (solutions.py)."""
        rule = propose(code, params, context)
        issue = Issue(
            id=f"MT-{self.env}-{len(self.issues) + 1:04d}",
            severity=severity,
            category=rule.category,
            module=str(extra.pop("module", self.module)),
            step=step,
            description=description,
            solution=rule.solution,
            code=code,
            **extra,
        )
        self.issues.append(issue)
        return issue

    def summary(self, step: str) -> StepSummary:
        """The (new or existing) counts of a step."""
        return self.summaries.setdefault(step, StepSummary(step))

    @property
    def has_blocker(self) -> bool:
        return any(issue.severity == BLOCKER for issue in self.issues)


def _sheet(workbook: Workbook, title: str, headers: list[tuple[str, int]], rows: list[list[object]], first: bool = False):
    """A sheet with a bold, frozen, filterable header row and wrapped text."""
    sheet = workbook.active if first else workbook.create_sheet()
    sheet.title = title
    sheet.append([name for name, _width in headers])
    for row in rows:
        sheet.append(row)
    for index, (_name, width) in enumerate(headers, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
        sheet.cell(row=1, column=index).font = Font(bold=True)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    return sheet


def _text(value: object) -> object:
    """A value that looks like a formula stays text in Excel."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def write_report(log: IssueLog, path: Path, timing: Timing | None = None, header: dict[str, str] | None = None) -> Path:
    """Write the run's report: Issues, Summary and Timings sheets."""
    workbook = Workbook()
    rows = [
        [_text(value) for value in (
            issue.id, issue.severity, issue.category, issue.module, issue.step, issue.source_file, issue.source_rows,
            issue.source_values, issue.request, issue.http_status, issue.code, issue.text, issue.description,
            issue.solution, issue.analysis, issue.status,
        )]
        for issue in log.issues
    ]
    issues = _sheet(workbook, "Issues", COLUMNS, rows, first=True)
    # Colour the severity cell so blockers stand out.
    for row_index, issue in enumerate(log.issues, start=2):
        colour = SEVERITY_FILL.get(issue.severity)
        if colour:
            issues.cell(row=row_index, column=2).fill = PatternFill("solid", fgColor=colour)

    # Summary: the run's settings, then the counts per step and per category.
    summary_rows: list[list[object]] = [[key, value] for key, value in (header or {}).items()]
    summary_rows.append(["", ""])
    summary_rows.append(["Step", "Transactions / loaded / skipped (ledger) / checked (dry run) / with an error"])
    for step in log.summaries.values():
        summary_rows.append([step.step, f"{step.total} / {step.loaded} / {step.skipped_ledger} / {step.checked} / {step.errors}"])
    summary_rows.append(["", ""])
    for category in sorted({issue.category for issue in log.issues}):
        summary_rows.append([f"Issues: {category}", sum(1 for issue in log.issues if issue.category == category)])
    _sheet(workbook, "Summary", [("Item", 34), ("Value", 80)], summary_rows)

    # Timings per endpoint.
    timing_rows = [
        [endpoint, len(durations), round(sum(durations), 2), round(sum(durations) / len(durations), 3), round(max(durations), 3)]
        for endpoint, durations in sorted((timing.calls if timing else {}).items())
    ]
    _sheet(workbook, "Timings", [("Endpoint", 50), ("Calls", 8), ("Total s", 10), ("Average s", 10), ("Max s", 10)], timing_rows)

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return path


def report_path(out_dir: Path, env: str, kind: str = "issues") -> Path:
    """<out>/<env>/<YYYYmmdd-HHMMSS>-<kind>.xlsx (local time of the PC)."""
    return out_dir / env / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{kind}.xlsx"
