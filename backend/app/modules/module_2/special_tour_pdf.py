# Builds the landscape "Leverplanning speciale levertoeren" PDF of KarTracker's
# "Speciale levertoeren-planning" screen: for the karren ticked on the screen,
# the tour's stops in order and the karren standing at each.
#
#   - one table: per stop (its number in this tour, the afleverlocatie and
#     zone on its first row) the karren with their team, transport type, the
#     selected tours passing by them, the delivery date and an empty
#     "Geleverd" box to tick off. No distributiepunten: the tour passes by the
#     karren, nothing is picked up;
#   - optionally a "Route" page: the ground plan with every stop as a numbered
#     badge (the same stop number as in the table, also for locations without
#     a position in "Leveringsvolgorde") and the dashed route 1 -> n.
#
# Same house style and map helpers as the Leverplanning PDF
# (delivery_planning_pdf.py: header/footer, ground-plan view and legend columns).

from fpdf import FPDF

from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.modules.module_2.delivery_planning_pdf import (
    ACCENT_COLOR,
    LOCATION_FILL,
    ROW_HEIGHT,
    ZEBRA_FILL,
    _ColumnWriter,
    _DeliveryPlanningPDF,
    _draw_map_view,
    _fit,
    _MapPoint,
    _project,
)
from app.modules.module_2.kar_moves_pdf import _badge
from app.schemas.kartracker import SpecialTourStop
from app.shared.pdf_common import BORDER_COLOR, MUTED_TEXT, TEXT_DARK, pdf_text

LABELS = {
    "nl": {
        "title": "Leverplanning speciale levertoeren",
        "subtitle": "{tours} · {festival} · {season} · {count} karren",
        "printed_on": "Afgedrukt op {date}",
        "printed_by": "afgedrukt door {name}",
        "page": "Pagina {page} / {pages}",
        "columns": [
            "Stop", "Afleverlocatie", "Zone", "Karnummer", "Ploeg",
            "Transporttype", "Levertoer", "Leverdatum", "Geleverd",
        ],
        "map_title": "Route",
        "map_subtitle": "De stops van de levertoer, in volgorde",
        "legend": "Legende",
        "legend_stop": "Stop (nummer in de toer)",
        "legend_route": "Route",
        "stops": "Stops",
        "outside_plan": "Buiten het grondplan:",
        "not_on_map": "Niet op de kaart (geen coördinaten):",
        "no_groundplan": "Geen grondplan voor deze locaties: enkel de stops.",
    },
    "en": {
        "title": "Special delivery tours planning",
        "subtitle": "{tours} · {festival} · {season} · {count} karren",
        "printed_on": "Printed on {date}",
        "printed_by": "printed by {name}",
        "page": "Page {page} / {pages}",
        "columns": [
            "Stop", "Delivery location", "Zone", "Kar number", "Team",
            "Transport type", "Delivery tour", "Delivery date", "Delivered",
        ],
        "map_title": "Route",
        "map_subtitle": "The tour's stops, in order",
        "legend": "Legend",
        "legend_stop": "Stop (number in the tour)",
        "legend_route": "Route",
        "stops": "Stops",
        "outside_plan": "Outside the ground plan:",
        "not_on_map": "Not on the map (no coordinates):",
        "no_groundplan": "No ground plan for these locations: stops only.",
    },
}

# Table column widths in mm (landscape A4 minus the margins = 273 mm) and
# their alignment, in the order of LABELS[...]["columns"]. A kar's team can be
# on several tours, so "Levertoer" gets plenty of room.
COLUMN_WIDTHS = (12, 50, 22, 22, 38, 28, 58, 23, 20)
COLUMN_ALIGN = ("C", "L", "L", "L", "L", "L", "L", "L", "C")


def _stop_label(stop: SpecialTourStop) -> str:
    """"Name - description" (just the name when there is no description)."""
    return f"{stop.name} — {stop.description}" if stop.description else stop.name


def _table_heading(pdf: FPDF, labels: dict) -> None:
    """The purple heading row of the table."""
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(pdf.l_margin)
    for heading, width, align in zip(labels["columns"], COLUMN_WIDTHS, COLUMN_ALIGN):
        pdf.cell(width, ROW_HEIGHT, _fit(pdf, heading, width), align=align, fill=True)
    pdf.ln(ROW_HEIGHT)


def _render_table(pdf: _DeliveryPlanningPDF, labels: dict, stops: list[SpecialTourStop]) -> None:
    """One table: the stops in order, each with its karren."""
    pdf.add_page()
    _table_heading(pdf, labels)
    for stop in stops:
        for index, kar in enumerate(stop.karren):
            # A new page repeats the table heading.
            if pdf.get_y() + ROW_HEIGHT > pdf.content_bottom:
                pdf.add_page()
                _table_heading(pdf, labels)

            # The stop's own cells only on its first kar, so each stop reads as one block.
            first = index == 0
            values = (
                str(stop.stop) if first else "",
                _stop_label(stop) if first else "",
                stop.zone_name if first else "",
                kar.kar_nummer,
                kar.team_name,
                kar.transport_type_name,
                ", ".join(kar.tour_names),
                kar.delivery_date.strftime("%d-%m-%Y") if kar.delivery_date else "",
                "",
            )
            top = pdf.get_y()
            # A thin rule above each new stop.
            if first:
                pdf.set_draw_color(*BORDER_COLOR)
                pdf.set_line_width(0.3)
                pdf.line(pdf.l_margin, top, pdf.l_margin + sum(COLUMN_WIDTHS), top)
            pdf.set_fill_color(*(LOCATION_FILL if first else ZEBRA_FILL))
            pdf.set_text_color(*TEXT_DARK)
            pdf.set_x(pdf.l_margin)
            for column, (value, width, align) in enumerate(zip(values, COLUMN_WIDTHS, COLUMN_ALIGN)):
                bold = first and column in (0, 1) or column == 3
                pdf.set_font("Helvetica", "B" if bold else "", 9 if column == 0 else 8.5)
                pdf.cell(width, ROW_HEIGHT, _fit(pdf, value, width), align=align, fill=True)
            # The empty box ticked when the kar has been served.
            box = 3.6
            box_x = pdf.l_margin + sum(COLUMN_WIDTHS[:-1]) + (COLUMN_WIDTHS[-1] - box) / 2
            pdf.set_draw_color(*TEXT_DARK)
            pdf.set_line_width(0.25)
            pdf.rect(box_x, top + (ROW_HEIGHT - box) / 2, box, box)
            pdf.ln(ROW_HEIGHT)


