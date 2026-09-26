# Builds the printable "karbladen" PDF for KarTracker's Kar Planning screen:
# one A4 page per selected kar, handed out with the kar itself. Each page
# shows the kar/box number, which team (Vereniging) it belongs to, and for
# every festival of the season where and when it is delivered and picked up.
# Two QR codes sit on the page: top right carries just the kar number (for
# scanning the kar), the lower one opens the public Intervention Request
# form prefilled for this kar's team (see build_request_url).
#
# Uses fpdf2 (pure Python, same library as module_3/intervention_request_pdf.py)
# and segno for the QR codes (also pure Python, no compiled dependency — see
# CLAUDE.md's Python 3.14 gotcha). The QR modules are drawn as vector
# rectangles rather than embedded as an image, so they stay razor sharp at
# any print resolution and need no image handling.

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import segno
from fpdf import FPDF

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
TEAMKAR_LOGO = ASSETS_DIR / "teamkar-logo.png"
# The red "RW" logo top left of the sheet. Not shipped yet: dropping a square
# image with this name into app/assets/ makes it appear, until then the
# corner just stays empty.
RW_LOGO = ASSETS_DIR / "rw-logo.png"

# Page geometry in mm (A4 portrait, measured from the reference sheet): a
# framed page, with a narrower column of tables in the middle of it.
FRAME_X, FRAME_Y, FRAME_W, FRAME_H = 17.5, 19.0, 175.0, 222.5
TABLE_X, TABLE_W = 42.0, 125.0
LABEL_W = 38.0
VALUE_X = TABLE_X + LABEL_W
VALUE_W = TABLE_W - LABEL_W

# The festival blocks all live between the Vereniging/Aflever Zone rows and
# the Type table, so their room is fixed; more festivals just get smaller.
BLOCKS_TOP = 86.0
BLOCKS_BOTTOM = 161.0

