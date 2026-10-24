# Builds the landscape "Leverplanning" PDF of KarTracker's "Initiële
# leverplanning" screen: for the karren ticked on the screen, where the
# driver picks each kar up (distributiepunt) and where it is delivered
# (afleverlocatie), in the order of the delivery tour.
#
#   - one section per distributiepunt ("Ophalen bij: ...") with a table of its
#     locations in tour order and their karren, plus an empty "Geleverd" box
#     per kar to tick off;
#   - optionally a "Leverroute" page: the ground plan with the route through
#     the locations (dashed line 1 -> n), numbered badges and the pick-up
#     points, like the "Kaart" on the Leveringsvolgorde screen.
#
# Same house style as StockMaster's PDFs (module_4/pdf_layout.py: header band
# with the TeamKar logo, footer with page x / y), in KarTracker's purple.
# Uses fpdf2 + Pillow and the shared helpers in app/shared/pdf_common.py.

import io
import math
from collections.abc import Callable
from dataclasses import dataclass

from fpdf import FPDF
from PIL import Image

from app.core.timezone import belgian_now
from app.db.models.kartracker_groundplan import KarTrackerGroundplan
from app.schemas.kartracker import InitialDeliveryDistributiepuntGroup
from app.shared.pdf_common import (
    BORDER_COLOR,
    MUTED_TEXT,
    TEAMKAR_LOGO_RATIO,
    TEXT_DARK,
    pdf_text,
    teamkar_logo,
)

# KarTracker's purple (purple-600, see frontend/src/lib/module-theme.ts).
ACCENT_COLOR = (147, 51, 234)
# Light purple for a location's first row and the zebra of its karren.
LOCATION_FILL = (243, 232, 255)
ZEBRA_FILL = (250, 245, 255)
# Grey badge for a location that isn't in the delivery tour.
UNPOSITIONED_COLOR = (156, 163, 175)
# The ground plan is the largest image in the PDF; this is plenty sharp for
# a landscape A4 page and keeps the file small.
MAP_IMAGE_MAX_PX = 2400
# The map zooms in on the printed points; this is the smallest stretch of
# ground (in metres) it shows, so one or two points don't fill the page.
MAP_MIN_SPAN_M = 150
# Room around the outermost points, as a share of their spread.
MAP_PADDING = 0.12

LABELS = {
    "nl": {
        "title": "Leverplanning",
        "subtitle": "Initiële leverplanning · {season} · {count} karren",
        "printed_on": "Afgedrukt op {date}",
        "printed_by": "afgedrukt door {name}",
        "page": "Pagina {page} / {pages}",
        "pick_up_at": "Ophalen bij: {name}",
        "kar_count": "{count} karren",
        "kar_count_one": "1 kar",
        "columns": [
            "Pos.", "Afleverlocatie", "Zone", "Karnummer", "Ploeg",
            "Transporttype", "Festival", "Leverdatum", "Geleverd",
        ],
        "no_position": "-",
        "map_title": "Leverroute",
        "map_subtitle": "Afleverlocaties in de volgorde van de levertoer",
        "legend": "Legende",
        "legend_location": "Afleverlocatie (positie in de levertoer)",
        "legend_unpositioned": "Afleverlocatie zonder positie",
        "legend_distributiepunt": "Distributiepunt (ophalen)",
        "legend_route": "Leverroute",
        "tour_stops": "Levertoer",
        "unpositioned_count": "+ {count} afleverlocaties zonder positie (grijs, zie de tabel)",
        "outside_plan": "Buiten het grondplan:",
        "not_on_map": "Niet op de kaart (geen coördinaten):",
        "no_groundplan": "Geen grondplan voor deze locaties: enkel de posities.",
    },
    "en": {
        "title": "Delivery planning",
        "subtitle": "Initial delivery planning · {season} · {count} karren",
        "printed_on": "Printed on {date}",
        "printed_by": "printed by {name}",
        "page": "Page {page} / {pages}",
        "pick_up_at": "Pick up at: {name}",
        "kar_count": "{count} karren",
        "kar_count_one": "1 kar",
        "columns": [
            "Pos.", "Delivery location", "Zone", "Kar number", "Team",
            "Transport type", "Festival", "Delivery date", "Delivered",
        ],
        "no_position": "-",
        "map_title": "Delivery route",
        "map_subtitle": "Delivery locations in the order of the delivery tour",
        "legend": "Legend",
        "legend_location": "Delivery location (position in the tour)",
        "legend_unpositioned": "Delivery location without a position",
        "legend_distributiepunt": "Distribution point (pick-up)",
        "legend_route": "Delivery route",
        "tour_stops": "Delivery tour",
        "unpositioned_count": "+ {count} delivery locations without a position (grey, see the table)",
        "outside_plan": "Outside the ground plan:",
        "not_on_map": "Not on the map (no coordinates):",
        "no_groundplan": "No ground plan for these locations: positions only.",
    },
}

