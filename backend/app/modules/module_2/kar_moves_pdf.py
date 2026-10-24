# Builds the landscape "Verplaatsingen" PDF of KarTracker's "Verplaatsingen
# tussen festivals" screen: for the karren ticked on the screen, where the
# driver picks each kar up (its afleverlocatie at the "Van" festival) and
# where it has to go (its afleverlocatie at the "Naar" festival).
#
#   - one section per pick-up location ("Ophalen bij: 3 · Poort"), in the
#     order of the delivery tour, with its karren, their destination and an
#     empty "Verplaatst" box per kar to tick off;
#   - optionally a map page: the ground plan with every location involved
#     (purple = pick-up, green = destination only) and an arrow per move with
#     its number of karren.
#
# Same house style and map helpers as the Leverplanning PDF
# (delivery_planning_pdf.py: header/footer, ground-plan view and legend columns).

import math

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
from app.schemas.kartracker import KarMovesLocation, KarMovesLocationGroup
from app.shared.pdf_common import MUTED_TEXT, TEXT_DARK, pdf_text

# Green (green-600) for a location that only receives karren.
DESTINATION_COLOR = (22, 163, 74)

LABELS = {
    "nl": {
        "title": "Verplaatsingen",
        "subtitle": "{from_festival} -> {to_festival} · {season} · {count} karren",
        "printed_on": "Afgedrukt op {date}",
        "printed_by": "afgedrukt door {name}",
        "page": "Pagina {page} / {pages}",
        "pick_up_at": "Ophalen bij: {name}",
        "kar_count": "{count} karren",
        "kar_count_one": "1 kar",
        "columns": ["Karnummer", "Ploeg", "Transporttype", "Pos.", "Naar afleverlocatie", "Zone", "Verplaatst"],
        "map_title": "Verplaatsingen",
        "map_subtitle": "Van {from_festival} naar {to_festival}: pijl = verplaatsing (aantal karren)",
        "legend": "Legende",
        "legend_pickup": "Ophaallocatie (positie in de levertoer)",
        "legend_destination": "Enkel bestemming",
        "legend_move": "Verplaatsing (aantal karren)",
        "locations": "Locaties",
        "letter_hint": "Letters = locatie zonder positie in de levertoer.",
        "outside_plan": "Buiten het grondplan:",
        "not_on_map": "Niet op de kaart (geen coördinaten):",
        "no_groundplan": "Geen grondplan voor deze locaties: enkel de posities.",
    },
    "en": {
        "title": "Moves",
        "subtitle": "{from_festival} -> {to_festival} · {season} · {count} karren",
        "printed_on": "Printed on {date}",
        "printed_by": "printed by {name}",
        "page": "Page {page} / {pages}",
        "pick_up_at": "Pick up at: {name}",
        "kar_count": "{count} karren",
        "kar_count_one": "1 kar",
        "columns": ["Kar number", "Team", "Transport type", "Pos.", "To delivery location", "Zone", "Moved"],
        "map_title": "Moves",
        "map_subtitle": "From {from_festival} to {to_festival}: arrow = move (number of karren)",
        "legend": "Legend",
        "legend_pickup": "Pick-up location (position in the tour)",
        "legend_destination": "Destination only",
        "legend_move": "Move (number of karren)",
        "locations": "Locations",
        "letter_hint": "Letters = location without a position in the delivery tour.",
        "outside_plan": "Outside the ground plan:",
        "not_on_map": "Not on the map (no coordinates):",
        "no_groundplan": "No ground plan for these locations: positions only.",
    },
}

# Table column widths in mm (landscape A4 minus the margins = 273 mm) and
# their alignment, in the order of LABELS[...]["columns"].
COLUMN_WIDTHS = (28, 50, 36, 14, 85, 36, 24)
COLUMN_ALIGN = ("L", "L", "L", "C", "L", "L", "C")


def _kar_count(labels: dict, count: int) -> str:
    return labels["kar_count_one"] if count == 1 else labels["kar_count"].format(count=count)


def _location_label(location: KarMovesLocation) -> str:
    """"Name — description" (just the name when there is no description)."""
    return f"{location.name} — {location.description}" if location.description else location.name


