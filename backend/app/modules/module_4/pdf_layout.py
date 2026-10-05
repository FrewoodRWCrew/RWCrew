# StockMaster's PDF house style, shared by every StockMaster document
# (Laadlijst, Vertrekbon, Bestellijst, Telblad, Boekingsbon — see
# stock_pdfs.py), so they all look like one family:
#   - header on every page: a teal top band (StockMaster's colour), the
#     TeamKar logo left, the title + subtitle, and the document number and
#     print date (Belgian time) on the right;
#   - tables with a teal heading row (repeated on every page), light zebra
#     rows and right-aligned numbers;
#   - footer: "StockMaster · RWCrew", printed by whom, page x / y;
#   - optional signature boxes and a kar-number QR code (like the Karblad).
#
# Uses fpdf2, like the other PDFs (module_2/karblad_pdf.py,
# module_8/ploegfiche_pdf.py). The built-in Helvetica font only knows
# latin-1, so all text goes through pdf_text() first.

from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import segno
from fpdf import FPDF
from fpdf.enums import TableCellFillMode
from fpdf.fonts import FontFace
from PIL import Image

from app.core.timezone import belgian_now

# StockMaster's teal accent (teal-600, see frontend/src/lib/module-theme.ts).
ACCENT_COLOR = (13, 148, 136)
TEXT_DARK = (31, 41, 55)
MUTED_TEXT = (107, 114, 128)
BORDER_COLOR = (223, 226, 230)
ZEBRA_FILL = (240, 249, 248)
WARNING_COLOR = (234, 88, 12)

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
TEAMKAR_LOGO = ASSETS_DIR / "teamkar-logo.png"
# The logo's own width:height ratio (1536 x 1024 px).
TEAMKAR_LOGO_RATIO = 1536 / 1024
# The logo is printed ~24 mm wide: 480 px is plenty sharp and keeps every
# PDF small (the full-size image would add ~600 KB to each document).
TEAMKAR_LOGO_PRINT_WIDTH_PX = 480


@lru_cache(maxsize=1)
def _teamkar_logo() -> Image.Image | None:
    """The TeamKar logo, shrunk once for printing (None if it's missing)."""
    if not TEAMKAR_LOGO.exists():
        return None
    logo = Image.open(TEAMKAR_LOGO)
    height = round(TEAMKAR_LOGO_PRINT_WIDTH_PX / TEAMKAR_LOGO_RATIO)
    return logo.resize((TEAMKAR_LOGO_PRINT_WIDTH_PX, height), Image.Resampling.LANCZOS)

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
    "→": "->",
}


def pdf_text(text: object) -> str:
    """Make any value safe for the built-in latin-1 PDF font."""
    if text is None:
        return ""
    value = str(text)
    for character, replacement in _TEXT_REPLACEMENTS.items():
        value = value.replace(character, replacement)
    return value.encode("latin-1", "replace").decode("latin-1")


class StockMasterPDF(FPDF):
    """An A4 page in StockMaster's house style. The header and footer are
    drawn automatically on every page.
    """

    def __init__(
        self,
        labels: dict,
        *,
        title: str,
        subtitle: str,
        doc_number: str | None,
        printed_by: str | None,
        landscape: bool = False,
    ) -> None:
        super().__init__(orientation="L" if landscape else "P", unit="mm", format="A4")
        self.labels = labels
        self.doc_title = title
        self.doc_subtitle = subtitle
        self.doc_number = doc_number
        self.printed_by = printed_by
        self.printed_on = belgian_now().strftime("%d-%m-%Y %H:%M")
        self.set_margins(14, 14, 14)
        self.set_auto_page_break(auto=True, margin=20)
        self.alias_nb_pages()
        self.add_page()

    def header(self) -> None:
        """Teal band, TeamKar logo, title/subtitle, number and print date."""
        self.set_fill_color(*ACCENT_COLOR)
        self.rect(0, 0, self.w, 3, style="F")

        logo_height = 16
        logo_width = logo_height * TEAMKAR_LOGO_RATIO
        logo = _teamkar_logo()
        if logo is not None:
            self.image(logo, x=self.l_margin, y=7, h=logo_height)
        text_left = self.l_margin + logo_width + 5
        right_block = 55

        # Title and subtitle, left of the right-hand block.
        self.set_xy(text_left, 8)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*TEXT_DARK)
        self.cell(self.w - self.r_margin - text_left - right_block, 8, pdf_text(self.doc_title))
        self.set_xy(text_left, 16.5)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*MUTED_TEXT)
        self.cell(self.w - self.r_margin - text_left - right_block, 5, pdf_text(self.doc_subtitle))

        # Document number and print date, right-aligned.
        self.set_xy(self.w - self.r_margin - right_block, 8)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*TEXT_DARK)
        if self.doc_number:
            self.cell(right_block, 5, pdf_text(self.doc_number), align="R")
        self.set_xy(self.w - self.r_margin - right_block, 13.5)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*MUTED_TEXT)
        self.cell(right_block, 5, pdf_text(self.labels["printed_on"].format(date=self.printed_on)), align="R")

        # Teal rule under the header.
        self.set_draw_color(*ACCENT_COLOR)
        self.set_line_width(0.5)
        self.line(self.l_margin, 26, self.w - self.r_margin, 26)
        self.set_y(30)

    def footer(self) -> None:
        """"StockMaster · RWCrew · printed by ..." left, page x / y right."""
        self.set_y(-13)
        self.set_draw_color(*BORDER_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 1.5, self.w - self.r_margin, self.get_y() - 1.5)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED_TEXT)
        left = "StockMaster · RWCrew"
        if self.printed_by:
            left += " · " + self.labels["printed_by"].format(name=self.printed_by)
        self.cell(0, 6, pdf_text(left), align="L")
        self.set_x(self.l_margin)
        self.cell(0, 6, pdf_text(self.labels["page"].format(page=self.page_no(), pages="{nb}")), align="R")


