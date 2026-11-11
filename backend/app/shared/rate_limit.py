# A small in-memory rate limiter for the public (no-login) endpoints: the
# intervention-request form (module-3) and the kar inventory (module-4).
#
# "At most N hits per key (usually the client's IP) in a sliding window of W
# seconds." Kept in memory, which is fine because the backend runs as ONE
# uvicorn process per environment (see CLAUDE.md, TagScan's auto scan); if
# workers are ever added, each would count on its own.

import heapq
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

# Keep lock-held cleanup bounded even when many different keys have been seen
# since the last hit.
_CLEANUP_MAX_REMOVALS = 32


def client_ip(request: Request) -> str:
    """The caller's address as uvicorn sees it ("unknown" without one)."""
    return request.client.host if request.client is not None else "unknown"


class SlidingWindowLimiter:
    """Counts hits per key and says when a key went over its limit."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        # Per key the moments of its recent hits, oldest first.
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        # (expiry moment, key) of every hit, so stale keys can be dropped.
        self._expiries: list[tuple[float, str]] = []
        self._lock = Lock()

    def _prune(self, now: float) -> None:
        """Drop at most a fixed number of expired keys (lock already held).
        The heap stores absolute expiry times, so compare them with now."""
        cutoff = now - self.window_seconds
        removals = 0
        while self._expiries and self._expiries[0][0] <= now:
            _, key = heapq.heappop(self._expiries)
            hits = self._hits.get(key)
            if hits is None:
                continue
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]
            removals += 1
            if removals >= _CLEANUP_MAX_REMOVALS:
                break

    def _recent(self, key: str, now: float) -> deque[float]:
        """The key's hits inside the window (lock already held)."""
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        return hits

    def hit(self, key: str) -> bool:
        """Count one hit for `key`; False (and not counted) when the key
        already reached its limit in the window."""
        now = monotonic()
        with self._lock:
            self._prune(now)
            hits = self._recent(key, now)
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            heapq.heappush(self._expiries, (now + self.window_seconds, key))
            return True

    def is_blocked(self, key: str) -> bool:
        """True while `key` is at its limit, without counting a hit."""
        now = monotonic()
        with self._lock:
            blocked = len(self._recent(key, now)) >= self.limit
            if not self._hits[key]:
                del self._hits[key]
            return blocked

    def seconds_left(self, key: str) -> int:
        """How long until the key's oldest hit leaves the window (0 when free)."""
        now = monotonic()
        with self._lock:
            hits = self._recent(key, now)
            if len(hits) < self.limit or not hits:
                return 0
            return max(int(hits[0] + self.window_seconds - now) + 1, 1)

    def clear(self, key: str) -> None:
        """Forget a key's hits (e.g. after a correct code)."""
        with self._lock:
            self._hits.pop(key, None)

    def reset(self) -> None:
        """Forget everything (tests)."""
        with self._lock:
            self._hits.clear()
            self._expiries.clear()

    def enforce(self, request: Request) -> None:
        """Count a hit for the caller's IP; 429 when over the limit."""
        if not self.hit(client_ip(request)):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
