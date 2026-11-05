# The standard load workbook: one sheet per kind of data (named after the
# runner's step), a header row and one row per source line. A converter
# writes it from an old list; a person reviews/corrects it; the runner reads it.

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

# The Atelier desk sheet (Uitgifte/Inname): one row per source line,
# "transaction" groups the rows booked together.
ATELIER_DESK = "AtelierDesk"
ATELIER_DESK_COLUMNS = [
    "transaction", "action", "booked_at", "day", "festival", "team", "first_name", "last_name", "email",
    "article", "fit", "size", "quantity", "source_file", "source_row", "source_values",
]
# The two desk actions.
PICK_UP = "ophalen"
RETURN = "terugbrengen"


def write_sheets(path: Path, sheets: dict[str, tuple[list[str], list[dict]]]) -> Path:
    """Write the load workbook: per sheet its columns and rows (dicts)."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, (columns, rows) in sheets.items():
        sheet = workbook.create_sheet(name)
        sheet.append(columns)
        for row in rows:
            sheet.append([row.get(column) for column in columns])
        for index, column in enumerate(columns, start=1):
            sheet.cell(row=1, column=index).font = Font(bold=True)
            sheet.column_dimensions[get_column_letter(index)].width = max(10, min(40, len(column) + 6))
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return path


def read_sheet(path: Path, name: str) -> list[dict] | None:
    """A sheet's rows as dicts keyed by the (lowercased) header; None when
    the workbook has no such sheet. Fully empty rows are skipped."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if name not in workbook.sheetnames:
            return None
        rows = workbook[name].iter_rows(values_only=True)
        header = [str(cell).strip().lower() if cell is not None else "" for cell in next(rows, ())]
        result = []
        for values in rows:
            if all(value is None or str(value).strip() == "" for value in values):
                continue
            result.append({header[i]: values[i] for i in range(min(len(header), len(values))) if header[i]})
        return result
    finally:
        workbook.close()