def _table_heading(pdf: FPDF, labels: dict) -> None:
    """The purple heading row of the table."""
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(pdf.l_margin)
    for heading, width, align in zip(labels["columns"], COLUMN_WIDTHS, COLUMN_ALIGN):
        pdf.cell(width, ROW_HEIGHT, _fit(pdf, heading, width), align=align, fill=True)
    pdf.ln(ROW_HEIGHT)


def _section_heading(pdf: _DeliveryPlanningPDF, labels: dict, group: KarMovesLocationGroup) -> None:
    """"Ophalen bij: 3 · <location> (zone)" with a purple bar and its kar count."""
    top = pdf.get_y() + 2
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(pdf.l_margin, top + 1.2, 1.6, 5.5, style="F")
    pdf.set_xy(pdf.l_margin + 4, top)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*TEXT_DARK)
    name = _location_label(group)
    if group.terrein_positie is not None:
        name = f"{group.terrein_positie} · {name}"
    heading = labels["pick_up_at"].format(name=f"{name} ({group.zone_name})")
    pdf.cell(pdf.get_string_width(pdf_text(heading)) + 4, 8, pdf_text(heading))
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 8, pdf_text(_kar_count(labels, len(group.karren))), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _render_tables(pdf: _DeliveryPlanningPDF, labels: dict, groups: list[KarMovesLocationGroup]) -> None:
    """One section per pick-up location (tour order) with its karren and their destination."""
    pdf.add_page()
    for group in groups:
        # Keep the heading together with the table heading and a first row.
        if pdf.get_y() + 12 + 2 * ROW_HEIGHT > pdf.content_bottom:
            pdf.add_page()
        _section_heading(pdf, labels, group)
        _table_heading(pdf, labels)

        for index, kar in enumerate(group.karren):
            # A new page repeats the table heading.
            if pdf.get_y() + ROW_HEIGHT > pdf.content_bottom:
                pdf.add_page()
                _table_heading(pdf, labels)

            destination = kar.to_location
            values = (
                kar.kar_nummer,
                kar.team_name,
                kar.transport_type_name,
                str(destination.terrein_positie) if destination.terrein_positie is not None else "-",
                _location_label(destination),
                destination.zone_name,
                "",
            )
            top = pdf.get_y()
            pdf.set_fill_color(*(LOCATION_FILL if index % 2 == 0 else ZEBRA_FILL))
            pdf.set_text_color(*TEXT_DARK)
            pdf.set_x(pdf.l_margin)
            for column, (value, width, align) in enumerate(zip(values, COLUMN_WIDTHS, COLUMN_ALIGN)):
                # Kar number and destination stand out: that's what the driver needs.
                pdf.set_font("Helvetica", "B" if column in (0, 3, 4) else "", 8.5)
                pdf.cell(width, ROW_HEIGHT, _fit(pdf, value, width), align=align, fill=True)
            # The empty box the driver ticks when the kar has been moved.
            box = 3.6
            box_x = pdf.l_margin + sum(COLUMN_WIDTHS[:-1]) + (COLUMN_WIDTHS[-1] - box) / 2
            pdf.set_draw_color(*TEXT_DARK)
            pdf.set_line_width(0.25)
            pdf.rect(box_x, top + (ROW_HEIGHT - box) / 2, box, box)
            pdf.ln(ROW_HEIGHT)
        pdf.ln(3)


# --- Map ---------------------------------------------------------------------


def _badge(pdf: FPDF, x: float, y: float, label: str, colour: tuple[int, int, int]) -> None:
    """A round badge with a white label (tour position or letter)."""
    pdf.set_fill_color(*colour)
    pdf.set_draw_color(255, 255, 255)
    pdf.set_line_width(0.4)
    radius = 2.4 if len(label) < 3 else 2.9
    pdf.circle(x, y, radius, style="FD")
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(x - radius, y - 1.5)
    pdf.cell(2 * radius, 3, pdf_text(label), align="C")


