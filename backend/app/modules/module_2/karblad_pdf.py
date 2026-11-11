# Builds the printable "karbladen" PDF for KarTracker's Kar Planning screen:
# one A4 page per selected kar, stuck on the kar itself — so it is the most
# visible document the app prints and is designed to read from a distance
# and to print cleanly on a black-and-white printer (no colour at all).
#
# Page, top to bottom:
#   - header: RW logo, the selected season's name (the year) and a QR code
#     carrying just the kar number (for scanning the kar);
#   - the kar number, very large, with the kar's transport type;
#   - an info panel: Vereniging and Aflever zone (of the afleverlocatie at
#     the season's first active festival);
#   - the delivery schedule: one block per festival, ordered by delivery
#     date, laid out in a grid that always fits the page;
#   - a help box whose QR code opens the public kar page (no login) with its
#     two tiles, Interventie aanvragen and Kar inventaris, prefilled for this
#     kar (see build_kar_qr_url);
#   - a small footer with TeamKar's internal delivery info (Distributiepunt
#     and Terreinpositie of that same location) and the print date.
# The kar's lock code (karcode) is deliberately NOT printed: this sheet hangs
# on the kar, so printing it would defeat the lock.
#
# Uses fpdf2 (pure Python) with the shared helpers of app/shared/pdf_common.py
# and the QR drawing of module_4/pdf_layout.py (vector rectangles, razor sharp
# at any print resolution).

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from urllib.parse import urlencode

from fpdf import FPDF
from PIL import Image

from app.core.timezone import belgian_now
from app.modules.module_4.pdf_layout import draw_qr
from app.shared.pdf_common import (
    ASSETS_DIR,
    BORDER_COLOR,
    MUTED_TEXT,
    TEAMKAR_LOGO_RATIO,
    pdf_text,
    teamkar_logo,
)

# The "RW" logo top left of the sheet (square image). Printed in greyscale so
# a black-and-white printer gives a predictable result; without the file the
# header simply starts with the title.
RW_LOGO = ASSETS_DIR / "rw-logo.png"
RW_LOGO_PRINT_PX = 400

# Page geometry in mm (A4 portrait).
PAGE_W, PAGE_H = 210.0, 297.0
MARGIN = 12.0
CONTENT_W = PAGE_W - 2 * MARGIN

# Black-and-white palette: pure black for the important things, greys for
# labels, panels and lines.
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PANEL_FILL = (241, 241, 241)
FOOTER_TEXT = (75, 75, 75)

# Vertical bands of the page (top y of each part).
HEADER_TOP = MARGIN
HEADER_RULE_Y = 42.0
HERO_TOP = 47.0
INFO_TOP = 99.0
INFO_H = 17.0
SCHEDULE_TOP = 122.0
SCHEDULE_BOTTOM = 226.0
HELP_TOP = 231.0
HELP_H = 50.0
FOOTER_Y = 285.0

# Festival blocks: the gap between them, and the height at which a block is
# drawn at full size (smaller blocks scale their fonts down with it).
CARD_GAP = 4.0
CARD_FULL_H = 40.0

