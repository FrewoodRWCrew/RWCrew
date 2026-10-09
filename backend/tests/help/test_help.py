# The module help manuals: the Markdown parser, the content of every
# manual (chapters point to real screens, both languages match, screenshots
# exist) and the PDF builder.

from pathlib import Path

import pytest

from app.help.content import CONTENT_DIR, load_manual, parse_manual
from app.help.help_pdf import TopicNotFound, build_help_pdf, visible_chapters
from app.modules.module_1.screens import SCREEN_DEFINITIONS as TAGSCAN_SCREENS
from app.modules.module_2.screens import SCREEN_DEFINITIONS as KARTRACKER_SCREENS
from app.modules.module_4.screens import SCREEN_DEFINITIONS as STOCKMASTER_SCREENS

# Every module with a manual, and the screen keys its chapters may use.
MANUAL_SCREENS: dict[str, set[str]] = {
    "module-1": {definition.key for definition in TAGSCAN_SCREENS},
    "module-2": {definition.key for definition in KARTRACKER_SCREENS},
    "module-4": {definition.key for definition in STOCKMASTER_SCREENS},
}
LOCALES = ("nl", "en")


def test_parser_reads_every_block_kind() -> None:
    manual = parse_manual(
        "\n".join(
            [
                "# Module",
                "Intro **bold**",
                "on two lines.",
                "",
                "## [start] Getting started",
                "### Sub",
                "1. First",
                "2. Second",
                "   continued",
                "- Bullet",
                "> A tip",
                "> on two lines",
                "![Caption](shot.png)",
                "",
                "## [stock | module.stock] Stock",
                "Text",
            ]
        ),
        Path("images"),
    )

    assert manual.title == "Module"
    assert [block.text for block in manual.intro] == ["Intro **bold** on two lines."]
    start, stock = manual.chapters
    assert (start.topic, start.screen_key, start.title) == ("start", None, "Getting started")
    assert [block.kind for block in start.blocks] == ["heading", "steps", "bullets", "tip", "image"]
    assert start.blocks[1].items == ("First", "Second continued")
    assert start.blocks[3].text == "A tip on two lines"
    assert (start.blocks[4].text, start.blocks[4].image) == ("Caption", "shot.png")
    assert (stock.topic, stock.screen_key) == ("stock", "module.stock")


@pytest.mark.parametrize("module_key", MANUAL_SCREENS)
def test_manual_content_is_consistent(module_key: str) -> None:
    manuals = {locale: load_manual(module_key, locale) for locale in LOCALES}
    for locale, manual in manuals.items():
        # Every chapter's screen exists, and topics are unique.
        topics = [chapter.topic for chapter in manual.chapters]
        assert len(topics) == len(set(topics)), locale
        unknown = {chapter.screen_key for chapter in manual.chapters} - MANUAL_SCREENS[module_key] - {None}
        assert not unknown, (locale, unknown)
        # Every screenshot that is referenced is there.
        for chapter in manual.chapters:
            for block in chapter.blocks:
                if block.kind == "image":
                    assert (manual.images_dir / block.image).exists(), (locale, block.image)

    # Both languages have the same chapters in the same order.
    shape = {locale: [(c.topic, c.screen_key) for c in manual.chapters] for locale, manual in manuals.items()}
    assert shape["nl"] == shape["en"]


def test_every_content_folder_is_tested() -> None:
    folders = {folder.name for folder in CONTENT_DIR.iterdir() if folder.is_dir()}
    assert folders == {key.replace("-", "_") for key in MANUAL_SCREENS}


def test_chapters_follow_the_viewable_screens() -> None:
    manual = load_manual("module-4", "nl")

    topics = [chapter.topic for chapter in visible_chapters(manual, {"stockmaster.stock"})]

    # The general chapters plus the ones about the stock screen only.
    assert topics == ["start", "booking", "stock", "book-in", "book-out"]


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("module_key", MANUAL_SCREENS)
def test_pdf_renders_full_and_per_topic(module_key: str, locale: str) -> None:
    every_screen = MANUAL_SCREENS[module_key]
    last_topic = load_manual(module_key, locale).chapters[-1].topic

    full = build_help_pdf(module_key, locale, every_screen, printed_for="Tester")
    one = build_help_pdf(module_key, locale, every_screen, topic=last_topic)

    assert full.startswith(b"%PDF") and one.startswith(b"%PDF")
    assert len(one) < len(full)


def test_hidden_or_unknown_topic_is_refused() -> None:
    with pytest.raises(TopicNotFound):
        build_help_pdf("module-4", "nl", {"stockmaster.stock"}, topic="kar-return")
    with pytest.raises(TopicNotFound):
        build_help_pdf("module-4", "nl", {"stockmaster.stock"}, topic="nope")
