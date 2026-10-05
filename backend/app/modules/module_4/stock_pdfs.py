# StockMaster's printable documents, all in the shared house style of
# pdf_layout.py (TeamKar logo, teal tables, footer with who printed it):
#   - Laadlijst per kar   what to load in a kar, sorted by bin (picking route)
#   - Vertrekbon          what left with a kar ("Kar vertrekt"), with an empty
#                         "terug" column to check on "Kar terug"
#   - Bestellijst         what to order for the season ("Te bestellen")
#   - Telblad             what to count, with an empty "geteld" column
#   - Boekingsbon         any booking with its lines (stamped when undone)

from datetime import datetime

from fpdf import FPDF

from app.core.timezone import to_belgian
from app.modules.module_4.pdf_layout import (
    ACCENT_COLOR,
    MUTED_TEXT,
    WARNING_COLOR,
    StockMasterPDF,
    data_table,
    draw_qr,
    finish,
    info_rows,
    muted_line,
    pdf_text,
    section_heading,
    signature_boxes,
)
from app.schemas.stockmaster import CountSheetLine, DocumentResponse, KarDetailResponse, OrderNeedResponse

LABELS = {
    "nl": {
        "printed_on": "Afgedrukt op {date}",
        "printed_by": "afgedrukt door {name}",
        "page": "Pagina {page} / {pages}",
        "sign_name": "Naam",
        "sign_date": "Datum",
        "sign_signature": "Handtekening",
        "kar": "Kar",
        "team": "Ploeg",
        "festival": "Festival",
        "season": "Seizoen",
        "warehouse": "Magazijn",
        "bins": "Locaties",
        "date": "Datum",
        "user": "Gebruiker",
        "reference": "Referentie",
        "reason": "Reden",
        "comment": "Opmerking",
        "status": "Status",
        "action": "Actie",
        "from_kar": "Van kar",
        "product": "Product",
        "bin": "Locatie",
        "category": "Categorie",
        "quantity": "Aantal",
        "total": "Totaal",
        "check": "OK",
        "no_team": "Geen ploeg",
        "all": "Alle",
        # Laadlijst
        "load_title": "Laadlijst",
        "load_subtitle": "Kar {kar} · seizoen {season}",
        "needed": "Nodig",
        "in_kar": "In kar",
        "to_load": "Te laden",
        "free": "Vrij",
        "no_needs": "Voor deze kar zijn er dit seizoen geen benodigdheden opgegeven.",
        "loaded_by": "Geladen door",
        "short_note": "Niet genoeg vrije voorraad om alles te laden voor: {products}",
        # Vertrekbon
        "dispatch_title": "Vertrekbon",
        "dispatch_subtitle": "Kar {kar} · {team}",
        "departed": "Vertrokken op",
        "returned_col": "Terug",
        "empty_kar": "De kar vertrok leeg.",
        "sign_warehouse": "Magazijn",
        "sign_team": "Ploeg",
        # Bestellijst
        "order_title": "Bestellijst",
        "order_subtitle": "Seizoen {season}",
        "in_stock": "In voorraad",
        "to_order": "Te bestellen",
        "ordered": "Besteld",
        "no_order": "Er hoeft niets besteld te worden: de voorraad dekt alle benodigdheden.",
        "no_warehouse": "Zonder magazijn",
        "filters": "Filters",
        # Telblad
        "count_title": "Telblad",
        "count_subtitle_kar": "Kar {kar}",
        "count_subtitle_free": "Vrije voorraad · {warehouse}",
        "expected": "Verwacht",
        "counted": "Geteld",
        "no_count_lines": "Er zijn geen producten om te tellen.",
        "counted_by": "Geteld door",
        # Boekingsbon
        "booking_title": "Boekingsbon",
        "from": "Van",
        "to": "Naar",
        "bucket_free": "Vrije voorraad",
        "bucket_external": "Extern",
        "bucket_kar": "Kar {kar}",
        "reversed_stamp": "ONGEDAAN GEMAAKT",
        "reversed_by": "Ongedaan gemaakt door {number}",
        "reversal_of": "Maakt {number} ongedaan",
        "status_posted": "Geboekt",
        "status_reversed": "Ongedaan gemaakt",
        "doc_types": {
            "book_in": "Inboeken",
            "kar_load": "Kar laden",
            "book_out": "Uitboeken",
            "kar_dispatch": "Kar vertrekt",
            "kar_return": "Kar terug",
            "kar_unload": "Kar uitladen",
            "count": "Telling",
            "reversal": "Ongedaan maken",
        },
    },
    "en": {
        "printed_on": "Printed on {date}",
        "printed_by": "printed by {name}",
        "page": "Page {page} / {pages}",
        "sign_name": "Name",
        "sign_date": "Date",
        "sign_signature": "Signature",
        "kar": "Cart",
        "team": "Team",
        "festival": "Festival",
        "season": "Season",
        "warehouse": "Warehouse",
        "bins": "Locations",
        "date": "Date",
        "user": "User",
        "reference": "Reference",
        "reason": "Reason",
        "comment": "Comment",
        "status": "Status",
        "action": "Action",
        "from_kar": "From cart",
        "product": "Product",
        "bin": "Location",
        "category": "Category",
        "quantity": "Quantity",
        "total": "Total",
        "check": "OK",
        "no_team": "No team",
        "all": "All",
        "load_title": "Load list",
        "load_subtitle": "Cart {kar} · season {season}",
        "needed": "Needed",
        "in_kar": "In cart",
        "to_load": "To load",
        "free": "Free",
        "no_needs": "No needs have been entered for this cart this season.",
        "loaded_by": "Loaded by",
        "short_note": "Not enough free stock to load everything for: {products}",
        "dispatch_title": "Departure note",
        "dispatch_subtitle": "Cart {kar} · {team}",
        "departed": "Departed on",
        "returned_col": "Back",
        "empty_kar": "The cart left empty.",
        "sign_warehouse": "Warehouse",
        "sign_team": "Team",
        "order_title": "Order list",
        "order_subtitle": "Season {season}",
        "in_stock": "In stock",
        "to_order": "To order",
        "ordered": "Ordered",
        "no_order": "Nothing needs to be ordered: the stock covers all needs.",
        "no_warehouse": "No warehouse",
        "filters": "Filters",
        "count_title": "Count sheet",
        "count_subtitle_kar": "Cart {kar}",
        "count_subtitle_free": "Free stock · {warehouse}",
        "expected": "Expected",
        "counted": "Counted",
        "no_count_lines": "There are no products to count.",
        "counted_by": "Counted by",
        "booking_title": "Booking note",
        "from": "From",
        "to": "To",
        "bucket_free": "Free stock",
        "bucket_external": "External",
        "bucket_kar": "Cart {kar}",
        "reversed_stamp": "UNDONE",
        "reversed_by": "Undone by {number}",
        "reversal_of": "Undoes {number}",
        "status_posted": "Booked",
        "status_reversed": "Undone",
        "doc_types": {
            "book_in": "Book in",
            "kar_load": "Load cart",
            "book_out": "Book out",
            "kar_dispatch": "Cart leaves",
            "kar_return": "Cart returns",
            "kar_unload": "Unload cart",
            "count": "Stock count",
            "reversal": "Undo",
        },
    },
}


