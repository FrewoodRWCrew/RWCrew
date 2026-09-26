# Builds the printable "Ploegfiche" PDF of Altsien Select: everything that
# was chosen in the Ploeg Wizard for one team in one season, laid out as a
# friendly one-stop overview for the organisation — Altsien logo header,
# team info, a progress overview of every wizard step, the festivals with
# their delivery locations, and the special requests with their status.
#
# Uses fpdf2 (pure Python, see CLAUDE.md's Python 3.14 gotcha), the same
# library and conventions as module_3/intervention_request_pdf.py. The
# built-in Helvetica font only knows latin-1, so free text goes through
# _pdf_text() first (the same fallback as module_2/karblad_pdf.py).

from datetime import date, datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from app.schemas.altsien_select import TeamStateResponse

# Altsien Select's own fuchsia accent (fuchsia-600, see
# frontend/src/lib/module-theme.ts), used for the top band, the section
# bars and the rule under the header.
ACCENT_COLOR = (192, 38, 211)
TEXT_DARK = (31, 41, 55)
MUTED_TEXT = (107, 114, 128)
BORDER_COLOR = (223, 226, 230)
ZEBRA_FILL = (246, 247, 249)
DONE_GREEN = (22, 163, 74)

# The StatusColor palette (app/schemas/intervention_requests.py) as RGB —
# Tailwind's 600 shades, matching frontend/src/lib/status-colors.ts.
STATUS_RGB = {
    "red": (220, 38, 38),
    "orange": (234, 88, 12),
    "amber": (217, 119, 6),
    "green": (22, 163, 74),
    "teal": (13, 148, 136),
    "blue": (37, 99, 235),
    "indigo": (79, 70, 229),
    "purple": (147, 51, 234),
    "gray": (75, 85, 99),
}

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
ALTSIEN_LOGO = ASSETS_DIR / "altsien-logo.png"
# The logo's own width:height ratio (352 x 416 px).
ALTSIEN_LOGO_RATIO = 352 / 416

LABELS = {
    "nl": {
        "title": "Ploegfiche",
        "season": "Seizoen {season}",
        "season_closed": "afgesloten",
        "team_heading": "Ploeginfo",
        "team_name": "Ploeg",
        "location": "Locatie",
        "delivery_method": "Leveringswijze",
        "kernleden": "Altsien Kernleden",
        "description": "Omschrijving",
        "progress_heading": "Voortgang wizard",
        "step_done": "Afgerond op {date}{by}",
        "step_done_by": " door {name}",
        "step_todo": "Nog te doen",
        "festivals_heading": "Festivals & afleverlocaties",
        "festival": "Festival",
        "dates": "Periode",
        "afleverlocatie": "Afleverlocatie",
        "no_festivals": "Er zijn nog geen festivals gekozen.",
        "no_location": "Nog niet gekozen",
        "requests_heading": "Speciale aanvragen",
        "request": "Aanvraag",
        "status": "Status",
        "organisation_note": "Antwoord organisatie",
        "no_requests": "Er zijn geen speciale aanvragen.",
        "placeholder": "Deze gegevens worden later ingevuld via een aparte module.",
        "generated": "Gegenereerd op {date}",
        "page": "Pagina {page}/{pages}",
        "not_specified": "Niet opgegeven",
        "steps": {
            "festivals": "Festivals",
            "afleverlocaties": "Afleverlocaties",
            "products": "Producten",
            "special_requests": "Speciale aanvragen",
            "walkies": "Walkie-talkies",
        },
    },
    "en": {
        "title": "Team sheet",
        "season": "Season {season}",
        "season_closed": "closed",
        "team_heading": "Team info",
        "team_name": "Team",
        "location": "Location",
        "delivery_method": "Delivery method",
        "kernleden": "Altsien core members",
        "description": "Description",
        "progress_heading": "Wizard progress",
        "step_done": "Completed on {date}{by}",
        "step_done_by": " by {name}",
        "step_todo": "To do",
        "festivals_heading": "Festivals & delivery locations",
        "festival": "Festival",
        "dates": "Period",
        "afleverlocatie": "Delivery location",
        "no_festivals": "No festivals have been selected yet.",
        "no_location": "Not chosen yet",
        "requests_heading": "Special requests",
        "request": "Request",
        "status": "Status",
        "organisation_note": "Organisation's answer",
        "no_requests": "There are no special requests.",
        "placeholder": "This will be filled in later through a separate module.",
        "generated": "Generated on {date}",
        "page": "Page {page}/{pages}",
        "not_specified": "Not specified",
        "steps": {
            "festivals": "Festivals",
            "afleverlocaties": "Delivery locations",
            "products": "Products",
            "special_requests": "Special requests",
            "walkies": "Walkie-talkies",
        },
    },
}

# Typographic characters people often paste that latin-1 lacks, mapped to
# a close plain equivalent before the generic "?" replacement kicks in.
_TEXT_REPLACEMENTS = {
    "–": "-",
    "—": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "€": "EUR",
    "•": "-",
}


