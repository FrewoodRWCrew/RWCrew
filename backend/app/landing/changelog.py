# The changelog behind the super admin's "Wijzigingen" screen.
#
# Localhost, test and production must show exactly the same list, so no
# environment keeps its own copy: every backend reads the one changelog.json on
# the repository's "changelog" branch, at runtime. That branch isn't deployed
# (the deploy workflows only run on develop and main), so a changed line shows
# everywhere within a minute without a deploy.

import logging
import time

import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import settings
from app.schemas.changelog import ChangelogEntry

logger = logging.getLogger(__name__)

CHANGELOG_URL = "https://api.github.com/repos/FrewoodRWCrew/RWCrew/contents/changelog.json?ref=changelog"

# How long a fetched list is reused, so opening the screen doesn't call GitHub
# every time (and a GitHub outage doesn't slow down every request).
CACHE_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 5

_entries_adapter = TypeAdapter(list[ChangelogEntry])

# The last good list and when GitHub was last asked (monotonic clock).
_cached_entries: list[ChangelogEntry] | None = None
_cached_at = 0.0


class ChangelogUnavailable(Exception):
    """GitHub can't be reached and no earlier copy of the list is available."""


def parse_changelog(content: str | bytes) -> list[ChangelogEntry]:
    """Validate the file's content and return its lines, newest on top.

    Raises ValueError on anything invalid: broken JSON, a wrong field (such as
    a line without a date or a shortened commit hash) or a duplicate id.
    """
    try:
        entries = _entries_adapter.validate_json(content)
    except ValidationError as error:
        raise ValueError(str(error)) from error

    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate id in changelog.json")

    # Newest date first; within one day the line added last comes first.
    return sorted(entries, key=lambda entry: (entry.date, entry.id), reverse=True)


def _fetch_from_github() -> list[ChangelogEntry]:
    """Download and validate the file. Raises on any network or content problem."""
    # This "raw" media type returns the file itself instead of a JSON wrapper
    # with base64 content. The token is optional: it only lifts GitHub's limit
    # on anonymous calls.
    headers = {"Accept": "application/vnd.github.raw+json"}
    if settings.changelog_github_token:
        headers["Authorization"] = f"Bearer {settings.changelog_github_token}"

    response = httpx.get(CHANGELOG_URL, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return parse_changelog(response.content)


def get_changelog() -> list[ChangelogEntry]:
    """Return the list, from the short cache or else fresh from GitHub.

    When GitHub fails the last good copy keeps being served; only without any
    copy at all (first request after a start) does this raise.
    """
    global _cached_entries, _cached_at

    now = time.monotonic()
    if _cached_entries is not None and now - _cached_at < CACHE_SECONDS:
        return _cached_entries

    try:
        _cached_entries = _fetch_from_github()
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("Could not load changelog.json from GitHub: %s", error)
        if _cached_entries is None:
            raise ChangelogUnavailable from error

    _cached_at = now
    return _cached_entries


def reset_cache() -> None:
    """Forget the cached list (used by the tests)."""
    global _cached_entries, _cached_at
    _cached_entries = None
    _cached_at = 0.0