def _labels(locale: str) -> dict:
    """The texts for the requested language (Dutch by default)."""
    return LABELS.get(locale, LABELS["nl"])


def _format_moment(value: datetime) -> str:
    """dd-mm-yyyy hh:mm in Belgian time."""
    return to_belgian(value).strftime("%d-%m-%Y %H:%M")


def _qr_block(pdf: FPDF, kar_nummer: str) -> None:
    """The kar number as a QR code at the top right of the content, with
    the number printed under it (the same QR content as the Karblad).
    """
    size = 24
    x = pdf.w - pdf.r_margin - size
    y = pdf.get_y()
    draw_qr(pdf, kar_nummer, x, y, size)
    pdf.set_xy(x, y + size)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ACCENT_COLOR)
    pdf.cell(size, 4, pdf_text(kar_nummer), align="C")
    pdf.set_xy(pdf.l_margin, y)


# --- Laadlijst per kar -----------------------------------------------------


def build_load_list_pdf(
    detail: KarDetailResponse, season_name: str, locale: str, printed_by: str | None
) -> bytes:
    """What to load in one kar: per needed product the needed quantity,
    what's already in it and what's still to load, sorted by bin so the
    picker walks the warehouse once.
    """
    labels = _labels(locale)
    kar = detail.kar
    pdf = StockMasterPDF(
        labels,
        title=labels["load_title"],
        subtitle=labels["load_subtitle"].format(kar=kar.kar_nummer, season=season_name),
        doc_number=kar.kar_nummer,
        printed_by=printed_by,
    )
    top = pdf.get_y()
    _qr_block(pdf, kar.kar_nummer)
    info_rows(
        pdf,
        [
            (labels["kar"], kar.kar_nummer),
            (labels["team"], kar.team_name or labels["no_team"]),
            (labels["season"], season_name),
            (labels["needed"], f"{kar.loaded_toward_required} / {kar.required_total}"),
        ],
    )
    pdf.set_y(max(pdf.get_y(), top + 30))

    needed_lines = [line for line in detail.lines if line.required > 0]
    if not needed_lines:
        muted_line(pdf, labels["no_needs"])
    else:
        needed_lines.sort(key=lambda line: ((line.bin_label or "~").lower(), line.name.lower()))
        rows = [
            [line.name, line.bin_label or "", line.required, line.in_kar, line.missing or "", line.free_available, ""]
            for line in needed_lines
        ]
        data_table(
            pdf,
            [labels["product"], labels["bin"], labels["needed"], labels["in_kar"], labels["to_load"], labels["free"], labels["check"]],
            rows,
            [58, 40, 18, 18, 20, 16, 12],
            ["L", "L", "R", "R", "R", "R", "C"],
            total_row=[
                labels["total"],
                "",
                sum(line.required for line in needed_lines),
                sum(line.in_kar for line in needed_lines),
                sum(line.missing for line in needed_lines),
                "",
                "",
            ],
        )
        if any(line.missing > line.free_available for line in needed_lines):
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*WARNING_COLOR)
            short = ", ".join(line.name for line in needed_lines if line.missing > line.free_available)
            pdf.multi_cell(0, 5, pdf_text(labels["short_note"].format(products=short)), new_x="LMARGIN", new_y="NEXT")
    signature_boxes(pdf, [labels["loaded_by"]], labels)
    return finish(pdf)