# Table column widths in mm (landscape A4 minus the margins = 273 mm) and
# their alignment, in the order of LABELS[...]["columns"].
COLUMN_WIDTHS = (12, 66, 26, 24, 42, 30, 30, 23, 20)
COLUMN_ALIGN = ("C", "L", "L", "L", "L", "L", "L", "L", "C")
ROW_HEIGHT = 6.5


class _DeliveryPlanningPDF(FPDF):
    """A landscape A4 page in the house style, header/footer on every page."""

    def __init__(self, labels: dict, *, subtitle: str, printed_by: str | None) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.labels = labels
        self.doc_subtitle = subtitle
        self.printed_by = printed_by
        self.printed_on = belgian_now().strftime("%d-%m-%Y %H:%M")
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=False)
        self.alias_nb_pages()

    def header(self) -> None:
        """Purple band, TeamKar logo, title/subtitle and the print date."""
        self.set_fill_color(*ACCENT_COLOR)
        self.rect(0, 0, self.w, 3, style="F")

        logo_height = 14
        logo = teamkar_logo()
        if logo is not None:
            self.image(logo, x=self.l_margin, y=6, h=logo_height)
        text_left = self.l_margin + logo_height * TEAMKAR_LOGO_RATIO + 5
        right_block = 60

        self.set_xy(text_left, 7)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*TEXT_DARK)
        self.cell(self.w - self.r_margin - text_left - right_block, 8, pdf_text(self.labels["title"]))
        self.set_xy(text_left, 15)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*MUTED_TEXT)
        self.cell(self.w - self.r_margin - text_left - right_block, 5, pdf_text(self.doc_subtitle))

        self.set_xy(self.w - self.r_margin - right_block, 9)
        self.set_font("Helvetica", "", 9)
        self.cell(right_block, 5, pdf_text(self.labels["printed_on"].format(date=self.printed_on)), align="R")

        # Purple rule under the header.
        self.set_draw_color(*ACCENT_COLOR)
        self.set_line_width(0.5)
        self.line(self.l_margin, 23, self.w - self.r_margin, 23)
        self.set_y(27)

    def footer(self) -> None:
        """"KarTracker · RWCrew · printed by ..." left, page x / y right."""
        self.set_y(-11)
        self.set_draw_color(*BORDER_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 1, self.w - self.r_margin, self.get_y() - 1)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED_TEXT)
        left = "KarTracker · RWCrew"
        if self.printed_by:
            left += " · " + self.labels["printed_by"].format(name=self.printed_by)
        self.cell(0, 5, pdf_text(left), align="L")
        self.set_x(self.l_margin)
        self.cell(0, 5, pdf_text(self.labels["page"].format(page=self.page_no(), pages="{nb}")), align="R")

    @property
    def content_bottom(self) -> float:
        """The lowest y the content may use (just above the footer)."""
        return self.h - 15


