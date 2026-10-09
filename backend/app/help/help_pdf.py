# Draws a module's help manual (parsed by content.py) as a PDF in the
# TeamKar house style, coloured in the module's own accent:
#   - full manual: a title page (logo, title, version, for whom), a
#     clickable table of contents, then one chapter per page for every
#     screen the user may view (PDF bookmarks come for free);
#   - one topic (the per-screen (?) button): just that chapter.
#
# fpdf2's built-in Helvetica only knows latin-1, so all text goes through
# pdf_text() first (app/shared/pdf_common.py).

from collections.abc import Collection
from functools import lru_cache

from fpdf import FPDF
from fpdf.outline import OutlineSection
from PIL import Image

from app.core.config import settings
from app.core.timezone import belgian_now
from app.help.content import Block, Chapter, Manual, load_manual
from app.shared.pdf_common import BORDER_COLOR, MUTED_TEXT, TEAMKAR_LOGO_RATIO, TEXT_DARK, pdf_text, teamkar_logo

# Each module's accent (the 600 shade of its colour in
# frontend/src/lib/module-theme.ts), used for bands, bars and numbers.
MODULE_ACCENTS: dict[str, tuple[int, int, int]] = {
    "module-1": (37, 99, 235),  # blue
    "module-2": (147, 51, 234),  # purple
    "module-3": (234, 88, 12),  # orange
    "module-4": (13, 148, 136),  # teal
    "module-8": (192, 38, 211),  # fuchsia
    "module-9": (8, 145, 178),  # cyan
}
DEFAULT_ACCENT = (22, 163, 74)

LABELS = {
    "nl": {
        "manual": "Handleiding",
        "contents": "Inhoud",
        "page": "pagina {page} / {pages}",
        "version": "Versie {version}",
        "made_for": "Opgemaakt voor {name} op {date}",
        "rights_note": "Deze handleiding toont enkel de schermen waar jij toegang toe hebt.",
        "tip": "Tip:",
    },
    "en": {
        "manual": "User guide",
        "contents": "Contents",
        "page": "page {page} / {pages}",
        "version": "Version {version}",
        "made_for": "Prepared for {name} on {date}",
        "rights_note": "This guide only shows the screens you have access to.",
        "tip": "Tip:",
    },
}

# Where the content starts below the running header, in mm.
CONTENT_TOP = 26
BODY_LINE = 5.6
# Screenshots are scaled to the page width, but never taller than this.
MAX_IMAGE_HEIGHT = 125
# Screenshots are embedded at most this many pixels wide (~150 dpi on A4).
PRINT_IMAGE_MAX_PX = 1100


class TopicNotFound(LookupError):
    """The asked topic doesn't exist, or the user may not see it."""


def _tint(color: tuple[int, int, int], share: float) -> tuple[int, int, int]:
    """The colour mixed with white (share = how much of the colour stays)."""
    return tuple(round(255 - (255 - part) * share) for part in color)  # type: ignore[return-value]


@lru_cache(maxsize=64)
def _print_image(path: str, _modified: float) -> Image.Image:
    """A screenshot shrunk to at most PRINT_IMAGE_MAX_PX wide, so the PDF
    stays small (cached; a changed file has a new modification time).
    """
    with Image.open(path) as image:
        picture = image.convert("RGB")
    if picture.width > PRINT_IMAGE_MAX_PX:
        height = round(picture.height * PRINT_IMAGE_MAX_PX / picture.width)
        picture = picture.resize((PRINT_IMAGE_MAX_PX, height), Image.Resampling.LANCZOS)
    return picture


def _version_label() -> str:
    """"2026.10.04 · 97cdc36" on a deployed server, "dev" locally — the same
    label as /api/health.
    """
    return " · ".join(part for part in (settings.app_commit_date, settings.app_commit) if part) or "dev"