LABELS = {
    "nl": {
        "subtitle": "Karblad",
        "kar_box": "KAR / BOX",
        "type": "TYPE",
        "association": "VERENIGING",
        "zone": "AFLEVER ZONE",
        "distribution_point": "Distributiepunt:",
        "terrain_position": "Terreinpositie:",
        "schedule": "Levering en ophaling per festival",
        "delivery": "LEVERING",
        "pickup": "OPHALING",
        "card_zone": "ZONE",
        "location": "LOCATIE",
        "no_festivals": "Er zijn nog geen festivals gepland voor dit jaar.",
        "help_line_1": "Iets te kort? Vragen over het materiaal?",
        "help_line_2": "Scan de QR-code met je smartphone.",
        "help_line_3": "Vraag een interventie aan of geef de inhoud van je kar door.",
        "printed_on": "Afgedrukt op {date}",
        "weekdays": ["ma", "di", "wo", "do", "vr", "za", "zo"],
        "months": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    },
    "en": {
        "subtitle": "Cart sheet",
        "kar_box": "KAR / BOX",
        "type": "TYPE",
        "association": "ASSOCIATION",
        "zone": "DELIVERY ZONE",
        "distribution_point": "Distribution point:",
        "terrain_position": "Terrain position:",
        "schedule": "Delivery and pick-up per festival",
        "delivery": "DELIVERY",
        "pickup": "PICK-UP",
        "card_zone": "ZONE",
        "location": "LOCATION",
        "no_festivals": "No festivals have been planned for this year yet.",
        "help_line_1": "Missing something? Questions about the equipment?",
        "help_line_2": "Scan the QR code with your smartphone.",
        "help_line_3": "Request an intervention or report what is in your kar.",
        "printed_on": "Printed on {date}",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
}


@dataclass
class KarbladFestival:
    """One row of the karblad's schedule: where the kar's team is delivered
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
    # Where the lower QR code points to (the public kar page).
    qr_url: str = ""
    # Zone, distribution point and terrain position of the afleverlocatie the
    # kar's team has at the season's first active festival (empty when the
    # team planned nothing there).
    aflever_zone: str | None = None
    distribution_point: str | None = None
    terrein_positie: int | None = None


def build_kar_qr_url(
    site_url: str,
    locale: str,
    team_id: int | None,
    cart_number: str,
    delivery_location: str | None,
    zone: str | None,
) -> str:
    """The public kar page (no login needed: Interventie aanvragen + Kar
    inventaris) with the fields we already know, which its tiles pass on to
    the forms: team, kar number, and the delivery location/zone. Blank values
    are left out of the query string. Older karbladen point to
    /intervention-request, which the frontend redirects to this page.
    """
    params = {
        "team_id": team_id,
        "cart_number": cart_number,
        "delivery_location": delivery_location,
        "zone": zone,
    }
    query = urlencode({key: value for key, value in params.items() if value not in (None, "")})
    return f"{site_url.rstrip('/')}/{locale}/kar?{query}"


@lru_cache(maxsize=1)
def _rw_logo() -> Image.Image | None:
    """The RW logo in greyscale, shrunk once for printing (None if missing)."""
    if not RW_LOGO.exists():
        return None
    logo = Image.open(RW_LOGO).convert("L")
    logo.thumbnail((RW_LOGO_PRINT_PX, RW_LOGO_PRINT_PX), Image.Resampling.LANCZOS)
    return logo


def _format_date(value: date | None, labels: dict) -> str:
    """"za 20 jun" — short weekday, day and month, without depending on the
    server's locale settings."""
    if value is None:
        return ""
    return f"{labels['weekdays'][value.weekday()]} {value.day} {labels['months'][value.month - 1]}"


def _fit(pdf: FPDF, text: object, width: float) -> str:
    """`text` made latin-1 safe and cut off with "..." so it fits in `width`
    mm in the current font (table cells stay on one line)."""
    value = pdf_text(text)
    if pdf.get_string_width(value) <= width:
        return value
    while value and pdf.get_string_width(value + "...") > width:
        value = value[:-1]
    return value.rstrip() + "..."


def _wrap_lines(pdf: FPDF, text: object, width: float, max_lines: int) -> list[str]:
    """`text` broken on spaces into lines of at most `width` mm in the
    current font, at most `max_lines` of them; only what still doesn't fit on
    the last line is cut off with "..."."""
    words = pdf_text(text).split()
    lines: list[str] = []
    current = ""
    for index, word in enumerate(words):
        candidate = f"{current} {word}".strip()
        if not current or pdf.get_string_width(candidate) <= width:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            # Last allowed line: everything that's left, cut to fit.
            current = " ".join(words[index:])
            break
    if current:
        lines.append(current)
    return [_fit(pdf, line, width) for line in lines[:max_lines]]


def _fit_font_size(pdf: FPDF, text: str, style: str, size: float, width: float, minimum: float) -> float:
    """The largest font size ≤ `size` (but ≥ `minimum`) at which `text`
    fits in `width` mm — big values shrink instead of running over."""
    while size > minimum:
        pdf.set_font("Helvetica", style, size)
        if pdf.get_string_width(text) <= width:
            return size
        size -= 0.5
    return minimum


def _text(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    h: float,
    text: object,
    *,
    style: str = "",
    size: float = 10,
    color: tuple[int, int, int] = BLACK,
    align: str = "L",
    spacing: float = 0,
) -> None:
    """One line of borderless text at an absolute position, cut to fit."""
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(*color)
    pdf.set_char_spacing(spacing)
    pdf.set_xy(x, y)
    pdf.cell(w, h, _fit(pdf, text, w - 1), align=align)
    pdf.set_char_spacing(0)


def _draw_header(pdf: FPDF, kar: KarbladData, title: str, labels: dict) -> None:
    """RW logo, the season's name with "Karblad" under it, the kar-number QR
    code right, and a heavy rule under it all."""
    logo = _rw_logo()
    text_left = MARGIN
    if logo is not None:
        pdf.image(logo, x=MARGIN, y=HEADER_TOP, w=26, h=26)
        text_left = MARGIN + 26 + 6

    qr_size = 26.0
    text_w = PAGE_W - MARGIN - qr_size - 4 - text_left
    _text(pdf, text_left, HEADER_TOP + 3, text_w, 12, title, style="B", size=28)
    _text(pdf, text_left, HEADER_TOP + 16, text_w, 7, labels["subtitle"], size=13, color=MUTED_TEXT)

    # Just the kar number, so scanning it identifies the kar.
    draw_qr(pdf, kar.kar_nummer, PAGE_W - MARGIN - qr_size, HEADER_TOP, qr_size)

    pdf.set_draw_color(*BLACK)
    pdf.set_line_width(0.9)
    pdf.line(MARGIN, HEADER_RULE_Y, PAGE_W - MARGIN, HEADER_RULE_Y)


def _draw_hero(pdf: FPDF, kar: KarbladData, labels: dict) -> None:
    """The kar number as large as fits, with its transport type in an
    outlined box on the right."""
    type_w = 52.0
    number_w = CONTENT_W - type_w - 8

    _text(pdf, MARGIN, HERO_TOP + 1, number_w, 6, labels["kar_box"], style="B", size=10,
          color=MUTED_TEXT, spacing=1.2)
    number = pdf_text(kar.kar_nummer)
    size = _fit_font_size(pdf, number, "B", 110, number_w, 40)
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(*BLACK)
    pdf.set_xy(MARGIN - 1.5, HERO_TOP + 8)
    pdf.cell(number_w, 40, number, align="L")

    # Transport type: outlined box, small label over a bold value.
    box_x = PAGE_W - MARGIN - type_w
    box_y = HERO_TOP + 14
    pdf.set_draw_color(*BLACK)
    pdf.set_line_width(0.6)
    pdf.rect(box_x, box_y, type_w, 24, style="D", round_corners=True, corner_radius=2.5)
    _text(pdf, box_x, box_y + 3, type_w, 5, labels["type"], style="B", size=8, color=MUTED_TEXT,
          align="C", spacing=1.2)
    type_size = _fit_font_size(pdf, pdf_text(kar.transport_type), "B", 18, type_w - 6, 9)
    _text(pdf, box_x, box_y + 10, type_w, 10, kar.transport_type, style="B", size=type_size, align="C")


def _draw_info_panel(pdf: FPDF, kar: KarbladData, labels: dict) -> None:
    """A grey panel with the team and the delivery zone side by side."""
    pdf.set_fill_color(*PANEL_FILL)
    pdf.rect(MARGIN, INFO_TOP, CONTENT_W, INFO_H, style="F", round_corners=True, corner_radius=2.5)

    cells = (
        (labels["association"], kar.team_name),
        (labels["zone"], kar.aflever_zone),
    )
    column_w = CONTENT_W / 2
    for index, (label, value) in enumerate(cells):
        x = MARGIN + 5 + index * column_w
        y = INFO_TOP + 3
        width = column_w - 8
        _text(pdf, x, y, width, 4, label, style="B", size=7.5, color=MUTED_TEXT, spacing=0.8)
        shown = pdf_text(value) if value not in (None, "") else "-"
        value_size = _fit_font_size(pdf, shown, "B", 14, width - 1, 9)
        _text(pdf, x, y + 4.5, width, 7, shown, style="B", size=value_size)


def _sorted_festivals(festivals: list[KarbladFestival]) -> list[KarbladFestival]:
    """Festivals by delivery date; the ones without a delivery date come
    last, keeping the order they were given in (festival start date)."""
    return sorted(festivals, key=lambda festival: (festival.delivery_date is None, festival.delivery_date or date.min))


def _grid_columns(count: int) -> int:
    """How many festival blocks sit side by side: few festivals get wide
    blocks, a big season gets more columns so everything stays on the page."""
    if count <= 2:
        return 1
    if count <= 6:
        return 2
    if count <= 12:
        return 3
    return 4


def _draw_festival_card(
    pdf: FPDF, festival: KarbladFestival, x: float, y: float, w: float, h: float, labels: dict
) -> None:
    """One festival's block: its name in a black bar, then delivery date,
    pick-up date and zone side by side, and the full location under them
    (wrapped over at most two lines). Everything scales with the block's
    height, so a small block is a smaller copy of a full one."""
    scale = min(1.0, h / CARD_FULL_H)
    pad = 4 * scale

    # Outline and the black name bar.
    pdf.set_draw_color(*BLACK)
    pdf.set_line_width(0.4)
    pdf.rect(x, y, w, h, style="D")
    bar_h = 8 * scale
    pdf.set_fill_color(*BLACK)
    pdf.rect(x, y, w, bar_h, style="F")
    name = pdf_text(festival.name)
    name_size = _fit_font_size(pdf, name, "B", 13 * scale, w - 2 * pad, 9 * scale)
    _text(pdf, x + pad, y, w - 2 * pad, bar_h, name, style="B", size=name_size, color=WHITE)

    # Delivery date, pick-up date and zone in three columns.
    label_size = 7.5 * scale
    label_h = 4 * scale
    top = y + bar_h + pad * 0.8
    column_w = (w - 2 * pad) / 3
    columns = (
        (labels["delivery"], _format_date(festival.delivery_date, labels)),
        (labels["pickup"], _format_date(festival.pickup_date, labels)),
        (labels["card_zone"], festival.zone_name),
    )
    for index, (label, value) in enumerate(columns):
        column_x = x + pad + index * column_w
        _text(pdf, column_x, top, column_w, label_h, label, style="B", size=label_size, color=MUTED_TEXT,
              spacing=0.8 * scale)
        shown = pdf_text(value) if value else "-"
        value_size = _fit_font_size(pdf, shown, "B", 13 * scale, column_w - 2, 8 * scale)
        _text(pdf, column_x, top + label_h, column_w, 6.5 * scale, shown, style="B", size=value_size)

    # The location, in full where possible.
    location_top = top + label_h + 6.5 * scale + 2.5 * scale
    _text(pdf, x + pad, location_top, w - 2 * pad, label_h, labels["location"], style="B", size=label_size,
          color=MUTED_TEXT, spacing=0.8 * scale)
    pdf.set_font("Helvetica", "B", 11 * scale)
    line_h = 5 * scale
    lines = _wrap_lines(pdf, festival.location, w - 2 * pad - 1, 2) if festival.location else ["-"]
    for index, line in enumerate(lines):
        _text(pdf, x + pad, location_top + label_h + index * line_h, w - 2 * pad, line_h, line, style="B",
              size=11 * scale)


def _draw_schedule(pdf: FPDF, kar: KarbladData, labels: dict) -> None:
    """Section title + one block per festival, ordered by delivery date, in
    a grid that fills the fixed room above the help box (more festivals =
    more columns and smaller blocks, never a second page)."""
    # Section title with a small black bar in front of it.
    pdf.set_fill_color(*BLACK)
    pdf.rect(MARGIN, SCHEDULE_TOP + 1.2, 1.6, 5.5, style="F")
    _text(pdf, MARGIN + 4, SCHEDULE_TOP, CONTENT_W - 4, 8, labels["schedule"], style="B", size=13)

    grid_top = SCHEDULE_TOP + 11
    festivals = _sorted_festivals(kar.festivals)
    if not festivals:
        _text(pdf, MARGIN, grid_top, CONTENT_W, 7, labels["no_festivals"], style="I", size=10,
              color=MUTED_TEXT)
        return

    columns = _grid_columns(len(festivals))
    rows = -(-len(festivals) // columns)
    card_w = (CONTENT_W - (columns - 1) * CARD_GAP) / columns
    # Blocks never grow taller than full size; few festivals leave room free.
    card_h = min(CARD_FULL_H, (SCHEDULE_BOTTOM - grid_top - (rows - 1) * CARD_GAP) / rows)
    for index, festival in enumerate(festivals):
        # Row by row, left to right, so the dates read in order.
        row, column = divmod(index, columns)
        _draw_festival_card(
            pdf,
            festival,
            MARGIN + column * (card_w + CARD_GAP),
            grid_top + row * (card_h + CARD_GAP),
            card_w,
            card_h,
            labels,
        )


def _draw_help_box(pdf: FPDF, kar: KarbladData, labels: dict) -> None:
    """Outlined box: the help text left, the public kar page's QR code
    right, the TeamKar logo bottom left."""
    pdf.set_draw_color(*BLACK)
    pdf.set_line_width(0.6)
    pdf.rect(MARGIN, HELP_TOP, CONTENT_W, HELP_H, style="D", round_corners=True, corner_radius=3)

    qr_size = 42.0
    text_x = MARGIN + 7
    text_w = CONTENT_W - qr_size - 18
    line_1 = pdf_text(labels["help_line_1"])
    size = _fit_font_size(pdf, line_1, "B", 16, text_w, 11)
    _text(pdf, text_x, HELP_TOP + 6, text_w, 8, line_1, style="B", size=size)
    _text(pdf, text_x, HELP_TOP + 16, text_w, 6, labels["help_line_2"], size=11)
    _text(pdf, text_x, HELP_TOP + 22, text_w, 6, labels["help_line_3"], size=11)

    logo = teamkar_logo()
    if logo is not None:
        logo_h = 15.0
        pdf.image(logo, x=text_x - 1, y=HELP_TOP + HELP_H - logo_h - 3, h=logo_h, w=logo_h * TEAMKAR_LOGO_RATIO)

    if kar.qr_url:
        draw_qr(pdf, kar.qr_url, PAGE_W - MARGIN - qr_size - 4, HELP_TOP + (HELP_H - qr_size) / 2, qr_size)


def _draw_footer(pdf: FPDF, kar: KarbladData, printed_on: str, labels: dict) -> None:
    """A thin grey line; left, small, TeamKar's internal delivery info
    (distribution point and terrain position, only needed while
    delivering); right the print date."""
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.2)
    pdf.line(MARGIN, FOOTER_Y - 0.5, PAGE_W - MARGIN, FOOTER_Y - 0.5)

    terrain = str(kar.terrein_positie) if kar.terrein_positie is not None else None
    x = MARGIN
    for label, value in (
        (labels["distribution_point"], kar.distribution_point),
        (labels["terrain_position"], terrain),
    ):
        # Label in normal weight, value in bold, each pair a few mm apart.
        pdf.set_font("Helvetica", "", 7.5)
        label_w = pdf.get_string_width(pdf_text(label)) + 1.2
        _text(pdf, x, FOOTER_Y, label_w + 1, 5, label, size=7.5, color=FOOTER_TEXT)
        shown = pdf_text(value) if value not in (None, "") else "-"
        pdf.set_font("Helvetica", "B", 7.5)
        value_w = min(60.0, pdf.get_string_width(shown) + 1.5)
        _text(pdf, x + label_w, FOOTER_Y, value_w + 1, 5, shown, style="B", size=7.5, color=FOOTER_TEXT)
        x += label_w + value_w + 6

    _text(pdf, MARGIN + CONTENT_W / 2, FOOTER_Y, CONTENT_W / 2, 5,
          labels["printed_on"].format(date=printed_on), size=7.5, color=MUTED_TEXT, align="R")


def _draw_page(pdf: FPDF, kar: KarbladData, title: str, labels: dict, printed_on: str) -> None:
    """One kar's page."""
    pdf.add_page()
    _draw_header(pdf, kar, title, labels)
    _draw_hero(pdf, kar, labels)
    _draw_info_panel(pdf, kar, labels)
    _draw_schedule(pdf, kar, labels)
    _draw_help_box(pdf, kar, labels)
    _draw_footer(pdf, kar, printed_on, labels)


def build_karbladen_pdf(karren: list[KarbladData], title: str, locale: str = "nl") -> bytes:
    """A PDF with one karblad page per entry of `karren`, in the given
    order. `title` (the selected season's name) heads every page."""
    labels = LABELS.get(locale, LABELS["nl"])
    printed_on = belgian_now().strftime("%d-%m-%Y")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    # Every element is placed at an absolute position, so fpdf2 must never
    # start an extra page on its own when a cell reaches the bottom.
    pdf.set_auto_page_break(auto=False)
    pdf.set_title(pdf_text(f"{labels['subtitle']} {title}"))
    for kar in karren:
        _draw_page(pdf, kar, title, labels, printed_on)

    return bytes(pdf.output())