def _pdf_text(text: str | None) -> str:
    """Make free text safe for the built-in latin-1 PDF font."""
    if not text:
        return ""
    for character, replacement in _TEXT_REPLACEMENTS.items():
        text = text.replace(character, replacement)
    return text.encode("latin-1", "replace").decode("latin-1")


def _format_date(value: date | datetime) -> str:
    """dd-mm-yyyy, the app's established date format."""
    return value.strftime("%d-%m-%Y")


class _PloegfichePDF(FPDF):
    """A4 page with the "generated on / page x of y" footer on every page."""

    def __init__(self, labels: dict, generated_on: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.labels = labels
        self.generated_on = generated_on

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(*BORDER_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 2, self.w - self.r_margin, self.get_y() - 2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED_TEXT)
        self.cell(0, 6, self.labels["generated"].format(date=self.generated_on), align="L")
        self.set_x(self.l_margin)
        self.cell(0, 6, self.labels["page"].format(page=self.page_no(), pages="{nb}"), align="R")


def _section_heading(pdf: FPDF, heading: str) -> None:
    """A section title with the module's fuchsia accent bar in front of it."""
    # Start a new page rather than leaving a heading orphaned at the bottom.
    if pdf.get_y() > pdf.h - 50:
        pdf.add_page()
    pdf.ln(3)
    top = pdf.get_y()
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(pdf.l_margin, top + 1.2, 1.6, 6, style="F")
    # Reset the fill colour, or the next table's plain rows inherit the accent.
    pdf.set_fill_color(255, 255, 255)
    pdf.set_xy(pdf.l_margin + 4, top)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 8.5, _pdf_text(heading), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)


