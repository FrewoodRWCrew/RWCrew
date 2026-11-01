# The Excel downloads of Atelier's "Balie" lists: Openstaand and Retourproblemen.
# Gets the rows the screens show and turns them into a workbook with
# build_xlsx, with headers and fit names in the user's language. Like the
# screens, neither file has an email column (GDPR).

from datetime import date, datetime

from app.core.timezone import to_belgian
from app.modules.module_9.xlsx_common import build_xlsx
from app.schemas.atelier import HandoutResponse, ReturnIssueResponse

_OPEN_HEADERS = {
    "nl": ["Ploeg", "Persoon", "Polsband", "Dag", "Artikel", "Maat", "Pasvorm", "Opgehaald"],
    "en": ["Team", "Person", "Wristband", "Day", "Article", "Size", "Fit", "Picked up"],
}
_ISSUE_HEADERS = {
    "nl": ["Retourstatus", "Artikel", "Maat", "Pasvorm", "Ploeg", "Persoon", "Polsband", "Dag", "Teruggebracht", "Geboekt door"],
    "en": ["Return status", "Article", "Size", "Fit", "Team", "Person", "Wristband", "Day", "Returned", "Booked by"],
}
_FITS = {
    "nl": {"women": "Dames", "men": "Heren", "unisex": "Unisex"},
    "en": {"women": "Women", "men": "Men", "unisex": "Unisex"},
}


def _language(locale: str) -> str:
    """The file's language: English on request, else Dutch (the default)."""
    return "en" if locale == "en" else "nl"


def _text(value: str | None) -> str | None:
    """Text as Excel must show it: names can come from the public wristband
    webhook, and a value starting like a formula must not be run as one."""
    if value and value[0] in "=+-@":
        return f"'{value}"
    return value


def _day(value: date) -> str:
    """A date as the screens show it."""
    return value.strftime("%d-%m-%Y")


def _moment(value: datetime) -> str:
    """A moment in Belgian time, as the screens show it."""
    return to_belgian(value).strftime("%d-%m-%Y %H:%M")


def open_pieces_xlsx(handouts: list[HandoutResponse], line_ids: set[int], locale: str) -> bytes:
    """Openstaand: one row per piece, sorted by team, person, day and article
    like the screen. Only the pieces in `line_ids` (what the screen shows)."""
    language = _language(locale)
    pieces = [(handout, line) for handout in handouts for line in handout.lines if line.id in line_ids]
    pieces.sort(key=lambda piece: (piece[0].team_name, piece[0].person_name, piece[0].day, piece[1].article_name))
    rows = [
        [
            _text(handout.team_name),
            _text(handout.person_name),
            _text(handout.bracelet_number),
            _day(handout.day),
            _text(line.article_name),
            _text(line.size_name),
            _FITS[language][line.fit],
            _moment(handout.created_at),
        ]
        for handout, line in pieces
    ]
    return build_xlsx("Openstaand" if language == "nl" else "Outstanding", _OPEN_HEADERS[language], rows)


def return_issues_xlsx(issues: list[ReturnIssueResponse], line_ids: set[int], locale: str) -> bytes:
    """Retourproblemen: one row per piece, in the screen's order (newest
    first). Only the pieces in `line_ids` (what the screen shows)."""
    language = _language(locale)
    rows = [
        [
            _text(issue.status_name),
            _text(issue.article_name),
            _text(issue.size_name),
            _FITS[language][issue.fit],
            _text(issue.team_name),
            _text(issue.person_name),
            _text(issue.bracelet_number),
            _day(issue.day),
            _moment(issue.returned_at),
            _text(issue.returned_by_name),
        ]
        for issue in issues
        if issue.line_id in line_ids
    ]
    return build_xlsx("Retourproblemen" if language == "nl" else "Return issues", _ISSUE_HEADERS[language], rows)