LABELS = {
    "nl": {
        "kar_box": "Kar / Box",
        "association": "Vereniging:",
        "zone": "Aflever Zone:",
        "delivery": "Levering:",
        "pickup": "Ophaling:",
        "type": "Type",
        "remarks": "Opmerkingen:",
        "help_line_1": "Iets te kort? Vragen?",
        "help_line_2": "Contacteer ons via de onderstaande link.",
        "pick_order": "Pick Orde:",
        "distribution_point": "DistributiePunt:",
        "route": "Rit:",
        "weekdays": ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"],
        "months": [
            "januari", "februari", "maart", "april", "mei", "juni",
            "juli", "augustus", "september", "oktober", "november", "december",
        ],
    },
    "en": {
        "kar_box": "Kar / Box",
        "association": "Association:",
        "zone": "Delivery Zone:",
        "delivery": "Delivery:",
        "pickup": "Pick-up:",
        "type": "Type",
        "remarks": "Remarks:",
        "help_line_1": "Missing something? Questions?",
        "help_line_2": "Contact us via the link below.",
        "pick_order": "Pick Order:",
        "distribution_point": "Distribution Point:",
        "route": "Route:",
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "months": [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
    },
}


@dataclass
class KarbladFestival:
    """One festival block on a karblad: where the kar's team is delivered
    for that festival and the festival's delivery/pick-up dates. Every
    field but the name may be missing (nothing planned / no dates entered).
    """

    name: str
    zone_name: str | None = None
    location: str | None = None
    delivery_date: date | None = None
    pickup_date: date | None = None


@dataclass
class KarbladData:
    """Everything printed on one kar's page."""

    kar_nummer: str
    team_name: str | None
    transport_type: str
    festivals: list[KarbladFestival] = field(default_factory=list)
    # Where the lower QR code points to.
    request_url: str = ""
    # The zone shown next to "Aflever Zone" and the distribution point in the
    # footer are both taken from the first festival with a planned location.
    aflever_zone: str | None = None
    distribution_point: str | None = None
    # Not stored anywhere yet — printed as empty fields so the paper sheet
    # keeps its layout (and can be filled in by hand) until they exist.
    pick_order: str | None = None
    route: str | None = None
    remarks: str | None = None


def build_request_url(
    site_url: str,
    locale: str,
    team_id: int | None,
    cart_number: str,
    delivery_location: str | None,
    zone: str | None,
) -> str:
    """The public Intervention Request form (no login needed) with the
    fields we already know prefilled: team, kar number, and the delivery
    location/zone. Blank values are left out of the query string.
    """
    params = {
        "team_id": team_id,
        "cart_number": cart_number,
        "delivery_location": delivery_location,
        "zone": zone,
    }
    query = urlencode({key: value for key, value in params.items() if value not in (None, "")})
    return f"{site_url.rstrip('/')}/{locale}/intervention-request?{query}"


def _safe(text: str | None) -> str:
    """fpdf2's built-in Helvetica only knows Latin-1, so map the typographic
    characters that commonly appear in names to plain ones and turn anything
    else it can't print into "?" instead of crashing the whole PDF.
    """
    if not text:
        return ""
    replacements = {"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "…": "...", " ": " "}
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode("latin-1", "replace").decode("latin-1")


def _format_date(value: date | None, labels: dict) -> str:
    """"Zaterdag 20 juni" — weekday, day and month name, without depending
    on the server's locale settings."""
    if value is None:
        return ""
    return f"{labels['weekdays'][value.weekday()]} {value.day} {labels['months'][value.month - 1]}"


def _cell(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str | None = "",
    *,
    style: str = "",
    size: float = 9,
    align: str = "C",
    border: bool = True,
) -> None:
    """One bordered (or borderless) text cell at an absolute position."""
    pdf.set_xy(x, y)
    pdf.set_font("Helvetica", style, size)
    pdf.cell(w, h, _safe(text), border=1 if border else 0, align=align)


def _draw_qr(pdf: FPDF, text: str, x: float, y: float, size: float) -> None:
    """Draws `text` as a QR code filling a size x size mm square at (x, y).
    Horizontally adjacent dark modules are merged into one rectangle so
    PDF viewers don't show hairline seams between them.
    """
    # A quiet zone of one module around the code keeps it scannable when the
    # page has printed borders right next to it.
    matrix = [list(row) for row in segno.make(text, error="m", micro=False).matrix]
    quiet = 1
    modules = len(matrix) + 2 * quiet
    module_size = size / modules

    pdf.set_fill_color(0, 0, 0)
    for row_index, row in enumerate(matrix):
        column = 0
        while column < len(row):
            if not row[column]:
                column += 1
                continue
            # Extend the run of dark modules as far as it goes.
            run_end = column
            while run_end < len(row) and row[run_end]:
                run_end += 1
            pdf.rect(
                x + (column + quiet) * module_size,
                y + (row_index + quiet) * module_size,
                (run_end - column) * module_size,
                module_size,
                style="F",
            )
            column = run_end


def _draw_festival_block(pdf: FPDF, y: float, pitch: float, festival: KarbladFestival, labels: dict) -> None:
    """One festival's heading plus its table. With plenty of room it is the
    reference sheet's three rows (zone code / Levering / Ophaling); when the
    season has many festivals it squeezes into two rows so it still fits.
    """
    compact = pitch < 18
    compact_row_count = 2
    if compact:
        row_h = max(2.5, min(3.8, (pitch - 4.5) / compact_row_count))
        heading_h = pitch - 0.5 - compact_row_count * row_h
        font_size = max(5.5, min(7.5, row_h * 2))
    else:
        row_h = min(5.7, (pitch - 9) / 3)
        font_size = 9
        heading_h = 4.5

    # Heading: the festival's name, bold + underlined, over the value column.
    _cell(pdf, VALUE_X, y, VALUE_W, heading_h, festival.name, style="BU", size=font_size + 1, border=False)
    table_y = y + heading_h + 0.5

    delivery = _format_date(festival.delivery_date, labels)
    pickup = _format_date(festival.pickup_date, labels)
    if compact:
        _cell(pdf, TABLE_X, table_y, LABEL_W, row_h, festival.zone_name, size=font_size)
        _cell(pdf, VALUE_X, table_y, VALUE_W, row_h, festival.location, style="B", size=font_size)
        _cell(pdf, TABLE_X, table_y + row_h, LABEL_W + VALUE_W, row_h,
              f"{labels['delivery']} {delivery}   |   {labels['pickup']} {pickup}", size=font_size)
        return

    # Row 1: zone code (label column) + location (value column).
    _cell(pdf, TABLE_X, table_y, LABEL_W, row_h, festival.zone_name, size=font_size)
    _cell(pdf, VALUE_X, table_y, VALUE_W, row_h, festival.location, style="B", size=font_size)
    # Rows 2 and 3: the two dates.
    _cell(pdf, TABLE_X, table_y + row_h, LABEL_W, row_h, labels["delivery"], size=font_size)
    _cell(pdf, VALUE_X, table_y + row_h, VALUE_W, row_h, delivery, size=font_size)
    _cell(pdf, TABLE_X, table_y + 2 * row_h, LABEL_W, row_h, labels["pickup"], size=font_size)
    _cell(pdf, VALUE_X, table_y + 2 * row_h, VALUE_W, row_h, pickup, size=font_size)


def _draw_page(pdf: FPDF, kar: KarbladData, title: str, labels: dict) -> None:
    """One kar's page."""
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.25)

    # --- Page frame, logos and title ---
    pdf.rect(FRAME_X, FRAME_Y, FRAME_W, FRAME_H)
    if RW_LOGO.exists():
        pdf.image(str(RW_LOGO), x=FRAME_X + 2.5, y=FRAME_Y + 1.5, w=20.5, h=20.5)
    _cell(pdf, FRAME_X + 25, 28, FRAME_W - 2 * 25 - 8, 12, title, style="BU", size=24, border=False)

    # --- Top right QR: just the kar number ---
    _draw_qr(pdf, kar.kar_nummer, 166.5, 22.0, 26.0)

    # --- Kar / Box banner ---
    _cell(pdf, TABLE_X, 48.5, LABEL_W, 15, labels["kar_box"], style="B", size=17)
    _cell(pdf, VALUE_X, 48.5, VALUE_W, 15, kar.kar_nummer, style="B", size=36)
    # The thin empty row the reference sheet has under the banner.
    _cell(pdf, TABLE_X, 63.5, TABLE_W, 3.5, "")

    # --- Vereniging + Aflever Zone ---
    _cell(pdf, TABLE_X, 67.0, LABEL_W, 6, labels["association"], size=10)
    _cell(pdf, VALUE_X, 67.0, VALUE_W, 6, kar.team_name, style="B", size=10)
    _cell(pdf, TABLE_X, 73.0, LABEL_W, 6, labels["zone"], size=10)
    _cell(pdf, VALUE_X, 73.0, VALUE_W, 6, kar.aflever_zone, style="B", size=10)

    # --- One block per festival, sharing the room between the rows above and the Type table ---
    if kar.festivals:
        pitch = min(26.0, (BLOCKS_BOTTOM - BLOCKS_TOP) / len(kar.festivals))
        for index, festival in enumerate(kar.festivals):
            _draw_festival_block(pdf, BLOCKS_TOP + index * pitch, pitch, festival, labels)

    # --- Type + remarks (left empty: nothing stores remarks yet) ---
    _cell(pdf, TABLE_X, 164.0, LABEL_W, 6, labels["type"], size=10)
    _cell(pdf, VALUE_X, 164.0, VALUE_W, 6, kar.transport_type, size=10)
    _cell(pdf, TABLE_X, 170.0, LABEL_W, 17, labels["remarks"], size=10)
    _cell(pdf, VALUE_X, 170.0, VALUE_W, 17, kar.remarks, size=10, align="L")

    # --- Help box with the lower QR (opens the prefilled intervention request) ---
    pdf.rect(TABLE_X, 187.0, TABLE_W, 47.0)
    _cell(pdf, TABLE_X, 189.0, TABLE_W, 6, labels["help_line_1"], style="B", size=12, border=False)
    _cell(pdf, TABLE_X, 195.0, TABLE_W, 6, labels["help_line_2"], style="B", size=12, border=False)
    if kar.request_url:
        _draw_qr(pdf, kar.request_url, TABLE_X + (TABLE_W - 30) / 2, 203.0, 30.0)
    if TEAMKAR_LOGO.exists():
        pdf.image(str(TEAMKAR_LOGO), x=FRAME_X + 2.5, y=221.0, w=19.0)

    # --- Footer line inside the frame ---
    _cell(pdf, FRAME_X, 237.5, 60, 4, f"{labels['pick_order']} {kar.pick_order or ''}", size=7, align="L", border=False)
    _cell(
        pdf, 89.5, 237.5, FRAME_W - 72, 4,
        f"{labels['distribution_point']} {kar.distribution_point or ''}    ||  {labels['route']}  {kar.route or ''}",
        size=7, align="L", border=False,
    )


def build_karbladen_pdf(karren: list[KarbladData], title: str, locale: str = "nl") -> bytes:
    """A PDF with one karblad page per entry of `karren`, in the given
    order. `title` is printed at the top of every page."""
    labels = LABELS.get(locale, LABELS["nl"])

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    # Every element is placed at an absolute position, so fpdf2 must never
    # start an extra page on its own when a cell reaches the bottom.
    pdf.set_auto_page_break(auto=False)
    for kar in karren:
        _draw_page(pdf, kar, title, labels)

    return bytes(pdf.output())
