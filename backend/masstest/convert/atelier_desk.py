# Converter for last year's Atelier "Uitgifte/Inname" list:
#
#   datum | group | ophaler | magazijn | beschrijving | aantal | gebroken aantal | product | product subtype
#
# - datum            → booked_at (Belgian time) and day
# - group            → team (matched by name/alias when running)
# - ophaler          → first name (first word) + family name (the rest)
# - aantal           → > 0 = Ophalen, < 0 = Terugbrengen (quantity = the absolute value)
# - product          → Atelier article (matched by name when running)
# - product subtype  → fit ("man" → men, "vrouw" → women, …) + size ("OneSize", "XL", …)
# - magazijn, beschrijving, gebroken aantal: not used (kept in source_values)
#
# Rows with the same datum, ophaler, group and direction form one
# transaction (one pick-up with several pieces, or one return). Rows that
# can't be read are left out of the load workbook and logged as issues.

from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from masstest.load_workbook import ATELIER_DESK, ATELIER_DESK_COLUMNS, PICK_UP, RETURN
from masstest.report import IssueLog

STEP = "convert"
REQUIRED = ("datum", "group", "ophaler", "aantal", "product", "product subtype")
# The first word of the subtype → the Atelier fit.
FIT_WORDS = {
    "man": "men", "men": "men", "heren": "men", "heer": "men", "m": "men",
    "vrouw": "women", "women": "women", "dames": "women", "dame": "women", "v": "women",
    "unisex": "unisex", "uni": "unisex",
}
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M")


def _clean(value: object) -> str:
    """Text with single spaces ("Albertieners vzw  (TOOG 24)" → one space)."""
    return " ".join(str(value).split()) if value is not None else ""


def parse_moment(value: object) -> datetime | None:
    """The datum cell as a (Belgian, zone-less) moment, or None."""
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    text = _clean(value)
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def parse_quantity(value: object) -> int | None:
    """The aantal as a whole number other than 0, or None."""
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if number != int(number) or int(number) == 0:
        return None
    return int(number)


def split_name(value: object) -> tuple[str, str] | None:
    """"Karel De Roock" → ("Karel", "De Roock"); None for fewer than two words."""
    words = _clean(value).split(" ")
    if len(words) < 2 or not words[0]:
        return None
    return words[0], " ".join(words[1:])


def split_subtype(value: object) -> tuple[str, str] | None:
    """"man OneSize" → ("men", "OneSize"); None when the fit word is unknown."""
    words = _clean(value).split(" ")
    if len(words) < 2 or words[0].lower() not in FIT_WORDS:
        return None
    return FIT_WORDS[words[0].lower()], " ".join(words[1:])


def convert_atelier_desk(source: Path, log: IssueLog) -> dict[str, tuple[list[str], list[dict]]]:
    """Read the old list and give the AtelierDesk sheet of the load workbook;
    unreadable rows are logged on `log`."""
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        rows = list(workbook.active.iter_rows(values_only=True))
    finally:
        workbook.close()
    if not rows:
        return {ATELIER_DESK: (ATELIER_DESK_COLUMNS, [])}

    header = [_clean(cell).lower() for cell in rows[0]]
    for column in REQUIRED:
        if column not in header:
            log.add(STEP, "column_missing", f"The source {source.name} has no column '{column}'.", params=[column],
                    source_file=source.name, source_rows="1")
    if any(column not in header for column in REQUIRED):
        return {ATELIER_DESK: (ATELIER_DESK_COLUMNS, [])}

    lines: list[dict] = []
    for number, values in enumerate(rows[1:], start=2):
        cells = {header[i]: values[i] for i in range(min(len(header), len(values))) if header[i]}
        if all(value is None or _clean(value) == "" for value in cells.values()):
            continue
        source_values = "; ".join(f"{key}={_clean(value)}" for key, value in cells.items() if _clean(value))
        where = {"source_file": source.name, "source_rows": str(number), "source_values": source_values}

        # Check every field; a row with any problem is left out (one issue per problem).
        problems = 0
        moment = parse_moment(cells.get("datum"))
        if moment is None:
            problems += 1
            log.add(STEP, "date_invalid", f"Row {number}: the datum can't be read.", params=[_clean(cells.get("datum"))], **where)
        name = split_name(cells.get("ophaler"))
        if name is None:
            problems += 1
            log.add(STEP, "name_required", f"Row {number}: ophaler '{_clean(cells.get('ophaler'))}' is not a first and "
                                           "family name.", **where)
        quantity = parse_quantity(cells.get("aantal"))
        if quantity is None:
            problems += 1
            log.add(STEP, "quantity_invalid", f"Row {number}: aantal '{_clean(cells.get('aantal'))}' can't be used.",
                    params=[_clean(cells.get("aantal"))], **where)
        subtype = split_subtype(cells.get("product subtype"))
        if subtype is None:
            problems += 1
            log.add(STEP, "fit_unknown", f"Row {number}: subtype '{_clean(cells.get('product subtype'))}' has no known "
                                         "fit + size.", params=[_clean(cells.get("product subtype"))], **where)
        team, article = _clean(cells.get("group")), _clean(cells.get("product"))
        if not team or not article:
            problems += 1
            log.add(STEP, "column_missing", f"Row {number}: group or product is empty.",
                    params=["group" if not team else "product"], **where)
        if problems:
            continue

        lines.append({
            "booked_at": moment.strftime("%Y-%m-%d %H:%M:%S"),
            "day": moment.date().isoformat(),
            "festival": None,
            "team": team,
            "first_name": name[0],
            "last_name": name[1],
            "email": None,
            "article": article,
            "fit": subtype[0],
            "size": subtype[1],
            "action": PICK_UP if quantity > 0 else RETURN,
            "quantity": abs(quantity),
            "source_file": source.name,
            "source_row": number,
            "source_values": source_values,
        })

    # In time order; rows of the same moment, person, team and direction
    # are one transaction.
    lines.sort(key=lambda line: (line["booked_at"], line["source_row"]))
    transactions: dict[tuple, str] = {}
    for line in lines:
        key = (line["booked_at"], f"{line['first_name']} {line['last_name']}".lower(), line["team"].lower(), line["action"])
        line["transaction"] = transactions.setdefault(key, f"T{len(transactions) + 1:05d}")
    return {ATELIER_DESK: (ATELIER_DESK_COLUMNS, lines)}