# --- Vertrekbon --------------------------------------------------------------


def build_dispatch_pdf(document: DocumentResponse, locale: str, printed_by: str | None) -> bytes:
    """What left with a kar, with an empty "terug" column to tick off on
    its return, and signature boxes for the warehouse and the team.
    """
    labels = _labels(locale)
    kar_nummer = document.kar_nummer or ""
    pdf = StockMasterPDF(
        labels,
        title=labels["dispatch_title"],
        subtitle=labels["dispatch_subtitle"].format(kar=kar_nummer, team=document.team_name or labels["no_team"]),
        doc_number=document.doc_number,
        printed_by=printed_by,
    )
    top = pdf.get_y()
    if kar_nummer:
        _qr_block(pdf, kar_nummer)
    info_rows(
        pdf,
        [
            (labels["kar"], kar_nummer),
            (labels["team"], document.team_name),
            (labels["festival"], document.festival_name),
            (labels["season"], document.season_name),
            (labels["departed"], _format_moment(document.created_at)),
            (labels["user"], document.created_by_name),
            (labels["reference"], document.reference),
            (labels["comment"], document.comment),
        ],
    )
    pdf.set_y(max(pdf.get_y(), top + 30))
    _reversed_notice(pdf, document, labels)

    if not document.lines:
        muted_line(pdf, labels["empty_kar"])
    else:
        data_table(
            pdf,
            [labels["product"], labels["quantity"], labels["returned_col"]],
            [[line.product_name, line.quantity, ""] for line in document.lines],
            [120, 30, 32],
            ["L", "R", "C"],
            total_row=[labels["total"], document.total_quantity, ""],
        )
    signature_boxes(pdf, [labels["sign_warehouse"], labels["sign_team"]], labels)
    return finish(pdf)


# --- Bestellijst -------------------------------------------------------------


def build_order_list_pdf(
    lines: list[OrderNeedResponse], season_name: str, filters_text: str | None, locale: str, printed_by: str | None
) -> bytes:
    """What to order for the season, grouped per warehouse, with an empty
    "besteld" column to note what was actually ordered.
    """
    labels = _labels(locale)
    pdf = StockMasterPDF(
        labels,
        title=labels["order_title"],
        subtitle=labels["order_subtitle"].format(season=season_name),
        doc_number=None,
        printed_by=printed_by,
    )
    info_rows(pdf, [(labels["season"], season_name), (labels["filters"], filters_text)])

    to_order = [line for line in lines if line.to_order > 0]
    if not to_order:
        muted_line(pdf, labels["no_order"])
        return finish(pdf)

    # One table per warehouse.
    groups: dict[str, list[OrderNeedResponse]] = {}
    for line in to_order:
        groups.setdefault(line.warehouse_name or labels["no_warehouse"], []).append(line)
    for warehouse_name, group in groups.items():
        section_heading(pdf, warehouse_name)
        group.sort(key=lambda line: ((line.category_name or "~").lower(), line.name.lower()))
        data_table(
            pdf,
            [labels["product"], labels["category"], labels["needed"], labels["in_stock"], labels["to_order"], labels["ordered"]],
            [
                [line.name, line.category_name or "", line.needed, line.in_stock, line.to_order, ""]
                for line in group
            ],
            [62, 36, 20, 22, 24, 18],
            ["L", "L", "R", "R", "R", "C"],
            total_row=[labels["total"], "", "", "", sum(line.to_order for line in group), ""],
        )
    return finish(pdf)


# --- Telblad -----------------------------------------------------------------