def _muted_line(pdf: FPDF, text: str) -> None:
    """A grey, italic explanatory line (empty lists, placeholders)."""
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.multi_cell(0, 6, _pdf_text(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _render_header(pdf: FPDF, state: TeamStateResponse, labels: dict) -> None:
    """Fuchsia top band, the Altsien logo left, title + team + season right."""
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(0, 0, pdf.w, 3, style="F")

    logo_height = 26
    if ALTSIEN_LOGO.exists():
        pdf.image(str(ALTSIEN_LOGO), x=pdf.l_margin, y=10, h=logo_height)
    text_left = pdf.l_margin + logo_height * ALTSIEN_LOGO_RATIO + 8

    pdf.set_xy(text_left, 11)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 6, _pdf_text(labels["title"].upper()), new_x="LEFT", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(pdf.w - pdf.r_margin - text_left, 10, _pdf_text(state.team.name), new_x="LEFT", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*MUTED_TEXT)
    season_text = labels["season"].format(season=state.season_name)
    if not state.season_open:
        season_text += f" ({labels['season_closed']})"
    pdf.cell(0, 6, _pdf_text(season_text), new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(max(pdf.get_y(), 10 + logo_height) + 5)
    pdf.set_draw_color(*ACCENT_COLOR)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def _render_team_info(pdf: FPDF, state: TeamStateResponse, labels: dict) -> None:
    """Label/value pairs with the team's master data."""
    _section_heading(pdf, labels["team_heading"])
    team = state.team
    fields = [
        (labels["team_name"], team.name),
        (labels["location"], team.location),
        (labels["delivery_method"], team.delivery_method),
        (labels["kernleden"], ", ".join(team.kernleden) if team.kernleden else None),
    ]
    if team.description:
        fields.append((labels["description"], team.description))

    for label, value in fields:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*MUTED_TEXT)
        pdf.cell(45, 6.5, _pdf_text(label))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(0, 6.5, _pdf_text(value or labels["not_specified"]), new_x="LMARGIN", new_y="NEXT")


def _draw_step_marker(pdf: FPDF, x: float, y: float, done: bool) -> None:
    """A green circle with a tick for a done step, an empty ring otherwise
    (drawn as shapes, since the core font has no tick character).
    """
    radius = 2.4
    if done:
        pdf.set_fill_color(*DONE_GREEN)
        pdf.circle(x=x + radius, y=y + radius, radius=radius, style="F")
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.5)
        pdf.line(x + 1.2, y + 2.5, x + 2.1, y + 3.4)
        pdf.line(x + 2.1, y + 3.4, x + 3.7, y + 1.5)
    else:
        pdf.set_draw_color(*MUTED_TEXT)
        pdf.set_line_width(0.35)
        pdf.circle(x=x + radius, y=y + radius, radius=radius, style="D")


def _render_progress(pdf: FPDF, state: TeamStateResponse, labels: dict) -> None:
    """One line per wizard step: marker, step name, done-on/by or to-do."""
    _section_heading(pdf, labels["progress_heading"])
    progress_by_key = {item.step_key: item for item in state.progress}

    for step in state.steps:
        done = progress_by_key.get(step.key)
        y = pdf.get_y()
        _draw_step_marker(pdf, pdf.l_margin + 1, y + 0.8, done is not None)
        pdf.set_xy(pdf.l_margin + 9, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(55, 6.5, _pdf_text(labels["steps"].get(step.key, step.label)))
        pdf.set_font("Helvetica", "", 10)
        if done is not None:
            by = labels["step_done_by"].format(name=done.completed_by_name) if done.completed_by_name else ""
            pdf.set_text_color(*DONE_GREEN)
            pdf.cell(0, 6.5, _pdf_text(labels["step_done"].format(date=_format_date(done.completed_at), by=by)))
        else:
            pdf.set_text_color(*MUTED_TEXT)
            pdf.cell(0, 6.5, _pdf_text(labels["step_todo"]))
        pdf.ln(7.5)


def _table_heading_style() -> FontFace:
    """Bold, dark heading row with a light fill."""
    return FontFace(emphasis="BOLD", color=TEXT_DARK, fill_color=(233, 235, 238))


def _render_festivals(pdf: FPDF, state: TeamStateResponse, labels: dict) -> None:
    """Zebra table of the selected festivals and their delivery location."""
    _section_heading(pdf, labels["festivals_heading"])
    selected = [festival for festival in state.festivals if festival.selected]
    if not selected:
        _muted_line(pdf, labels["no_festivals"])
        return

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.2)
    with pdf.table(
        col_widths=(50, 50, 80),
        headings_style=_table_heading_style(),
        cell_fill_color=ZEBRA_FILL,
        cell_fill_mode="ROWS",
        borders_layout="HORIZONTAL_LINES",
        line_height=6.5,
        padding=2,
        text_align="LEFT",
    ) as table:
        table.row([labels["festival"], labels["dates"], labels["afleverlocatie"]])
        for festival in selected:
            if festival.afleverlocatie_name:
                location = festival.afleverlocatie_name
                if festival.afleverlocatie_description:
                    location += f"\n{festival.afleverlocatie_description}"
                location_style = None
            else:
                location = labels["no_location"]
                location_style = FontFace(emphasis="ITALICS", color=MUTED_TEXT)
            row = table.row()
            row.cell(_pdf_text(festival.festival_name), style=FontFace(emphasis="BOLD"))
            # A one-day festival shows a single date instead of a range.
            period = _format_date(festival.start_date)
            if festival.end_date != festival.start_date:
                period += f" - {_format_date(festival.end_date)}"
            row.cell(period)
            row.cell(_pdf_text(location), style=location_style)
    pdf.ln(2)


def _render_requests(pdf: FPDF, state: TeamStateResponse, labels: dict) -> None:
    """Table of special requests, the status in its own colour."""
    _section_heading(pdf, labels["requests_heading"])
    if not state.requests:
        _muted_line(pdf, labels["no_requests"])
        return

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.2)
    with pdf.table(
        col_widths=(85, 30, 65),
        headings_style=_table_heading_style(),
        cell_fill_color=ZEBRA_FILL,
        cell_fill_mode="ROWS",
        borders_layout="HORIZONTAL_LINES",
        line_height=6.5,
        padding=2,
        text_align="LEFT",
    ) as table:
        table.row([labels["request"], labels["status"], labels["organisation_note"]])
        for request in state.requests:
            row = table.row()
            row.cell(_pdf_text(request.text))
            row.cell(
                _pdf_text(request.status_name),
                style=FontFace(emphasis="BOLD", color=STATUS_RGB.get(request.status_color, MUTED_TEXT)),
            )
            row.cell(_pdf_text(request.organisation_note or "-"))
    pdf.ln(2)


def _render_placeholder(pdf: FPDF, heading: str, labels: dict) -> None:
    """A section whose content comes from a module that doesn't exist yet."""
    _section_heading(pdf, heading)
    _muted_line(pdf, labels["placeholder"])


def build_ploegfiche_pdf(state: TeamStateResponse, locale: str = "nl") -> bytes:
    """The Ploegfiche PDF for one team in one season."""
    labels = LABELS.get(locale, LABELS["nl"])
    generated_on = datetime.now(timezone.utc).astimezone().strftime("%d-%m-%Y %H:%M")

    pdf = _PloegfichePDF(labels, generated_on)
    pdf.set_margins(15, 12, 15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.alias_nb_pages()
    pdf.add_page()

    _render_header(pdf, state, labels)
    _render_team_info(pdf, state, labels)
    _render_progress(pdf, state, labels)

    # One section per wizard step, in wizard order. A step without its own
    # renderer here (e.g. one added later) only appears in the progress list.
    step_renderers = {
        "festivals": lambda: _render_festivals(pdf, state, labels),
        "products": lambda: _render_placeholder(pdf, labels["steps"]["products"], labels),
        "special_requests": lambda: _render_requests(pdf, state, labels),
        "walkies": lambda: _render_placeholder(pdf, labels["steps"]["walkies"], labels),
    }
    for step in state.steps:
        renderer = step_renderers.get(step.key)
        if renderer is not None:
            renderer()

    return bytes(pdf.output())