def _fit(pdf: FPDF, text: str, width: float) -> str:
    """The text, cut off with "..." so it fits in a cell of `width` mm."""
    value = pdf_text(text)
    room = width - 2  # the cell's own padding
    if pdf.get_string_width(value) <= room:
        return value
    while value and pdf.get_string_width(value + "...") > room:
        value = value[:-1]
    return value + "..."


def _kar_count(labels: dict, count: int) -> str:
    return labels["kar_count_one"] if count == 1 else labels["kar_count"].format(count=count)


def _format_date(value) -> str:
    return value.strftime("%d-%m-%Y") if value else ""


def _table_heading(pdf: FPDF, labels: dict) -> None:
    """The purple heading row of the table."""
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(pdf.l_margin)
    for heading, width, align in zip(labels["columns"], COLUMN_WIDTHS, COLUMN_ALIGN):
        pdf.cell(width, ROW_HEIGHT, _fit(pdf, heading, width), align=align, fill=True)
    pdf.ln(ROW_HEIGHT)


def _section_heading(pdf: _DeliveryPlanningPDF, labels: dict, group: InitialDeliveryDistributiepuntGroup) -> None:
    """"Ophalen bij: <distributiepunt>" with a purple bar and its kar count."""
    top = pdf.get_y() + 2
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(pdf.l_margin, top + 1.2, 1.6, 5.5, style="F")
    pdf.set_xy(pdf.l_margin + 4, top)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*TEXT_DARK)
    heading = labels["pick_up_at"].format(name=group.name)
    pdf.cell(pdf.get_string_width(pdf_text(heading)) + 4, 8, pdf_text(heading))
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 8, pdf_text(_kar_count(labels, group.count)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _render_tables(pdf: _DeliveryPlanningPDF, labels: dict, groups: list[InitialDeliveryDistributiepuntGroup]) -> None:
    """One section per distributiepunt, its locations in tour order with their karren."""
    pdf.add_page()
    for group in groups:
        # Keep the heading together with the table heading and a first row.
        if pdf.get_y() + 12 + 2 * ROW_HEIGHT > pdf.content_bottom:
            pdf.add_page()
        _section_heading(pdf, labels, group)
        _table_heading(pdf, labels)

        for location in group.locations:
            location_label = f"{location.name} — {location.description}" if location.description else location.name
            position = str(location.terrein_positie) if location.terrein_positie is not None else labels["no_position"]
            for index, kar in enumerate(location.karren):
                # A new page repeats the table heading.
                if pdf.get_y() + ROW_HEIGHT > pdf.content_bottom:
                    pdf.add_page()
                    _table_heading(pdf, labels)

                # The location's own cells only on its first kar, so each
                # location reads as one block.
                first = index == 0
                values = (
                    position if first else "",
                    location_label if first else "",
                    location.zone_name if first else "",
                    kar.kar_nummer,
                    kar.team_name,
                    kar.transport_type_name,
                    kar.festival_name,
                    _format_date(kar.delivery_date),
                    "",
                )
                top = pdf.get_y()
                # A thin rule above each new location.
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
                # The empty box the driver ticks when the kar is delivered.
                box = 3.6
                box_x = pdf.l_margin + sum(COLUMN_WIDTHS[:-1]) + (COLUMN_WIDTHS[-1] - box) / 2
                pdf.set_draw_color(*TEXT_DARK)
                pdf.set_line_width(0.25)
                pdf.rect(box_x, top + (ROW_HEIGHT - box) / 2, box, box)
                pdf.ln(ROW_HEIGHT)
        pdf.ln(3)


# --- Route map ---------------------------------------------------------------

# Point kinds drawn as a numbered badge ("3." when listed as outside the plan).
NUMBERED_KINDS = ("location", "pickup", "destination")


@dataclass
class _MapPoint:
    """One pin on the route map, in projected (Web-Mercator) units."""

    x: float
    y: float
    label: str  # number in the badge, else the location's/distributiepunt's name
    kind: str  # "location" | "unpositioned" | "distributiepunt"


def _project(latitude: float, longitude: float) -> tuple[float, float]:
    """Web-Mercator x/y (y grows northwards), the projection Leaflet uses,
    so the ground plan is stretched over its bounds the same way as on screen.
    """
    x = math.radians(longitude)
    y = math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2))
    return x, y


