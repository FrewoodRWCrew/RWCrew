# Builds the printable "delivery note" PDF for one Intervention Request —
# the association-facing document handed to whoever picks up/drops off
# whatever the request was about: which team it's for, where to deliver,
# what's being asked, and who to contact. Deliberately leaves out
# internal/operational fields (status, who's handling it, which internal
# cart) that don't matter to the association reading a printed copy.
#
# Uses fpdf2 — pure Python, no C/Rust toolchain required (matches the
# reason pg8000/openpyxl were chosen over compiled alternatives — see
# CLAUDE.md's Python 3.14 gotcha), the same library and styling
# conventions as app/modules/module_1/tag_header_pdf.py.

from pathlib import Path

from fpdf import FPDF

from app.db.models.intervention_request import InterventionRequest

# The event this delivery note is printed for — fixed text rather than
# looked up from MasterData_festival, since Intervention Requests aren't
# linked to a specific festival record. Update this by hand when the
# event/year changes.
DOCUMENT_TITLE = "Rock Werchter 2026"

# Module 3's own accent colour (frontend/src/lib/module-theme.ts's
# "orange-600"), reused here the same way tag_header_pdf.py uses TagScan's
# blue — so this report reads as "part of" Intervention Requests rather
# than a generic export.
ACCENT_COLOR = (234, 88, 12)
TEXT_DARK = (31, 41, 55)
MUTED_TEXT = (107, 114, 128)
BORDER_COLOR = (223, 226, 230)

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
TEAMKAR_LOGO = ASSETS_DIR / "teamkar-logo.png"
ALTSIEN_LOGO = ASSETS_DIR / "altsien-logo.png"
LIVENATION_LOGO = ASSETS_DIR / "livenation-logo.jpg"

# Each logo's own width:height ratio, so a shared footer height (see
# _render_footer_logos) still lines them up evenly despite each source
# image having a different shape.
_LOGOS = (
    (TEAMKAR_LOGO, 1536 / 1024),
    (ALTSIEN_LOGO, 352 / 416),
    (LIVENATION_LOGO, 200 / 200),
)

LABELS = {
    "nl": {
        "document_subtitle": "Interventieaanvraag {request_number}",
        "info_heading": "Info",
        "association_label": "Vereniging",
        "cart_number_label": "Kar Nr",
        "delivery_location_label": "Afleverplaats",
        "zone_label": "Afleverzone",
        "question_heading": "Vraag / Opmerking",
        "question_label": "Vraag",
        "preferred_delivery_label": "Voorkeur moment van levering",
        "employee_heading": "Medewerker Vereniging",
        "employee_name_label": "Naam Medewerker",
        "employee_phone_label": "Mobiel Nummer Medewerker",
        "not_specified": "Niet opgegeven",
    },
    "en": {
        "document_subtitle": "Intervention Request {request_number}",
        "info_heading": "Info",
        "association_label": "Association",
        "cart_number_label": "Cart No.",
        "delivery_location_label": "Delivery Location",
        "zone_label": "Delivery Zone",
        "question_heading": "Question / Remark",
        "question_label": "Question",
        "preferred_delivery_label": "Preferred Delivery Time",
        "employee_heading": "Association Contact",
        "employee_name_label": "Contact Name",
        "employee_phone_label": "Contact Mobile Number",
        "not_specified": "Not specified",
    },
}


class _DeliveryNotePDF(FPDF):
    """Adds the footer logo band every page of the note shares — in
    practice always exactly one page, but kept as a page-level footer
    (rather than drawn once at the end) so the layout still holds up if a
    very long question ever pushes the note onto a second page.
    """

    def footer(self) -> None:
        logo_height = 18
        gap = 12
        widths = [logo_height * ratio for _, ratio in _LOGOS]
        total_width = sum(widths) + gap * (len(_LOGOS) - 1)

        self.set_draw_color(*BORDER_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.h - 30, self.w - self.r_margin, self.h - 30)

        x = (self.w - total_width) / 2
        y = self.h - 26
        for (path, _ratio), width in zip(_LOGOS, widths):
            if path.exists():
                self.image(str(path), x=x, y=y, h=logo_height)
            x += width + gap


def _format_datetime(value) -> str:
    """dd-mm-yyyy HH:mm — this app's established deterministic date format
    (see formatDateTime in intervention-requests-management.tsx), not a
    raw str(datetime) dump.
    """
    return value.strftime("%d-%m-%Y %H:%M") if value is not None else None


def _render_field(pdf: FPDF, label: str, value: str | None, labels: dict[str, str]) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(55, 7, f"{label}:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(0, 7, value or labels["not_specified"], new_x="LMARGIN", new_y="NEXT")


def _render_section(pdf: FPDF, heading: str, fields: list[tuple[str, str | None]], labels: dict[str, str]) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 9, heading, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*ACCENT_COLOR)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 40, pdf.get_y())
    pdf.ln(4)

    for label, value in fields:
        _render_field(pdf, label, value, labels)
    pdf.ln(4)


def build_delivery_note_pdf(request: InterventionRequest, team_name: str, locale: str = "nl") -> bytes:
    """The printable delivery note for one intervention request: a title,
    an "Info" block, the question itself plus preferred delivery time, the
    association contact's details, and the TeamKar/Altsien/Live Nation
    logos in the footer.
    """
    labels = LABELS.get(locale, LABELS["nl"])

    pdf = _DeliveryNotePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=35)
    pdf.add_page()

    # --- Title ---
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(0, 0, pdf.w, 2.5, style="F")
    pdf.set_xy(pdf.l_margin, 14)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, DOCUMENT_TITLE, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 8, labels["document_subtitle"].format(request_number=request.request_number), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y() + 3, pdf.w - pdf.r_margin, pdf.get_y() + 3)
    pdf.set_y(pdf.get_y() + 12)

    _render_section(
        pdf,
        labels["info_heading"],
        [
            (labels["association_label"], team_name),
            (labels["cart_number_label"], request.cart_number),
            (labels["delivery_location_label"], request.delivery_location),
            (labels["zone_label"], request.zone),
        ],
        labels,
    )

    _render_section(
        pdf,
        labels["question_heading"],
        [
            (labels["question_label"], request.question),
            (labels["preferred_delivery_label"], _format_datetime(request.preferred_delivery_at)),
        ],
        labels,
    )

    _render_section(
        pdf,
        labels["employee_heading"],
        [
            (labels["employee_name_label"], request.employee_name),
            (labels["employee_phone_label"], request.employee_phone),
        ],
        labels,
    )

    return bytes(pdf.output())