def info_rows(pdf: FPDF, rows: Sequence[tuple[str, object]], label_width: float = 38) -> None:
    """Label/value pairs under the header (kar, team, season, ...). Empty
    values are skipped.
    """
    for label, value in rows:
        if value in (None, ""):
            continue
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*MUTED_TEXT)
        pdf.cell(label_width, 6, pdf_text(label))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(0, 6, pdf_text(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def section_heading(pdf: FPDF, heading: str) -> None:
    """A section title with a small teal bar in front of it."""
    if pdf.get_y() > pdf.h - 45:
        pdf.add_page()
    pdf.ln(2)
    top = pdf.get_y()
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(pdf.l_margin, top + 1.2, 1.6, 5.5, style="F")
    pdf.set_fill_color(255, 255, 255)
    pdf.set_xy(pdf.l_margin + 4, top)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 8, pdf_text(heading), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def muted_line(pdf: FPDF, text: str) -> None:
    """A grey, italic explanatory line (e.g. an empty list)."""
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.multi_cell(0, 6, pdf_text(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def data_table(
    pdf: FPDF,
    headings: Sequence[str],
    rows: Sequence[Sequence[object]],
    col_widths: Sequence[float],
    align: Sequence[str],
    *,
    total_row: Sequence[object] | None = None,
) -> None:
    """A table in the house style: teal heading row (repeated on every
    page), zebra rows, numbers aligned as asked ("L"/"R"/"C" per column)
    and an optional bold totals row.
    """
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.2)
    heading_style = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=ACCENT_COLOR)
    with pdf.table(
        col_widths=tuple(col_widths),
        width=sum(col_widths),
        align="LEFT",
        text_align=tuple(align),
        headings_style=heading_style,
        cell_fill_color=ZEBRA_FILL,
        cell_fill_mode=TableCellFillMode.ROWS,
        line_height=6.2,
        borders_layout="HORIZONTAL_LINES",
        repeat_headings=1,
    ) as table:
        heading_row = table.row()
        for heading in headings:
            heading_row.cell(pdf_text(heading))
        for values in rows:
            row = table.row()
            for value in values:
                row.cell(pdf_text(value))
        if total_row is not None:
            row = table.row(style=FontFace(emphasis="BOLD"))
            for value in total_row:
                row.cell(pdf_text(value))
    pdf.ln(2)


def signature_boxes(pdf: FPDF, captions: Sequence[str], labels: dict) -> None:
    """One box per caption ("Magazijn", "Ploeg") with name, date and
    signature lines, side by side at the bottom of the content.
    """
    box_height = 30
    if pdf.get_y() > pdf.h - pdf.b_margin - box_height - 6:
        pdf.add_page()
    pdf.ln(4)
    top = pdf.get_y()
    gap = 6
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    width = (usable - gap * (len(captions) - 1)) / len(captions)
    for index, caption in enumerate(captions):
        left = pdf.l_margin + index * (width + gap)
        pdf.set_draw_color(*BORDER_COLOR)
        pdf.set_line_width(0.3)
        pdf.rect(left, top, width, box_height)
        pdf.set_xy(left + 2, top + 1.5)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT_COLOR)
        pdf.cell(width - 4, 5, pdf_text(caption))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*MUTED_TEXT)
        for offset, label in ((10, labels["sign_name"]), (17, labels["sign_date"]), (24, labels["sign_signature"])):
            pdf.set_xy(left + 2, top + offset)
            pdf.cell(22, 5, pdf_text(label))
            pdf.set_draw_color(*BORDER_COLOR)
            pdf.line(left + 24, top + offset + 4.2, left + width - 3, top + offset + 4.2)
    pdf.set_y(top + box_height + 2)


def draw_qr(pdf: FPDF, text: str, x: float, y: float, size: float) -> None:
    """Draw `text` as a QR code filling a size x size mm square at (x, y) —
    the same drawing as the Karblad's (module_2/karblad_pdf.py), so a kar's
    QR code scans the same everywhere. Adjacent dark modules are merged into
    one rectangle so PDF viewers show no hairline seams.
    """
    matrix = [list(row) for row in segno.make(text, error="m", micro=False).matrix]
    quiet = 1
    module_size = size / (len(matrix) + 2 * quiet)
    pdf.set_fill_color(0, 0, 0)
    for row_index, row in enumerate(matrix):
        column = 0
        while column < len(row):
            if not row[column]:
                column += 1
                continue
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
    pdf.set_fill_color(255, 255, 255)


def finish(pdf: FPDF) -> bytes:
    """The finished document as bytes."""
    return bytes(pdf.output())