def build_count_sheet_pdf(
    lines: list[CountSheetLine],
    *,
    kar_nummer: str | None,
    warehouse_name: str | None,
    bin_range: str | None,
    season_name: str | None,
    locale: str,
    printed_by: str | None,
) -> bytes:
    """What to count, sorted by bin, with an empty "geteld" column."""
    labels = _labels(locale)
    subtitle = (
        labels["count_subtitle_kar"].format(kar=kar_nummer)
        if kar_nummer
        else labels["count_subtitle_free"].format(warehouse=warehouse_name or labels["all"])
    )
    pdf = StockMasterPDF(
        labels, title=labels["count_title"], subtitle=subtitle, doc_number=kar_nummer, printed_by=printed_by
    )
    top = pdf.get_y()
    if kar_nummer:
        _qr_block(pdf, kar_nummer)
    info_rows(
        pdf,
        [
            (labels["kar"], kar_nummer),
            (labels["warehouse"], None if kar_nummer else (warehouse_name or labels["all"])),
            (labels["bins"], bin_range),
            (labels["season"], season_name),
        ],
    )
    if kar_nummer:
        pdf.set_y(max(pdf.get_y(), top + 30))

    if not lines:
        muted_line(pdf, labels["no_count_lines"])
    else:
        data_table(
            pdf,
            [labels["product"], labels["bin"], labels["expected"], labels["counted"]],
            [[line.name, line.bin_label or "", line.expected, ""] for line in lines],
            [78, 52, 24, 28],
            ["L", "L", "R", "C"],
        )
    signature_boxes(pdf, [labels["counted_by"]], labels)
    return finish(pdf)


# --- Boekingsbon -------------------------------------------------------------


def _bucket_text(bucket: str, kar_nummer: str | None, labels: dict) -> str:
    """How a place reads on paper."""
    if bucket == "free":
        return labels["bucket_free"]
    if bucket == "kar":
        return labels["bucket_kar"].format(kar=kar_nummer or "?")
    return labels["bucket_external"]


def _reversed_notice(pdf: FPDF, document: DocumentResponse, labels: dict) -> None:
    """A red "UNDONE" stamp for a booking that was reversed."""
    if document.status != "reversed":
        return
    y = pdf.get_y()
    pdf.set_draw_color(220, 38, 38)
    pdf.set_text_color(220, 38, 38)
    pdf.set_line_width(0.8)
    pdf.set_font("Helvetica", "B", 16)
    text = labels["reversed_stamp"]
    width = pdf.get_string_width(text) + 10
    x = pdf.w - pdf.r_margin - width - 4
    with pdf.rotation(angle=8, x=x + width / 2, y=y + 6):
        pdf.rect(x, y, width, 11)
        pdf.set_xy(x, y + 1.5)
        pdf.cell(width, 8, pdf_text(text), align="C")
    if document.reversed_by_number:
        pdf.set_xy(pdf.l_margin, y + 2)
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.cell(0, 6, pdf_text(labels["reversed_by"].format(number=document.reversed_by_number)))
    pdf.set_y(y + 20)
    pdf.set_text_color(*MUTED_TEXT)


def build_booking_pdf(document: DocumentResponse, locale: str, printed_by: str | None) -> bytes:
    """Any booking: who did what when, and every line from → to."""
    labels = _labels(locale)
    action = labels["doc_types"].get(document.doc_type, document.doc_type)
    subtitle_parts = [action]
    if document.kar_nummer:
        subtitle_parts.append(labels["bucket_kar"].format(kar=document.kar_nummer))
    pdf = StockMasterPDF(
        labels,
        title=labels["booking_title"],
        subtitle=" · ".join(subtitle_parts),
        doc_number=document.doc_number,
        printed_by=printed_by,
    )
    info_rows(
        pdf,
        [
            (labels["action"], action),
            (labels["date"], _format_moment(document.created_at)),
            (labels["user"], document.created_by_name),
            (labels["season"], document.season_name),
            (labels["kar"], document.kar_nummer),
            (labels["from_kar"], document.from_kar_nummer),
            (labels["team"], document.team_name),
            (labels["festival"], document.festival_name),
            (labels["reference"], document.reference),
            (labels["reason"], document.reason_name),
            (labels["comment"], document.comment),
            (
                labels["status"],
                labels["reversal_of"].format(number=document.reversal_of_number)
                if document.reversal_of_number
                else labels["status_reversed" if document.status == "reversed" else "status_posted"],
            ),
        ],
    )
    _reversed_notice(pdf, document, labels)
    data_table(
        pdf,
        [labels["product"], labels["from"], labels["to"], labels["quantity"]],
        [
            [
                line.product_name,
                _bucket_text(line.from_bucket, line.from_kar_nummer, labels),
                _bucket_text(line.to_bucket, line.to_kar_nummer, labels),
                line.quantity,
            ]
            for line in document.lines
        ],
        [76, 42, 42, 22],
        ["L", "L", "L", "R"],
        total_row=[labels["total"], "", "", document.total_quantity],
    )
    return finish(pdf)