def _groundplan_bounds(plan: KarTrackerGroundplan) -> tuple[float, float, float, float]:
    """A ground plan's projected bounds: (min x, min y, max x, max y)."""
    min_x, min_y = _project(plan.sw_latitude, plan.sw_longitude)
    max_x, max_y = _project(plan.ne_latitude, plan.ne_longitude)
    return min(min_x, max_x), min(min_y, max_y), max(min_x, max_x), max(min_y, max_y)


def _pick_groundplan(points: list[_MapPoint], groundplans: list[KarTrackerGroundplan]) -> KarTrackerGroundplan | None:
    """The ground plan that holds the most points (None when none holds any)."""
    best: KarTrackerGroundplan | None = None
    best_count = 0
    for plan in groundplans:
        min_x, min_y, max_x, max_y = _groundplan_bounds(plan)
        count = sum(1 for point in points if min_x <= point.x <= max_x and min_y <= point.y <= max_y)
        if count > best_count:
            best, best_count = plan, count
    return best


def _print_image(plan: KarTrackerGroundplan, crop: tuple[float, float, float, float]) -> io.BytesIO:
    """The part of the ground plan shown on the map (`crop` = left, top,
    right, bottom as fractions of the image), shrunk and re-encoded as JPEG
    (white behind transparency). Cropping first keeps the zoomed-in part sharp.
    """
    image = Image.open(io.BytesIO(plan.image_data))
    left, top, right, bottom = crop
    image = image.crop(
        (
            round(left * image.width),
            round(top * image.height),
            max(round(right * image.width), round(left * image.width) + 1),
            max(round(bottom * image.height), round(top * image.height) + 1),
        )
    )
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")
    image.thumbnail((MAP_IMAGE_MAX_PX, MAP_IMAGE_MAX_PX))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    output.seek(0)
    return output


