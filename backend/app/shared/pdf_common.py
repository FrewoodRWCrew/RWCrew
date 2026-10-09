# Small pieces every fpdf2 PDF of the app can share: the TeamKar logo
# (shrunk once for printing), the neutral text colours and pdf_text(), which
# makes any value safe for fpdf2's built-in latin-1 Helvetica font.
#
# Used by StockMaster's house style (module_4/pdf_layout.py) and by the
# module help manuals (app/help/help_pdf.py).

from functools import lru_cache
from pathlib import Path

from PIL import Image

# Neutral colours shared by the house-style PDFs.
TEXT_DARK = (31, 41, 55)
MUTED_TEXT = (107, 114, 128)
BORDER_COLOR = (223, 226, 230)

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
TEAMKAR_LOGO = ASSETS_DIR / "teamkar-logo.png"
# The logo's own width:height ratio (1536 x 1024 px).
TEAMKAR_LOGO_RATIO = 1536 / 1024
# The logo is printed ~24 mm wide: 480 px is plenty sharp and keeps every
# PDF small (the full-size image would add ~600 KB to each document).
TEAMKAR_LOGO_PRINT_WIDTH_PX = 480


@lru_cache(maxsize=1)
def teamkar_logo() -> Image.Image | None:
    """The TeamKar logo, shrunk once for printing (None if it's missing)."""
    if not TEAMKAR_LOGO.exists():
        return None
    logo = Image.open(TEAMKAR_LOGO)
    height = round(TEAMKAR_LOGO_PRINT_WIDTH_PX / TEAMKAR_LOGO_RATIO)
    return logo.resize((TEAMKAR_LOGO_PRINT_WIDTH_PX, height), Image.Resampling.LANCZOS)


# Typographic characters people often paste that latin-1 lacks, mapped to
# a close plain equivalent before the generic "?" replacement kicks in.
_TEXT_REPLACEMENTS = {
    "–": "-",
    "—": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "€": "EUR",
    "•": "-",
    "→": "->",
}


def pdf_text(text: object) -> str:
    """Make any value safe for the built-in latin-1 PDF font."""
    if text is None:
        return ""
    value = str(text)
    for character, replacement in _TEXT_REPLACEMENTS.items():
        value = value.replace(character, replacement)
    return value.encode("latin-1", "replace").decode("latin-1")
