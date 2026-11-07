# Shared helpers for admin-editable mail texts ("Instellingen > E-mails" in
# Atelier and Altsien Select): a subject and body written as plain text with
# placeholders such as {voornaam}. Each module keeps its own placeholder list,
# default texts and template table; this file only finds unknown placeholders
# and fills a text in (plain text + escaped HTML), the same way for every module.

import re
from collections.abc import Iterable
from dataclasses import dataclass
from html import escape

# A placeholder in a text: a name between curly braces.
PLACEHOLDER_PATTERN = re.compile(r"\{([^{}\s]*)\}")


def unknown_placeholders(text: str, known: Iterable[str]) -> list[str]:
    """The placeholders in a text that are not in `known` (in order, once each)."""
    allowed = set(known)
    found: list[str] = []
    for name in PLACEHOLDER_PATTERN.findall(text):
        if name not in allowed and name not in found:
            found.append(name)
    return found


def fill(text: str, values: dict[str, str], *, html: bool) -> str:
    """Replace the placeholders by their values; for HTML both the text and
    the values are escaped and line breaks become <br>."""

    def value_of(match: re.Match) -> str:
        name = match.group(1)
        # An unknown placeholder (can't be saved, but just in case) stays as typed.
        if name not in values:
            return match.group(0)
        return escape(values[name]) if html else values[name]

    if not html:
        return PLACEHOLDER_PATTERN.sub(value_of, text)
    # Escaping leaves the braces alone, so the placeholders are still found.
    return PLACEHOLDER_PATTERN.sub(value_of, escape(text)).replace("\n", "<br>")


@dataclass(frozen=True)
class RenderedMail:
    """A template filled in with values: subject + plain text + HTML."""

    subject: str
    text: str
    html: str


def render(subject: str, body: str, values: dict[str, str]) -> RenderedMail:
    """Fill in a subject and body (the subject without the environment's prefix)."""
    # A subject is one line: line breaks in values become spaces.
    one_line = {name: " ".join(value.split()) for name, value in values.items()}
    return RenderedMail(
        subject=fill(subject, one_line, html=False),
        text=fill(body, values, html=False),
        html=f'<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937">{fill(body, values, html=True)}</div>',
    )
