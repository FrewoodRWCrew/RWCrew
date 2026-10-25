# Atelier's stock PDFs (block 3), in StockMaster's house style
# (module_4/pdf_layout.py) in Atelier's own red:
#   - Boekingsbon: one stock booking with its lines;
#   - Bestellijst: the "Te bestellen" lines of a season, per article.

from app.core.timezone import to_belgian
from app.modules.module_4.pdf_layout import (
    StockMasterPDF,
    data_table,
    finish,
    info_rows,
    muted_line,
    section_heading,
)
from app.modules.module_5.picklist_pdf import ATELIER_RED
from app.schemas.atelier import OrderNeedLine, StockDocumentResponse

LABELS = {
    "nl": {
        "printed_on": "Afgedrukt op {date}",
        "printed_by": "afgedrukt door {name}",
        "page": "Pagina {page} / {pages}",
        "booking_title": "Boekingsbon kledij",
        "order_title": "Bestellijst kledij",
        "order_subtitle": "Seizoen {season}",
        "type": "Soort",
        "date": "Datum",
        "by": "Geboekt door",
        "reference": "Referentie",
        "reason": "Reden",
        "note": "Opmerking",
        "status": "Status",
        "reversal_of": "Maakt ongedaan",
        "reversed_by": "Ongedaan gemaakt door {number}",
        "lines": "Lijnen",
        "article": "Artikel",
        "size": "Maat",
        "from": "Van",
        "to": "Naar",
        "quantity": "Aantal",
        "total": "Totaal",
        "needed": "Nodig per dag",
        "festival": "Festival",
        "owned": "In bezit",
        "to_order": "Te bestellen",
        "nothing_to_order": "Niets te bestellen: de voorraad dekt de hoogste dagbehoefte van elk festival.",
        "outside": "Buiten",
        "doc_types": {
            "receipt": "Ontvangst", "washed": "Gewassen", "write_off": "Afboeken", "count": "Telling",
            "reversal": "Ongedaan maken",
        },
        "statuses": {"available": "Beschikbaar", "to_wash": "Te wassen", "handed_out": "Uitgegeven"},
        "reasons": {"damaged": "Beschadigd", "lost": "Verloren", "not_returned": "Niet teruggebracht", "other": "Andere"},
        "doc_status": {"posted": "Geboekt", "reversed": "Ongedaan gemaakt"},
        "fits": {"women": "Dames", "men": "Heren", "unisex": "Unisex"},
    },
    "en": {
        "printed_on": "Printed on {date}",
        "printed_by": "printed by {name}",
        "page": "Page {page} / {pages}",
        "booking_title": "Clothing booking note",
        "order_title": "Clothing order list",
        "order_subtitle": "Season {season}",
        "type": "Type",
        "date": "Date",
        "by": "Booked by",
        "reference": "Reference",
        "reason": "Reason",
        "note": "Note",
        "status": "Status",
        "reversal_of": "Undoes",
        "reversed_by": "Undone by {number}",
        "lines": "Lines",
        "article": "Article",
        "size": "Size",
        "from": "From",
        "to": "To",
        "quantity": "Quantity",
        "total": "Total",
        "needed": "Needed per day",
        "festival": "Festival",
        "owned": "Owned",
        "to_order": "To order",
        "nothing_to_order": "Nothing to order: the stock covers every festival's highest day need.",
        "outside": "Outside",
        "doc_types": {
            "receipt": "Receipt", "washed": "Washed", "write_off": "Write-off", "count": "Stock count",
            "reversal": "Undo",
        },
        "statuses": {"available": "Available", "to_wash": "To wash", "handed_out": "Handed out"},
        "reasons": {"damaged": "Damaged", "lost": "Lost", "not_returned": "Not returned", "other": "Other"},
        "doc_status": {"posted": "Booked", "reversed": "Undone"},
        "fits": {"women": "Women", "men": "Men", "unisex": "Unisex"},
    },
}


def _labels(locale: str) -> dict:
    """The texts for the requested language (Dutch by default)."""
    return LABELS.get(locale, LABELS["nl"])


def build_booking_pdf(document: StockDocumentResponse, locale: str, printed_by: str | None) -> bytes:
    """One booking with its lines."""
    labels = _labels(locale)
    doc_type = labels["doc_types"].get(document.doc_type, document.doc_type)
    pdf = StockMasterPDF(
        labels,
        title=labels["booking_title"],
        subtitle=doc_type,
        doc_number=document.doc_number,
        printed_by=printed_by,
        accent_color=ATELIER_RED,
        brand="Atelier",
    )
    status = labels["doc_status"].get(document.status, document.status)
    if document.reversed_by_number:
        status += " · " + labels["reversed_by"].format(number=document.reversed_by_number)
    info_rows(
        pdf,
        [
            (labels["type"], doc_type),
            (labels["date"], to_belgian(document.created_at).strftime("%d-%m-%Y %H:%M")),
            (labels["by"], document.created_by_name),
            (labels["reference"], document.reference),
            (labels["reason"], labels["reasons"].get(document.reason) if document.reason else None),
            (labels["status"], status),
            (labels["reversal_of"], document.reversal_of_number),
            (labels["note"], document.note),
        ],
    )
    section_heading(pdf, labels["lines"])

    def place(status: str | None) -> str:
        return labels["statuses"].get(status, status) if status else labels["outside"]

    data_table(
        pdf,
        [labels["article"], labels["size"], labels["from"], labels["to"], labels["quantity"]],
        [
            [move.article_name, f"{move.size_name} · {labels['fits'][move.fit]}", place(move.from_status), place(move.to_status), move.quantity]
            for move in document.movements
        ],
        col_widths=(62, 34, 30, 30, 26),
        align=("L", "L", "L", "L", "R"),
        total_row=[labels["total"], "", "", "", document.total_quantity],
    )
    return finish(pdf)


def build_order_list_pdf(lines: list[OrderNeedLine], season_name: str, locale: str, printed_by: str | None) -> bytes:
    """The Te bestellen list of a season."""
    labels = _labels(locale)
    pdf = StockMasterPDF(
        labels,
        title=labels["order_title"],
        subtitle=labels["order_subtitle"].format(season=season_name),
        doc_number=None,
        printed_by=printed_by,
        accent_color=ATELIER_RED,
        brand="Atelier",
    )
    if not lines:
        muted_line(pdf, labels["nothing_to_order"])
        return finish(pdf)
    data_table(
        pdf,
        [labels["article"], labels["size"], labels["needed"], labels["festival"], labels["owned"], labels["to_order"]],
        [
            [
                f"{line.article_name} ({line.article_code})",
                f"{line.size_name} · {labels['fits'][line.fit]}",
                line.needed,
                line.festival_name,
                line.owned,
                line.to_order,
            ]
            for line in lines
        ],
        col_widths=(56, 26, 22, 38, 18, 22),
        align=("L", "L", "R", "L", "R", "R"),
        total_row=[labels["total"], "", "", "", "", sum(line.to_order for line in lines)],
    )
    return finish(pdf)
