# Atelier's picklist (block 2): what to take from the store for one
# festival day. Page 1 = the store totals per article with the estimated
# sizes; then one block per chosen team (persons, articles x pieces and an
# empty box to tick off when the bundle is ready). Uses StockMaster's PDF
# house style (module_4/pdf_layout.py) in Atelier's own red.

from datetime import date

from app.modules.module_4.pdf_layout import (
    StockMasterPDF,
    data_table,
    finish,
    info_rows,
    muted_line,
    section_heading,
)
from app.schemas.atelier import PreparationResponse

# Atelier's accent (red-600, see frontend/src/lib/module-theme.ts).
ATELIER_RED = (220, 38, 38)

LABELS = {
    "nl": {
        "title": "Picklijst kledij",
        "subtitle": "{festival} · {day}",
        "printed_on": "Afgedrukt op {date}",
        "printed_by": "afgedrukt door {name}",
        "page": "Pagina {page} / {pages}",
        "festival": "Festival",
        "day": "Dag",
        "persons": "Personen",
        "pieces": "Stuks",
        "teams": "Ploegen",
        "totals": "Totaal uit de winkel",
        "article": "Artikel",
        "code": "Code",
        "total": "Totaal",
        "sizes": "Geschatte maten",
        "equal_split": "(gelijk verdeeld)",
        "per_team": "Per ploeg",
        "team_heading": "{team} · {persons} personen",
        "ready": "Klaar",
        "nothing": "Er zijn geen reservaties voor deze dag.",
        "no_package": "Ploegen met een reservatie maar zonder pakket: {teams}",
    },
    "en": {
        "title": "Clothing picklist",
        "subtitle": "{festival} · {day}",
        "printed_on": "Printed on {date}",
        "printed_by": "printed by {name}",
        "page": "Page {page} / {pages}",
        "festival": "Festival",
        "day": "Day",
        "persons": "Persons",
        "pieces": "Pieces",
        "teams": "Teams",
        "totals": "Total from the store",
        "article": "Article",
        "code": "Code",
        "total": "Total",
        "sizes": "Estimated sizes",
        "equal_split": "(equal split)",
        "per_team": "Per team",
        "team_heading": "{team} · {persons} persons",
        "ready": "Ready",
        "nothing": "There are no reservations for this day.",
        "no_package": "Teams with a reservation but without a package: {teams}",
    },
}

FIT_SHORT = {"nl": {"women": "D", "men": "H", "unisex": "U"}, "en": {"women": "W", "men": "M", "unisex": "U"}}


def build_picklist_pdf(preparation: PreparationResponse, day: date, locale: str, printed_by: str | None) -> bytes:
    """The picklist of one festival day, for the teams in `preparation`
    (build_preparation already narrowed it to the chosen teams)."""
    labels = LABELS.get(locale, LABELS["nl"])
    fits = FIT_SHORT.get(locale, FIT_SHORT["nl"])
    day_text = day.strftime("%d-%m-%Y")
    bundles = preparation.bundles

    pdf = StockMasterPDF(
        labels,
        title=labels["title"],
        subtitle=labels["subtitle"].format(festival=preparation.festival.name, day=day_text),
        doc_number=None,
        printed_by=printed_by,
        accent_color=ATELIER_RED,
        brand="Atelier",
    )

    info_rows(
        pdf,
        [
            (labels["festival"], preparation.festival.name),
            (labels["day"], day_text),
            (labels["teams"], len(bundles)),
            (labels["persons"], preparation.persons_per_day),
            (labels["pieces"], preparation.pieces_per_day),
        ],
    )

    section_heading(pdf, labels["totals"])
    if not bundles:
        muted_line(pdf, labels["nothing"])
    else:
        rows = []
        for need in preparation.articles:
            # e.g. "S/U 3  M/U 5  L/U 4"; sizes with 0 pieces are left out.
            sizes = "  ".join(
                f"{size.size_name}/{fits[size.fit]} {size.quantity}" for size in need.sizes if size.quantity
            )
            if need.equal_split and sizes:
                sizes += f" {labels['equal_split']}"
            rows.append([need.article_name, need.article_code, need.quantity, sizes])
        data_table(
            pdf,
            [labels["article"], labels["code"], labels["total"], labels["sizes"]],
            rows,
            col_widths=(62, 34, 18, 68),
            align=("L", "L", "R", "L"),
        )

    if preparation.teams_without_package:
        muted_line(pdf, labels["no_package"].format(teams=", ".join(preparation.teams_without_package)))

    if bundles:
        section_heading(pdf, labels["per_team"])
        for bundle in bundles:
            section_heading(pdf, labels["team_heading"].format(team=bundle.team_name, persons=bundle.persons))
            data_table(
                pdf,
                [labels["article"], labels["pieces"], labels["ready"]],
                [[line.article_name, line.quantity, "[   ]"] for line in bundle.lines],
                col_widths=(120, 30, 32),
                align=("L", "R", "C"),
            )
    return finish(pdf)
