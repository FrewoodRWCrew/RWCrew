# Reads a module's help manual from its Markdown files
# (app/help/content/<module_N>/<locale>.md) into chapters the PDF builder
# (help_pdf.py) can draw. The format is a small, fixed subset of Markdown so
# the texts can be edited without touching code:
#
#   # StockMaster                              <- manual title (first line)
#   Intro paragraph...                         <- shown on the title page
#
#   ## [book-in | stockmaster.stock] Inboeken  <- chapter: [topic | screen key]
#   ### Sub heading
#   A paragraph; consecutive lines are joined.
#   1. A numbered step
#   - A bullet
#   > A tip, shown in a coloured box
#   ![Caption](book-in.png)                    <- screenshot from images/
#
# The topic is the chapter's stable id: the per-screen (?) button asks for
# it. The screen key decides who sees the chapter (the "view" right on that
# screen); a chapter without one ("## [start] Zo werkt ...") is always shown.
# **bold** inside a line is kept and drawn bold.

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "content"

# "## [topic | screen.key] Title" or "## [topic] Title".
_CHAPTER_RE = re.compile(r"^##\s+\[\s*([\w-]+)\s*(?:\|\s*([\w.-]+)\s*)?\]\s*(.+)$")
_STEP_RE = re.compile(r"^\d+[.)]\s+(.+)$")
_IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.+?)\)$")


@dataclass(frozen=True)
class Block:
    """One piece of a chapter: kind is heading / paragraph / steps /
    bullets / tip / image. `text` holds the text (or the image caption),
    `items` the lines of a list, `image` the picture's file name.
    """

    kind: str
    text: str = ""
    items: tuple[str, ...] = ()
    image: str = ""


@dataclass
class Chapter:
    """One "##" chapter of the manual."""

    topic: str
    screen_key: str | None
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Manual:
    """A whole parsed manual: its title, the intro and the chapters."""

    title: str
    intro: list[Block]
    chapters: list[Chapter]
    # The folder the manual's screenshots are read from.
    images_dir: Path


def content_folder(module_key: str) -> Path:
    """The folder holding one module's manual ("module-4" -> module_4/)."""
    return CONTENT_DIR / module_key.replace("-", "_")


def has_manual(module_key: str, locale: str) -> bool:
    """Whether this module has a manual in this language."""
    return (content_folder(module_key) / f"{locale}.md").exists()


def parse_manual(text: str, images_dir: Path) -> Manual:
    """Turn the Markdown text of one manual into a Manual."""
    title = ""
    intro: list[Block] = []
    chapters: list[Chapter] = []

    # Blocks go to the current chapter, or to the intro before the first one.
    def target() -> list[Block]:
        return chapters[-1].blocks if chapters else intro

    # Lines of the list/paragraph/tip being collected, flushed into a block
    # when something of a different kind (or a blank line) follows.
    pending_kind: str | None = None
    pending: list[str] = []

    def flush() -> None:
        nonlocal pending_kind, pending
        if pending_kind in ("paragraph", "tip"):
            target().append(Block(pending_kind, text=" ".join(pending)))
        elif pending_kind in ("steps", "bullets"):
            target().append(Block(pending_kind, items=tuple(pending)))
        pending_kind, pending = None, []

    def collect(kind: str, line: str) -> None:
        nonlocal pending_kind
        if pending_kind != kind:
            flush()
            pending_kind = kind
        pending.append(line)

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # A blank line ends whatever was being collected.
        if not line:
            flush()
            continue

        # The manual's title: the first "# " line.
        if line.startswith("# ") and not title:
            flush()
            title = line[2:].strip()
            continue

        # A new chapter.
        chapter_match = _CHAPTER_RE.match(line)
        if chapter_match:
            flush()
            topic, screen_key, chapter_title = chapter_match.groups()
            chapters.append(Chapter(topic=topic, screen_key=screen_key, title=chapter_title.strip()))
            continue

        # A sub heading inside a chapter.
        if line.startswith("### "):
            flush()
            target().append(Block("heading", text=line[4:].strip()))
            continue

        # A screenshot on its own line.
        image_match = _IMAGE_RE.match(line)
        if image_match:
            flush()
            caption, file_name = image_match.groups()
            target().append(Block("image", text=caption.strip(), image=file_name.strip()))
            continue

        # Numbered steps, bullets and tips; a line that continues one of
        # them (indented, no marker) is added to its last item.
        step_match = _STEP_RE.match(line)
        if step_match:
            collect("steps", step_match.group(1))
        elif line.startswith(("- ", "* ")):
            collect("bullets", line[2:].strip())
        elif line.startswith(">"):
            collect("tip", line[1:].strip())
        elif pending_kind in ("steps", "bullets") and raw_line[:1].isspace():
            pending[-1] += " " + line
        else:
            collect("paragraph", line)

    flush()
    return Manual(title=title, intro=intro, chapters=chapters, images_dir=images_dir)


@lru_cache(maxsize=32)
def load_manual(module_key: str, locale: str) -> Manual:
    """Read and parse one module's manual (cached: the backend restarts on
    every deploy, which is when the texts change).
    """
    folder = content_folder(module_key)
    text = (folder / f"{locale}.md").read_text(encoding="utf-8")
    return parse_manual(text, folder / "images")