# --- Route map -----------------------------------------------------------------


def _render_map(
    pdf: _DeliveryPlanningPDF, labels: dict, stops: list[SpecialTourStop], groundplans: list[KarTrackerGroundplan]
) -> None:
    """The "Route" page: ground plan, the dashed route through the stops, a
    numbered badge per stop and a legend.
    """
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 7, pdf_text(labels["map_title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 5, pdf_text(labels["map_subtitle"]), new_x="LMARGIN", new_y="NEXT")

    # Every stop with coordinates becomes a point (in stop order); the rest is listed.
    points: list[_MapPoint] = []
    not_on_map: list[str] = []
    for stop in stops:
        if stop.latitude is None or stop.longitude is None:
            not_on_map.append(f"{stop.stop}. {stop.name}")
            continue
        x, y = _project(stop.latitude, stop.longitude)
        points.append(_MapPoint(x, y, str(stop.stop), "location"))

    # The map area on the left, the legend column on the right.
    area_x, area_y = pdf.l_margin, pdf.get_y() + 2
    legend_w = 72
    area_w = pdf.w - pdf.l_margin - pdf.r_margin - legend_w - 5
    area_h = pdf.content_bottom - area_y
    legend_x = area_x + area_w + 5

    to_page, plan, drawn, outside_plan = _draw_map_view(pdf, points, groundplans, area_x, area_y, area_w, area_h)

    # The route 1 -> n as a dashed purple line, then the badges on top.
    if len(drawn) > 1:
        pdf.set_draw_color(*ACCENT_COLOR)
        pdf.set_line_width(0.6)
        pdf.set_dash_pattern(dash=2, gap=1.4)
        pdf.polyline([to_page(point.x, point.y) for point in drawn])
        pdf.set_dash_pattern()
    for point in drawn:
        x, y = to_page(point.x, point.y)
        _badge(pdf, x, y, point.label, ACCENT_COLOR)

    _render_legend(pdf, labels, legend_x, area_y, legend_w, stops, plan is None, outside_plan, not_on_map)


def _render_legend(
    pdf: _DeliveryPlanningPDF,
    labels: dict,
    x: float,
    y: float,
    width: float,
    stops: list[SpecialTourStop],
    no_groundplan: bool,
    outside_plan: list[str],
    not_on_map: list[str],
) -> None:
    """The column right of the map: the symbols, every stop by number and
    what isn't on the map. Continues in columns on a new page when it doesn't fit.
    """
    # Symbols: drawn swatch + text.
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_xy(x, y)
    pdf.cell(width, 5.5, pdf_text(labels["legend"]))
    y += 5.5
    for kind, text in (("stop", labels["legend_stop"]), ("route", labels["legend_route"])):
        centre_y = y + 2
        if kind == "route":
            pdf.set_draw_color(*ACCENT_COLOR)
            pdf.set_line_width(0.6)
            pdf.set_dash_pattern(dash=2, gap=1.4)
            pdf.line(x, centre_y, x + 5, centre_y)
            pdf.set_dash_pattern()
        else:
            pdf.set_fill_color(*ACCENT_COLOR)
            pdf.circle(x + 2.5, centre_y, 1.8, style="F")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_xy(x + 7, y)
        pdf.cell(width - 7, 4, _fit(pdf, text, width - 7))
        y += 4.5

    writer = _ColumnWriter(pdf, x, y, width)
    if no_groundplan:
        writer.line(labels["no_groundplan"], muted=True)
    writer.gap(2)

    # Every stop: "number. description (zone)" (the name when there is no description).
    writer.line(labels["stops"], bold=True, size=9, height=5.5)
    for stop in stops:
        writer.line(f"{stop.stop}.  {stop.description or stop.name}  ({stop.zone_name})")

    # What couldn't be drawn.
    for heading, names in ((labels["outside_plan"], outside_plan), (labels["not_on_map"], not_on_map)):
        if names:
            writer.gap(2)
            writer.line(heading, bold=True)
            writer.paragraph(", ".join(names), muted=True)


def build_special_tour_pdf(
    stops: list[SpecialTourStop],
    *,
    season_name: str,
    festival_name: str,
    tour_names: list[str],
    include_map: bool,
    groundplans: list[KarTrackerGroundplan],
    printed_by: str | None,
    locale: str = "nl",
) -> bytes:
    """The landscape PDF for the given (already filtered) stops, optionally
    with the route map page.
    """
    labels = LABELS.get(locale, LABELS["nl"])
    total = sum(len(stop.karren) for stop in stops)
    subtitle = labels["subtitle"].format(
        tours=", ".join(tour_names), festival=festival_name, season=season_name, count=total
    )
    pdf = _DeliveryPlanningPDF(labels, subtitle=subtitle, printed_by=printed_by)
    _render_table(pdf, labels, stops)
    if include_map:
        _render_map(pdf, labels, stops, groundplans)
    return bytes(pdf.output())
