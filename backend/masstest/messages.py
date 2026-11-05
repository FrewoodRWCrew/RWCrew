# The text a person would see for an API refusal: the frontend's own
# translation of the "code|param|…" detail (frontend/messages/nl.json), so
# the report reads like the screens do.

import json
from functools import lru_cache
from pathlib import Path

MESSAGES_DIR = Path(__file__).resolve().parents[2] / "frontend" / "messages"

# Where each module keeps the texts of its error codes (first match wins).
ERROR_NAMESPACES = {
    "atelier": (("atelier", "desk", "errors"), ("atelier", "stock", "errors")),
}


@lru_cache(maxsize=4)
def _messages(locale: str) -> dict:
    """The frontend's messages file, or nothing when it isn't there (the
    runner then shows the bare code)."""
    try:
        return json.loads((MESSAGES_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def split_detail(detail: str) -> tuple[str, list[str]]:
    """"code|p1|p2" → ("code", ["p1", "p2"])."""
    code, *params = detail.split("|")
    return code, params


def translate(module: str, detail: str, locale: str = "nl") -> str:
    """The screen text of an error detail, with its {p1}, {p2} … filled in;
    the detail itself when no text exists for the code."""
    code, params = split_detail(detail)
    for path in ERROR_NAMESPACES.get(module, ()):
        node = _messages(locale)
        for part in path:
            node = node.get(part, {}) if isinstance(node, dict) else {}
        text = node.get(code) if isinstance(node, dict) else None
        if isinstance(text, str):
            for index, value in enumerate(params, start=1):
                text = text.replace(f"{{p{index}}}", value)
            return text
    return detail