def _arrow(pdf: FPDF, start: tuple[float, float], end: tuple[float, float], count: int) -> None:
    """A line from `start` to `end` that stops at the badges, an arrow head
    at the end and the number of karren in the middle.
    """
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 6:
        return  # badges (almost) on top of each other: no room for an arrow
    ux, uy = dx / length, dy / length
    # Start and stop just outside the two badges.
    x1, y1 = start[0] + ux * 3, start[1] + uy * 3
    x2, y2 = end[0] - ux * 3.2, end[1] - uy * 3.2
    pdf.set_draw_color(*TEXT_DARK)
    pdf.set_line_width(0.45)
    pdf.line(x1, y1, x2, y2)
    # The head: a small filled triangle pointing at the destination.
    head, half = 2.2, 1.1
    base_x, base_y = x2 - ux * head, y2 - uy * head
    pdf.set_fill_color(*TEXT_DARK)
    pdf.polygon([(x2, y2), (base_x - uy * half, base_y + ux * half), (base_x + uy * half, base_y - ux * half)], style="F")
    # The number of karren on a small white label halfway.
    text = str(count)
    mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
    pdf.set_font("Helvetica", "B", 6.5)
    width = pdf.get_string_width(text) + 1.8
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*TEXT_DARK)
    pdf.set_line_width(0.2)
    pdf.rect(mid_x - width / 2, mid_y - 1.6, width, 3.2, style="FD")
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_xy(mid_x - width / 2, mid_y - 1.5)
    pdf.cell(width, 3, text, align="C")


def _location_badges(groups: list[KarMovesLocationGroup]) -> tuple[list[KarMovesLocation], dict[int, str], set[int]]:
    """Every location involved once (tour order), its badge label (tour
    position, or a letter A, B, ... when it has none) and the pick-up ids.
    """
    pickup_ids = {group.id for group in groups}
    by_id: dict[int, KarMovesLocation] = {}
    for group in groups:
        by_id[group.id] = group
        for kar in group.karren:
            by_id.setdefault(kar.to_location.id, kar.to_location)
    locations = sorted(
        by_id.values(),
        key=lambda loc: (loc.terrein_positie is None, loc.terrein_positie or 0, loc.name.lower()),
    )
    badge_labels: dict[int, str] = {}
    letter = 0
    for location in locations:
        if location.terrein_positie is not None:
            badge_labels[location.id] = str(location.terrein_positie)
        else:
            # A, B, ..., Z, AA, AB, ... for locations without a position.
            index, text = letter, ""
            while True:
                text = chr(ord("A") + index % 26) + text
                index = index // 26 - 1
                if index < 0:
                    break
            badge_labels[location.id] = text
            letter += 1
    return locations, badge_labels, pickup_ids


