# These tests check the changelog behind the super admin's "Wijzigingen"
# screen: only the super admin may read it, the lines come newest first, the
# file is validated strictly, and a GitHub outage doesn't lose the list.
# GitHub itself is never called: httpx.get is replaced in every test.

import json
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models.user import User
from app.landing import changelog
from app.landing.changelog import ChangelogUnavailable, get_changelog, parse_changelog

SHA = "a" * 40


def _line(**overrides: object) -> dict:
    """One valid line of the file, with the given fields changed."""
    line = {
        "id": 1,
        "issues": ["12"],
        "date": "2026-10-29",
        "type": "fix",
        "status": "done",
        "module": "StockMaster",
        "title": "A title",
        "description": "A description",
        "commits": [SHA],
    }
    return line | overrides


class FakeGitHub:
    """Stands in for httpx.get: answers with `body`, or fails while `failing`."""

    def __init__(self, body: list[dict]) -> None:
        self.body = body
        self.failing = False
        self.calls = 0

    def get(self, url: str, **_kwargs: object) -> httpx.Response:
        self.calls += 1
        if self.failing:
            raise httpx.ConnectError("GitHub is down")
        return httpx.Response(200, content=json.dumps(self.body), request=httpx.Request("GET", url))


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    changelog.reset_cache()
    yield
    changelog.reset_cache()


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    fake = FakeGitHub([_line()])
    monkeypatch.setattr(changelog.httpx, "get", fake.get)
    return fake


def _login_as(client: TestClient, db_session: Session, *, is_super_admin: bool) -> None:
    email = "admin@example.com" if is_super_admin else "regular@example.com"
    db_session.add(
        User(email=email, hashed_password=hash_password("password123"), display_name=email, is_super_admin=is_super_admin)
    )
    db_session.commit()
    client.post("/api/auth/login", json={"email": email, "password": "password123"})


def test_non_super_admin_cannot_read_the_changelog(client: TestClient, db_session: Session, github: FakeGitHub) -> None:
    _login_as(client, db_session, is_super_admin=False)

    assert client.get("/api/admin/changelog").status_code == 403
    assert github.calls == 0


def test_super_admin_gets_the_newest_line_on_top(client: TestClient, db_session: Session, github: FakeGitHub) -> None:
    github.body = [
        _line(id=1, date="2026-10-01"),
        _line(id=2, date="2026-10-29"),
        _line(id=3, date="2026-10-29", status="open", commits=[], issues=[]),
    ]
    _login_as(client, db_session, is_super_admin=True)

    response = client.get("/api/admin/changelog")

    assert response.status_code == 200
    body = response.json()
    # Newest date first, and within one day the line added last.
    assert [line["id"] for line in body] == [3, 2, 1]
    assert body[1]["date"] == "2026-10-29"
    assert body[1]["commits"] == [SHA]


def test_unreachable_github_without_a_copy_gives_503(client: TestClient, db_session: Session, github: FakeGitHub) -> None:
    github.failing = True
    _login_as(client, db_session, is_super_admin=True)

    assert client.get("/api/admin/changelog").status_code == 503


def test_list_is_cached_for_a_short_while(github: FakeGitHub) -> None:
    get_changelog()
    get_changelog()

    assert github.calls == 1


def test_last_good_copy_is_served_when_github_fails(github: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    get_changelog()
    # Let the cache run out, then make GitHub fail.
    monkeypatch.setattr(changelog, "_cached_at", -changelog.CACHE_SECONDS * 1000.0)
    github.failing = True

    assert [line.id for line in get_changelog()] == [1]
    assert github.calls == 2


def test_invalid_file_keeps_the_last_good_copy(github: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    get_changelog()
    monkeypatch.setattr(changelog, "_cached_at", -changelog.CACHE_SECONDS * 1000.0)
    github.body = [_line(id=2, commits=["abc123"])]

    assert [line.id for line in get_changelog()] == [1]


def test_invalid_file_without_a_copy_is_unavailable(github: FakeGitHub) -> None:
    github.body = [_line(date="not a date")]

    with pytest.raises(ChangelogUnavailable):
        get_changelog()


@pytest.mark.parametrize(
    "line",
    [
        {key: value for key, value in _line().items() if key != "date"},  # every line needs a date
        _line(commits=["abc123"]),  # shortened commit hash
        _line(commits=["A" * 40]),  # not lowercase hex
        _line(type="bug"),
        _line(status="closed"),
        _line(title=""),
        _line(unknown_field="typo"),
    ],
)
def test_parse_refuses_invalid_lines(line: dict) -> None:
    with pytest.raises(ValueError):
        parse_changelog(json.dumps([line]))


def test_parse_refuses_duplicate_ids_and_broken_json() -> None:
    with pytest.raises(ValueError):
        parse_changelog(json.dumps([_line(), _line()]))
    with pytest.raises(ValueError):
        parse_changelog("{not json")