class HelpPDF(FPDF):
    """An A4 manual page: thin accent band, small logo and "<module> ·
    Handleiding" on top; module, version and page x / y at the bottom. The
    title page (if any) draws its own top instead of the running header.
    """

    def __init__(self, *, module_title: str, accent: tuple[int, int, int], labels: dict, has_title_page: bool):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.module_title = module_title
        self.accent = accent
        self.labels = labels
        self.has_title_page = has_title_page
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=20)
        self.alias_nb_pages()
        # Store pictures JPEG-compressed: screenshots with maps would make the
        # PDF several MB as lossless images.
        self.set_image_filter("DCTDecode")

    @property
    def usable_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def header(self) -> None:
        """Accent band, small logo, "<module> · Handleiding" right."""
        if self.has_title_page and self.page_no() == 1:
            return
        self.set_fill_color(*self.accent)
        self.rect(0, 0, self.w, 2.5, style="F")
        logo = teamkar_logo()
        if logo is not None:
            self.image(logo, x=self.l_margin, y=6.5, h=10)
        self.set_xy(self.l_margin, 9)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*MUTED_TEXT)
        self.cell(0, 5, pdf_text(f"{self.module_title} · {self.labels['manual']}"), align="R")
        self.set_draw_color(*self.accent)
        self.set_line_width(0.4)
        self.line(self.l_margin, 19.5, self.w - self.r_margin, 19.5)
        self.set_y(CONTENT_TOP)

    def footer(self) -> None:
        """Module, manual and version left, page x / y right."""
        self.set_y(-13)
        self.set_draw_color(*BORDER_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 1.5, self.w - self.r_margin, self.get_y() - 1.5)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED_TEXT)
        left = f"{self.module_title} · {self.labels['manual']} · RWCrew · {self.labels['version'].format(version=_version_label())}"
        self.cell(0, 6, pdf_text(left), align="L")
        self.set_x(self.l_margin)
        self.cell(0, 6, pdf_text(self.labels["page"].format(page=self.page_no(), pages="{nb}")), align="R")

    # --- Building blocks -------------------------------------------------

    def body_text(self, text: str, *, size: float = 10.5, color: tuple[int, int, int] = TEXT_DARK) -> None:
        """A paragraph; **bold** inside it is drawn bold."""
        self.set_font("Helvetica", "", size)
        self.set_text_color(*color)
        self.multi_cell(0, BODY_LINE, pdf_text(text), markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_heading(self, text: str) -> None:
        """A "###" heading in the module's colour."""
        if self.get_y() > self.h - 50:
            self.add_page()
        self.ln(1.5)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.accent)
        self.multi_cell(0, 6.5, pdf_text(text), align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def numbered_steps(self, items: Collection[str]) -> None:
        """Steps with a filled, numbered circle in front of each."""
        indent = 8.5
        self.set_font("Helvetica", "", 10.5)
        for number, item in enumerate(items, start=1):
            if self.get_y() > self.h - self.b_margin - 12:
                self.add_page()
            top = self.get_y()
            # The circle with its number.
            self.set_fill_color(*self.accent)
            self.ellipse(self.l_margin, top + 0.2, 5.2, 5.2, style="F")
            self.set_xy(self.l_margin, top + 0.2)
            self.set_font("Helvetica", "B", 8.5)
            self.set_text_color(255, 255, 255)
            self.cell(5.2, 5.2, str(number), align="C")
            # The step's text next to it.
            self.set_xy(self.l_margin + indent, top)
            self.set_font("Helvetica", "", 10.5)
            self.set_text_color(*TEXT_DARK)
            self.multi_cell(
                self.usable_width - indent, BODY_LINE, pdf_text(item), markdown=True, align="L",
                new_x="LMARGIN", new_y="NEXT",
            )
            self.ln(1.6)
        self.ln(1)

    def bullets(self, items: Collection[str]) -> None:
        """A list with a small accent square in front of each line."""
        indent = 6
        for item in items:
            if self.get_y() > self.h - self.b_margin - 10:
                self.add_page()
            top = self.get_y()
            self.set_fill_color(*self.accent)
            self.rect(self.l_margin + 1, top + 2, 1.8, 1.8, style="F")
            self.set_xy(self.l_margin + indent, top)
            self.set_font("Helvetica", "", 10.5)
            self.set_text_color(*TEXT_DARK)
            self.multi_cell(
                self.usable_width - indent, BODY_LINE, pdf_text(item), markdown=True, align="L",
                new_x="LMARGIN", new_y="NEXT",
            )
            self.ln(0.8)
        self.ln(1.5)

    def tip(self, text: str) -> None:
        """A tinted box with an accent bar on its left and "Tip:" in bold."""
        padding = 3
        inner_width = self.usable_width - 2 * padding - 2
        content = pdf_text(f"**{self.labels['tip']}** {text}")
        self.set_font("Helvetica", "", 10)
        height = self.multi_cell(inner_width, 5.2, content, markdown=True, dry_run=True, output="HEIGHT")
        box_height = height + 2 * padding
        if self.get_y() + box_height > self.h - self.b_margin:
            self.add_page()
        top = self.get_y()
        self.set_fill_color(*_tint(self.accent, 0.12))
        self.rect(self.l_margin, top, self.usable_width, box_height, style="F")
        self.set_fill_color(*self.accent)
        self.rect(self.l_margin, top, 1.4, box_height, style="F")
        self.set_xy(self.l_margin + 2 + padding, top + padding)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(inner_width, 5.2, content, markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_y(top + box_height + 3)

    def screenshot(self, path, caption: str) -> None:
        """A screenshot scaled to the page width (never taller than
        MAX_IMAGE_HEIGHT), with a thin border and an optional caption.
        A missing file is skipped: the text still makes sense without it.
        """
        if not path.exists():
            return
        image = _print_image(str(path), path.stat().st_mtime)
        pixel_width, pixel_height = image.size
        width = self.usable_width
        height = width * pixel_height / pixel_width
        if height > MAX_IMAGE_HEIGHT:
            height = MAX_IMAGE_HEIGHT
            width = height * pixel_width / pixel_height
        needed = height + (8 if caption else 3)
        if self.get_y() + needed > self.h - self.b_margin:
            self.add_page()
        left = self.l_margin + (self.usable_width - width) / 2
        top = self.get_y() + 1
        self.image(image, x=left, y=top, w=width, h=height)
        self.set_draw_color(*BORDER_COLOR)
        self.set_line_width(0.3)
        self.rect(left, top, width, height)
        self.set_y(top + height + 1.5)
        if caption:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*MUTED_TEXT)
            self.multi_cell(0, 4.5, pdf_text(caption), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def blocks(self, blocks: Collection[Block], manual: Manual) -> None:
        """Draw a list of blocks, each with its own building block above."""
        for block in blocks:
            if block.kind == "heading":
                self.sub_heading(block.text)
            elif block.kind == "paragraph":
                self.body_text(block.text)
            elif block.kind == "steps":
                self.numbered_steps(block.items)
            elif block.kind == "bullets":
                self.bullets(block.items)
            elif block.kind == "tip":
                self.tip(block.text)
            elif block.kind == "image":
                self.screenshot(manual.images_dir / block.image, block.text)

    def chapter(self, chapter: Chapter, manual: Manual) -> None:
        """One chapter, on a page of its own, with an entry in the table of
        contents and the PDF bookmarks.
        """
        # A fresh page right after the header doesn't need another break.
        if self.page == 0 or self.get_y() > CONTENT_TOP + 1:
            self.add_page()
        self.start_section(pdf_text(chapter.title))
        top = self.get_y()
        self.set_fill_color(*self.accent)
        self.rect(self.l_margin, top + 1.5, 2, 8, style="F")
        self.set_xy(self.l_margin + 5, top)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(self.usable_width - 5, 11, pdf_text(chapter.title), align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.blocks(chapter.blocks, manual)


def _title_page(pdf: HelpPDF, manual: Manual, printed_for: str | None) -> None:
    """Big logo, the module's name, "Handleiding", the intro and the
    version / for whom lines at the bottom.
    """
    pdf.add_page()
    pdf.set_fill_color(*pdf.accent)
    pdf.rect(0, 0, pdf.w, 8, style="F")

    # The logo, centred.
    logo = teamkar_logo()
    logo_height = 34
    if logo is not None:
        pdf.image(logo, x=(pdf.w - logo_height * TEAMKAR_LOGO_RATIO) / 2, y=30, h=logo_height)

    # Title and subtitle.
    pdf.set_y(76)
    pdf.set_font("Helvetica", "B", 30)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 14, pdf_text(manual.title), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(*pdf.accent)
    pdf.cell(0, 9, pdf_text(pdf.labels["manual"]), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*pdf.accent)
    pdf.set_line_width(0.6)
    pdf.line(pdf.w / 2 - 20, pdf.get_y() + 4, pdf.w / 2 + 20, pdf.get_y() + 4)
    pdf.ln(12)

    # The intro text of the manual.
    pdf.blocks(manual.intro, manual)

    # Version, for whom, and that only the user's own screens are in it.
    pdf.set_y(pdf.h - 48)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*MUTED_TEXT)
    lines = [pdf.labels["version"].format(version=_version_label())]
    if printed_for:
        lines.append(pdf.labels["made_for"].format(name=printed_for, date=belgian_now().strftime("%d-%m-%Y %H:%M")))
    lines.append(pdf.labels["rights_note"])
    for line in lines:
        pdf.cell(0, 5.5, pdf_text(line), align="C", new_x="LMARGIN", new_y="NEXT")


def _render_toc(pdf: HelpPDF, outline: list[OutlineSection]) -> None:
    """The table of contents: one clickable line per chapter with a dotted
    leader and its page number.
    """
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 11, pdf_text(pdf.labels["contents"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for section in outline:
        link = pdf.add_link(page=section.page_number)
        number = str(section.page_number)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*TEXT_DARK)
        name = section.name
        number_width = pdf.get_string_width(number) + 2
        name_width = pdf.get_string_width(name) + 2
        dots_width = pdf.usable_width - name_width - number_width
        dots = "." * max(int(dots_width / pdf.get_string_width(".")) - 1, 0)
        pdf.cell(name_width, 8, name, link=link)
        pdf.set_text_color(*BORDER_COLOR)
        pdf.cell(dots_width, 8, dots, align="R", link=link)
        pdf.set_text_color(*pdf.accent)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(number_width, 8, number, align="R", link=link, new_x="LMARGIN", new_y="NEXT")


def visible_chapters(manual: Manual, viewable_screen_keys: Collection[str]) -> list[Chapter]:
    """The chapters this user gets: those without a screen, and those of a
    screen they may view.
    """
    return [
        chapter
        for chapter in manual.chapters
        if chapter.screen_key is None or chapter.screen_key in viewable_screen_keys
    ]


def build_help_pdf(
    module_key: str,
    locale: str,
    viewable_screen_keys: Collection[str],
    *,
    topic: str | None = None,
    printed_for: str | None = None,
) -> bytes:
    """The module's manual as PDF bytes. Without `topic`: the whole manual
    with only the chapters of screens in `viewable_screen_keys`. With
    `topic`: only that chapter (TopicNotFound if it doesn't exist or its
    screen isn't viewable).
    """
    manual = load_manual(module_key, locale)
    visible = visible_chapters(manual, viewable_screen_keys)
    labels = LABELS.get(locale, LABELS["nl"])
    accent = MODULE_ACCENTS.get(module_key, DEFAULT_ACCENT)

    if topic is not None:
        chosen = [chapter for chapter in visible if chapter.topic == topic]
        if not chosen:
            raise TopicNotFound(topic)
        pdf = HelpPDF(module_title=manual.title, accent=accent, labels=labels, has_title_page=False)
        pdf.set_title(pdf_text(f"{manual.title} - {chosen[0].title}"))
        pdf.chapter(chosen[0], manual)
        return bytes(pdf.output())

    pdf = HelpPDF(module_title=manual.title, accent=accent, labels=labels, has_title_page=True)
    pdf.set_title(pdf_text(f"{manual.title} - {labels['manual']}"))
    _title_page(pdf, manual, printed_for)
    # Page 2: the table of contents, filled in once every chapter is drawn.
    pdf.add_page()
    pdf.insert_toc_placeholder(_render_toc, pages=1)
    for chapter in visible:
        pdf.chapter(chapter, manual)
    return bytes(pdf.output())
