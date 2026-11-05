# The mass test's connection to RWCrew: logs in like a person (the cookie
# login of /api/auth/login), refreshes the session once on a 401, and times
# every call so slow endpoints end up in the report.

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

# A call slower than this (seconds) is reported as a performance issue.
SLOW_CALL_SECONDS = 2.0


@dataclass
class CallResult:
    """What one API call gave back: status, body (JSON when possible) and
    how long it took."""

    method: str
    path: str
    status: int
    body: Any
    seconds: float

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def detail(self) -> str:
        """The API's error detail ("code|param|…"), or the raw body."""
        if isinstance(self.body, dict) and "detail" in self.body:
            detail = self.body["detail"]
            return detail if isinstance(detail, str) else str(detail)
        return str(self.body)[:500]


@dataclass
class Timing:
    """Durations per endpoint (method + path template), for the summary."""

    calls: dict[str, list[float]] = field(default_factory=dict)

    def add(self, key: str, seconds: float) -> None:
        self.calls.setdefault(key, []).append(seconds)


class ApiClient:
    """A logged-in session on one environment's API."""

    def __init__(self, base_url: str, timeout: float = 60.0, transport: httpx.BaseTransport | None = None) -> None:
        self.http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        self.timing = Timing()

    def login(self, email: str, password: str) -> CallResult:
        """Log in through the normal login endpoint; the cookies stay on the client."""
        return self._send("POST", "/api/auth/login", "/api/auth/login", json={"email": email, "password": password, "client": "web"})

    def call(self, method: str, path: str, *, template: str | None = None, **kwargs: Any) -> CallResult:
        """One API call; after a 401 the session is refreshed once and the
        call repeated. `template` names the endpoint in the timing summary
        (e.g. "/desk/persons/{id}/open") so calls with ids add up."""
        result = self._send(method, path, template or path, **kwargs)
        if result.status == 401:
            refresh = self._send("POST", "/api/auth/refresh", "/api/auth/refresh")
            if refresh.ok:
                result = self._send(method, path, template or path, **kwargs)
        return result

    def _send(self, method: str, path: str, template: str, **kwargs: Any) -> CallResult:
        """Send, time and decode one request. A network failure becomes
        status 0 with the error text as body, so it can be reported too."""
        started = time.perf_counter()
        try:
            response = self.http.request(method, path, **kwargs)
            status = response.status_code
            try:
                body = response.json()
            except ValueError:
                body = response.text[:2000]
        except httpx.HTTPError as error:
            status, body = 0, f"{type(error).__name__}: {error}"
        seconds = time.perf_counter() - started
        self.timing.add(f"{method} {template}", seconds)
        return CallResult(method, path, status, body, seconds)

    def close(self) -> None:
        self.http.close()