def _render_map(
    pdf: _DeliveryPlanningPDF,
    labels: dict,
    groups: list[KarMovesLocationGroup],
    groundplans: list[KarTrackerGroundplan],
    *,
    from_festival: str,
    to_festival: str,
) -> None:
    """The map page: ground plan, an arrow per move, the badges and a legend."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 7, pdf_text(labels["map_title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED_TEXT)
    subtitle = labels["map_subtitle"].format(from_festival=from_festival, to_festival=to_festival)
    pdf.cell(0, 5, pdf_text(subtitle), new_x="LMARGIN", new_y="NEXT")

    locations, badge_labels, pickup_ids = _location_badges(groups)

    # Everything with coordinates becomes a point; the rest is listed.
    points: list[_MapPoint] = []
    point_by_location: dict[int, _MapPoint] = {}
    not_on_map: list[str] = []
    for location in locations:
        if location.latitude is None or location.longitude is None:
            not_on_map.append(f"{badge_labels[location.id]}. {location.name}")
            continue
        x, y = _project(location.latitude, location.longitude)
        kind = "pickup" if location.id in pickup_ids else "destination"
        point = _MapPoint(x, y, badge_labels[location.id], kind)
        points.append(point)
        point_by_location[location.id] = point

    # The map area on the left, the legend column on the right.
    area_x, area_y = pdf.l_margin, pdf.get_y() + 2
    legend_w = 72
    area_w = pdf.w - pdf.l_margin - pdf.r_margin - legend_w - 5
    area_h = pdf.content_bottom - area_y
    legend_x = area_x + area_w + 5

    to_page, plan, drawn, outside_plan = _draw_map_view(pdf, points, groundplans, area_x, area_y, area_w, area_h)
    drawn_ids = {id(point) for point in drawn}

    # One arrow per (from, to) pair, with its number of karren; only when both ends are drawn.
    moves: dict[tuple[int, int], int] = {}
    for group in groups:
        for kar in group.karren:
            pair = (group.id, kar.to_location.id)
            moves[pair] = moves.get(pair, 0) + 1
    for (from_id, to_id), count in moves.items():
        start, end = point_by_location.get(from_id), point_by_location.get(to_id)
        if start is None or end is None or id(start) not in drawn_ids or id(end) not in drawn_ids:
            continue
        _arrow(pdf, to_page(start.x, start.y), to_page(end.x, end.y), count)

    # The badges on top: purple for pick-up locations, green for destinations only.
    for point in drawn:
        x, y = to_page(point.x, point.y)
        _badge(pdf, x, y, point.label, ACCENT_COLOR if point.kind == "pickup" else DESTINATION_COLOR)

    _render_legend(
        pdf, labels, legend_x, area_y, legend_w, locations, badge_labels, plan is None, outside_plan, not_on_map
    )


def _render_legend(
    pdf: _DeliveryPlanningPDF,
    labels: dict,
    x: float,
    y: float,
    width: float,
    locations: list[KarMovesLocation],
    badge_labels: dict[int, str],
    no_groundplan: bool,
    outside_plan: list[str],
    not_on_map: list[str],
) -> None:
    """The column right of the map: the symbols, then every location by its
    badge label and what isn't on the map. Continues in columns on a new page
    when it doesn't fit.
    """
    # Symbols: drawn swatch + text.
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_xy(x, y)
    pdf.cell(width, 5.5, pdf_text(labels["legend"]))
    y += 5.5
    for kind, text in (
        ("pickup", labels["legend_pickup"]),
        ("destination", labels["legend_destination"]),
        ("move", labels["legend_move"]),
    ):
        centre_y = y + 2
        if kind == "move":
            pdf.set_draw_color(*TEXT_DARK)
            pdf.set_line_width(0.45)
            pdf.line(x, centre_y, x + 3.8, centre_y)
            pdf.set_fill_color(*TEXT_DARK)
            pdf.polygon([(x + 5, centre_y), (x + 3.4, centre_y - 1), (x + 3.4, centre_y + 1)], style="F")
        else:
            pdf.set_fill_color(*(ACCENT_COLOR if kind == "pickup" else DESTINATION_COLOR))
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

    # Every location: "label. description (zone)" (the name when there is no description).
    writer.line(labels["locations"], bold=True, size=9, height=5.5)
    for location in locations:
        writer.line(f"{badge_labels[location.id]}.  {location.description or location.name}  ({location.zone_name})")
    if any(location.terrein_positie is None for location in locations):
        writer.gap(1)
        writer.paragraph(labels["letter_hint"], muted=True)

    # What couldn't be drawn.
    for heading, names in ((labels["outside_plan"], outside_plan), (labels["not_on_map"], not_on_map)):
        if names:
            writer.gap(2)
            writer.line(heading, bold=True)
            writer.paragraph(", ".join(names), muted=True)


def build_kar_moves_pdf(
    groups: list[KarMovesLocationGroup],
    *,
    season_name: str,
    from_festival: str,
    to_festival: str,
    include_map: bool,
    groundplans: list[KarTrackerGroundplan],
    printed_by: str | None,
    locale: str = "nl",
) -> bytes:
    """The landscape "Verplaatsingen" PDF for the given (already filtered)
    pick-up location groups, optionally with the map page.
    """
    labels = LABELS.get(locale, LABELS["nl"])
    total = sum(len(group.karren) for group in groups)
    subtitle = labels["subtitle"].format(
        from_festival=from_festival, to_festival=to_festival, season=season_name, count=total
    )
    pdf = _DeliveryPlanningPDF(labels, subtitle=subtitle, printed_by=printed_by)
    _render_tables(pdf, labels, groups)
    if include_map:
        _render_map(pdf, labels, groups, groundplans, from_festival=from_festival, to_festival=to_festival)
    return bytes(pdf.output())
