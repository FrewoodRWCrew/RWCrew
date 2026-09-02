# Builds the "Tag Scan Summary" PDF for one Tag Headerdata row: every one
# of its lines grouped by matched product with a subtotal count per
# group (mirroring the Tag Linedata screen's "Group by Product" toggle,
# but scoped to a single file — grouping collapses to just the product,
# since every line here already shares the same filename). Lines with no
# matched product (status "no_match", "cancelled", or a "converted" line
# whose tag has no assigned product) are listed separately, not grouped.
#
# Uses fpdf2 — pure Python, no C/Rust toolchain required (matches the
# reason pg8000/openpyxl were chosen over compiled alternatives — see
# CLAUDE.md's Python 3.14 gotcha).

from datetime import datetime

from fpdf import FPDF
from sqlalchemy.orm import Session

from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.modules.module_1.tag_line_data import list_lines_for_header

# Tailwind's blue-600, matching TagScan's own module accent colour
# (see frontend/src/lib/module-theme.ts) so the report reads as "part of"
# the same module rather than a generic export.
ACCENT_COLOR = (37, 99, 235)
MUTED_TEXT = (110, 110, 110)
SUBTOTAL_FILL = (219, 234, 254)
ROW_FILL = (245, 247, 250)

# Line #, EPC, Serial Number, Manufacturer, Batch Number — sums to 190mm,
# the usable width of an A4 page with fpdf2's default 10mm margins.
COLUMN_WIDTHS = (15, 65, 35, 40, 35)

LABELS = {
    "nl": {
        "report_title": "Tag Scan Overzicht",
        "filename": "Bestandsnaam",
        "logged_at": "Geregistreerd op",
        "total_lines": "Totaal aantal regels",
        "product_heading": "Product: {product}",
        "subtotal": "Subtotaal: {count} regel(s)",
        "col_line": "Regel #",
        "col_epc": "EPC",
        "col_serial": "Serienummer",
        "col_manufacturer": "Fabrikant",
        "col_batch": "Batchnummer",
        "no_match_heading": "Geen match ({count})",
        "cancelled_heading": "Geannuleerd ({count})",
        "generated_at": "Gegenereerd op {timestamp}",
        "page": "Pagina {page}",
    },
    "en": {
        "report_title": "Tag Scan Summary",
        "filename": "Filename",
        "logged_at": "Logged At",
        "total_lines": "Total Lines",
        "product_heading": "Product: {product}",
        "subtotal": "Subtotal: {count} line(s)",
        "col_line": "Line #",
        "col_epc": "EPC",
        "col_serial": "Serial Number",
        "col_manufacturer": "Manufacturer",
        "col_batch": "Batch Number",
        "no_match_heading": "No match ({count})",
        "cancelled_heading": "Cancelled ({count})",
        "generated_at": "Generated on {timestamp}",
        "page": "Page {page}",
    },
}


class _SummaryPDF(FPDF):
    """Adds the page-number footer every page of the report shares."""

    def __init__(self, labels: dict[str, str]):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._labels = labels
        self.set_auto_page_break(auto=True, margin=20)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED_TEXT)
        self.cell(0, 10, self._labels["page"].format(page=self.page_no()), align="C")


def _render_product_group(pdf: FPDF, labels: dict[str, str], product: str, lines: list[TagLineData]) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*ACCENT_COLOR)
    pdf.cell(0, 9, labels["product_heading"].format(product=product), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(*ACCENT_COLOR)
    headers = (
        labels["col_line"],
        labels["col_epc"],
        labels["col_serial"],
        labels["col_manufacturer"],
        labels["col_batch"],
    )
    for width, label in zip(COLUMN_WIDTHS, headers):
        pdf.cell(width, 7, label, fill=True)
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 9)
    for index, line in enumerate(lines):
        pdf.set_text_color(0, 0, 0)
        values = (
            str(line.line_number),
            line.epc,
            line.assigned_serial_number or "",
            line.manufacturer or "",
            line.batch_number or "",
        )
        for width, value in zip(COLUMN_WIDTHS, values):
            pdf.cell(width, 6, value, fill=index % 2 == 1)
        pdf.ln(6)
        pdf.set_fill_color(*ROW_FILL)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*SUBTOTAL_FILL)
    pdf.set_text_color(*ACCENT_COLOR)
    pdf.cell(sum(COLUMN_WIDTHS), 7, labels["subtotal"].format(count=len(lines)), fill=True)
    pdf.ln(11)


def _render_simple_section(pdf: FPDF, labels: dict[str, str], heading_key: str, lines: list[TagLineData]) -> None:
    if not lines:
        return
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 8, labels[heading_key].format(count=len(lines)), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    for line in lines:
        # A plain hyphen, not an em dash: fpdf2's built-in core fonts only
        # support latin-1, which doesn't include "—" and would otherwise
        # raise FPDFUnicodeEncodingException for every line in this section.
        pdf.cell(0, 6, f"{labels['col_line']} {line.line_number} - {labels['col_epc']}: {line.epc}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def build_header_summary_pdf(db: Session, header: TagHeaderData, locale: str = "nl") -> bytes:
    """The full "beautiful layout" PDF for one scanned file: a title band,
    a short info block, one table + subtotal per matched product
    (alphabetical, for a stable/presentable report order), then any
    unmatched or cancelled lines in their own short sections.
    """
    labels = LABELS.get(locale, LABELS["nl"])

    lines = list_lines_for_header(db, header.id)

    grouped_by_product: dict[str, list[TagLineData]] = {}
    no_match_lines: list[TagLineData] = []
    cancelled_lines: list[TagLineData] = []
    for line in lines:
        if line.assigned_product_name is not None:
            grouped_by_product.setdefault(line.assigned_product_name, []).append(line)
        elif line.status == "cancelled":
            cancelled_lines.append(line)
        else:
            no_match_lines.append(line)

    pdf = _SummaryPDF(labels)
    pdf.add_page()

    # --- Title band ---
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(0, 0, pdf.w, 28, style="F")
    pdf.set_xy(0, 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, labels["report_title"], align="C")
    pdf.set_xy(pdf.l_margin, 34)

    # --- Info block ---
    pdf.set_text_color(0, 0, 0)
    for label_key, value in (
        ("filename", header.filename),
        ("logged_at", header.created_at.strftime("%Y-%m-%d %H:%M")),
        ("total_lines", str(header.line_count)),
    ):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 8, labels[label_key] + ":")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for product in sorted(grouped_by_product):
        pdf.set_fill_color(*ROW_FILL)
        _render_product_group(pdf, labels, product, grouped_by_product[product])

    _render_simple_section(pdf, labels, "no_match_heading", no_match_lines)
    _render_simple_section(pdf, labels, "cancelled_heading", cancelled_lines)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 6, labels["generated_at"].format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")))

    return bytes(pdf.output())