def _draw_map_view(
    pdf: FPDF,
    points: list[_MapPoint],
    groundplans: list[KarTrackerGroundplan],
    area_x: float,
    area_y: float,
    area_w: float,
    area_h: float,
) -> tuple[Callable[[float, float], tuple[float, float]], KarTrackerGroundplan | None, list[_MapPoint], list[str]]:
    """The map's background in the given area: picks the ground plan holding
    most points, zooms in on the points and draws the (faded) plan and a
    border. Returns the projected -> page function, the plan used (None =
    none), the points inside the plan (the ones to draw) and the labels of
    the points left out because they lie outside it. Shared by the
    Leverplanning map and the Verplaatsingen map (kar_moves_pdf.py).
    """
    plan = _pick_groundplan(points, groundplans)

    # Points outside the ground plan are listed instead of drawn, so one stray
    # coordinate can't pull the map away from the terrain.
    outside_plan: list[str] = []
    if plan is not None:
        plan_bounds = _groundplan_bounds(plan)
        inside = []
        for point in points:
            if plan_bounds[0] <= point.x <= plan_bounds[2] and plan_bounds[1] <= point.y <= plan_bounds[3]:
                inside.append(point)
            else:
                outside_plan.append(f"{point.label}." if point.kind in NUMBERED_KINDS else point.label)
        points = inside

    # What the map shows, in projected units: zoomed in on the printed points
    # (with some room around them and at least MAP_MIN_SPAN_M of ground), or
    # the whole ground plan when there is nothing to draw.
    if points:
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        centre_x, centre_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        # Metres -> projected units at this latitude (Web-Mercator stretches by 1 / cos(latitude)).
        latitude = 2 * math.atan(math.exp(centre_y)) - math.pi / 2
        min_span = MAP_MIN_SPAN_M / (6_378_137 * math.cos(latitude))
        span_x = max((max_x - min_x) * (1 + 2 * MAP_PADDING), min_span)
        span_y = max((max_y - min_y) * (1 + 2 * MAP_PADDING), min_span)
    elif plan is not None:
        centre_x, centre_y = (plan_bounds[0] + plan_bounds[2]) / 2, (plan_bounds[1] + plan_bounds[3]) / 2
        span_x, span_y = plan_bounds[2] - plan_bounds[0], plan_bounds[3] - plan_bounds[1]
    else:
        centre_x, centre_y, span_x, span_y = 0.0, 0.0, 1.0, 1.0
    # Widen one side so the view has the area's shape and fills it.
    if span_x / span_y < area_w / area_h:
        span_x = span_y * area_w / area_h
    else:
        span_y = span_x * area_h / area_w
    min_x, max_x = centre_x - span_x / 2, centre_x + span_x / 2
    min_y, max_y = centre_y - span_y / 2, centre_y + span_y / 2

    scale = area_w / span_x
    view_x, view_y, view_w, view_h = area_x, area_y, area_w, area_h

    def to_page(x: float, y: float) -> tuple[float, float]:
        """Projected units -> page mm (y flipped: north is up)."""
        return view_x + (x - min_x) * scale, view_y + (max_y - y) * scale

    # Background: the ground plan (slightly faded so the badges stand out)
    # or a plain light area.
    pdf.set_fill_color(248, 248, 250)
    pdf.rect(view_x, view_y, view_w, view_h, style="F")
    if plan is not None:
        # The part of the plan inside the view, cut out of the image.
        part = (
            max(min_x, plan_bounds[0]),
            max(min_y, plan_bounds[1]),
            min(max_x, plan_bounds[2]),
            min(max_y, plan_bounds[3]),
        )
        if part[0] < part[2] and part[1] < part[3]:
            plan_w, plan_h = plan_bounds[2] - plan_bounds[0], plan_bounds[3] - plan_bounds[1]
            crop = (
                (part[0] - plan_bounds[0]) / plan_w,
                (plan_bounds[3] - part[3]) / plan_h,
                (part[2] - plan_bounds[0]) / plan_w,
                (plan_bounds[3] - part[1]) / plan_h,
            )
            left, top = to_page(part[0], part[3])
            right, bottom = to_page(part[2], part[1])
            pdf.image(_print_image(plan, crop), x=left, y=top, w=right - left, h=bottom - top)
            with pdf.local_context(fill_opacity=0.3):
                pdf.set_fill_color(255, 255, 255)
                pdf.rect(left, top, right - left, bottom - top, style="F")
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.3)
    pdf.rect(view_x, view_y, view_w, view_h)

    return to_page, plan, points, outside_plan


def _render_map(
    pdf: _DeliveryPlanningPDF,
    labels: dict,
    groups: list[InitialDeliveryDistributiepuntGroup],
    groundplans: list[KarTrackerGroundplan],
) -> None:
    """The "Leverroute" page: ground plan, route, badges and a legend."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 7, pdf_text(labels["map_title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED_TEXT)
    pdf.cell(0, 5, pdf_text(labels["map_subtitle"]), new_x="LMARGIN", new_y="NEXT")

    # Every printed location once, in tour order (positioned first).
    locations = [location for group in groups for location in group.locations]
    locations.sort(key=lambda loc: (loc.terrein_positie is None, loc.terrein_positie or 0, loc.name.lower()))

    # Everything with coordinates becomes a point; the rest is listed.
    points: list[_MapPoint] = []
    not_on_map: list[str] = []
    for location in locations:
        if location.latitude is None or location.longitude is None:
            not_on_map.append(location.name)
            continue
        x, y = _project(location.latitude, location.longitude)
        if location.terrein_positie is not None:
            points.append(_MapPoint(x, y, str(location.terrein_positie), "location"))
        else:
            points.append(_MapPoint(x, y, location.name, "unpositioned"))
    for group in groups:
        if group.latitude is None or group.longitude is None:
            not_on_map.append(group.name)
            continue
        x, y = _project(group.latitude, group.longitude)
        points.append(_MapPoint(x, y, group.name, "distributiepunt"))

    # The map area on the left, the legend column on the right.
    area_x, area_y = pdf.l_margin, pdf.get_y() + 2
    legend_w = 72
    area_w = pdf.w - pdf.l_margin - pdf.r_margin - legend_w - 5
    area_h = pdf.content_bottom - area_y
    legend_x = area_x + area_w + 5

    to_page, plan, points, outside_plan = _draw_map_view(pdf, points, groundplans, area_x, area_y, area_w, area_h)

    # Locations without a tour position: small grey dots underneath the rest.
    for point in points:
        if point.kind == "unpositioned":
            x, y = to_page(point.x, point.y)
            pdf.set_fill_color(*UNPOSITIONED_COLOR)
            pdf.set_draw_color(255, 255, 255)
            pdf.set_line_width(0.3)
            pdf.circle(x, y, 1.4, style="FD")

    # The route 1 -> n as a dashed purple line.
    route = [point for point in points if point.kind == "location"]
    if len(route) > 1:
        pdf.set_draw_color(*ACCENT_COLOR)
        pdf.set_line_width(0.6)
        pdf.set_dash_pattern(dash=2, gap=1.4)
        pdf.polyline([to_page(point.x, point.y) for point in route])
        pdf.set_dash_pattern()

    # Pick-up points: dark squares with their name.
    for point in points:
        if point.kind != "distributiepunt":
            continue
        x, y = to_page(point.x, point.y)
        pdf.set_fill_color(*TEXT_DARK)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.4)
        pdf.rect(x - 2.2, y - 2.2, 4.4, 4.4, style="FD")
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_xy(x + 2.8, y - 2)
        pdf.cell(pdf.get_string_width(pdf_text(point.label)) + 1, 4, pdf_text(point.label))

    # The tour's numbered badges on top.
    for point in route:
        x, y = to_page(point.x, point.y)
        pdf.set_fill_color(*ACCENT_COLOR)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.4)
        radius = 2.4 if len(point.label) < 3 else 2.9
        pdf.circle(x, y, radius, style="FD")
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(x - radius, y - 1.5)
        pdf.cell(2 * radius, 3, point.label, align="C")

    _render_legend(pdf, labels, legend_x, area_y, legend_w, locations, groups, plan is None, outside_plan, not_on_map)


class _ColumnWriter:
    """Writes short lines into a column; when it is full it moves to the next
    column, and after the last one to a new page with full-width columns.
    """

    def __init__(self, pdf: _DeliveryPlanningPDF, x: float, y: float, width: float) -> None:
        self.pdf = pdf
        self.columns = [x]
        self.column = 0
        self.top = y
        self.y = y
        self.width = width

    def _next_column(self) -> None:
        self.column += 1
        if self.column >= len(self.columns):
            # A new page with as many columns of the same width as fit.
            self.pdf.add_page()
            usable = self.pdf.w - self.pdf.l_margin - self.pdf.r_margin
            count = max(1, int((usable + 5) // (self.width + 5)))
            self.columns = [self.pdf.l_margin + index * (self.width + 5) for index in range(count)]
            self.column = 0
            self.top = self.pdf.get_y()
        self.y = self.top

    def gap(self, height: float) -> None:
        self.y += height

    def line(self, text: str, *, bold: bool = False, muted: bool = False, size: float = 7.5, height: float = 4.0) -> None:
        if self.y + height > self.pdf.content_bottom:
            self._next_column()
        pdf = self.pdf
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_text_color(*(MUTED_TEXT if muted else TEXT_DARK))
        pdf.set_xy(self.columns[self.column], self.y)
        pdf.cell(self.width, height, _fit(pdf, text, self.width))
        self.y += height

    def paragraph(self, text: str, *, muted: bool = False, size: float = 7.5, height: float = 3.6) -> None:
        """Longer text wrapped over as many lines as it needs."""
        self.pdf.set_font("Helvetica", "", size)
        wrapped = self.pdf.multi_cell(self.width, height, pdf_text(text), dry_run=True, output="LINES")
        for wrapped_line in wrapped:
            self.line(wrapped_line, muted=muted, size=size, height=height)


def _render_legend(
    pdf: _DeliveryPlanningPDF,
    labels: dict,
    x: float,
    y: float,
    width: float,
    locations: list,
    groups: list[InitialDeliveryDistributiepuntGroup],
    no_groundplan: bool,
    outside_plan: list[str],
    not_on_map: list[str],
) -> None:
    """The column right of the map: the symbols, then the tour's stops by
    position, the number of locations without a position and what isn't on
    the map. Continues in columns on a new page when it doesn't fit.
    """
    # Symbols: drawn swatch + text.
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_xy(x, y)
    pdf.cell(width, 5.5, pdf_text(labels["legend"]))
    y += 5.5
    symbols = [
        ("location", labels["legend_location"]),
        ("unpositioned", labels["legend_unpositioned"]),
        ("distributiepunt", labels["legend_distributiepunt"]),
        ("route", labels["legend_route"]),
    ]
    for kind, text in symbols:
        centre_y = y + 2
        if kind == "route":
            pdf.set_draw_color(*ACCENT_COLOR)
            pdf.set_line_width(0.6)
            pdf.set_dash_pattern(dash=2, gap=1.4)
            pdf.line(x, centre_y, x + 5, centre_y)
            pdf.set_dash_pattern()
        elif kind == "distributiepunt":
            pdf.set_fill_color(*TEXT_DARK)
            pdf.rect(x + 0.8, centre_y - 1.7, 3.4, 3.4, style="F")
        elif kind == "location":
            pdf.set_fill_color(*ACCENT_COLOR)
            pdf.circle(x + 2.5, centre_y, 1.8, style="F")
        else:
            pdf.set_fill_color(*UNPOSITIONED_COLOR)
            pdf.circle(x + 2.5, centre_y, 1.2, style="F")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_xy(x + 7, y)
        pdf.cell(width - 7, 4, _fit(pdf, text, width - 7))
        y += 4.5

    writer = _ColumnWriter(pdf, x, y, width)
    if no_groundplan:
        writer.line(labels["no_groundplan"], muted=True)
    writer.gap(2)

    # The tour's stops: "position. description (zone)" (the name when there is no description).
    positioned = [location for location in locations if location.terrein_positie is not None]
    if positioned:
        writer.line(labels["tour_stops"], bold=True, size=9, height=5.5)
        for location in positioned:
            writer.line(f"{location.terrein_positie}.  {location.description or location.name}  ({location.zone_name})")
    unpositioned = len(locations) - len(positioned)
    if unpositioned:
        writer.gap(2)
        writer.line(labels["unpositioned_count"].format(count=unpositioned), muted=True)

    # What couldn't be drawn.
    for heading, names in ((labels["outside_plan"], outside_plan), (labels["not_on_map"], not_on_map)):
        if names:
            writer.gap(2)
            writer.line(heading, bold=True)
            writer.paragraph(", ".join(names), muted=True)


def build_delivery_planning_pdf(
    groups: list[InitialDeliveryDistributiepuntGroup],
    *,
    season_name: str,
    include_map: bool,
    groundplans: list[KarTrackerGroundplan],
    printed_by: str | None,
    locale: str = "nl",
) -> bytes:
    """The landscape "Leverplanning" PDF for the given (already filtered)
    distributiepunt groups, optionally with the route map page.
    """
    labels = LABELS.get(locale, LABELS["nl"])
    total = sum(group.count for group in groups)
    pdf = _DeliveryPlanningPDF(
        labels, subtitle=labels["subtitle"].format(season=season_name, count=total), printed_by=printed_by
    )
    _render_tables(pdf, labels, groups)
    if include_map:
        _render_map(pdf, labels, groups, groundplans)
    return bytes(pdf.output())
