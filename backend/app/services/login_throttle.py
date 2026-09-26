"""Brute-force protection for the login endpoint.

Failed attempts are counted per (client IP, e-mail) in a sliding time window. Keying by
both slows down password guessing from one source without letting a stranger lock a
victim out of their account from elsewhere (which a per-e-mail lock would allow).

[PORTFOLIO] The counters live in process memory: they reset on restart and are not
shared between workers. [PROD] Use a shared store (e.g. Redis) or the API gateway / WAF
rate limiting, plus alerts on repeated failures.
"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock

from app.core.exceptions import TooManyRequestsError


class LoginThrottle:
    def __init__(
        self,
        max_failures: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()  # requests run in a thread pool

    def _recent(self, key: str, now: float) -> deque[float]:
        attempts = self._failures[key]
        while attempts and now - attempts[0] >= self.window_seconds:
            attempts.popleft()
        return attempts

    def check(self, key: str) -> None:
        """Raise 429 while `key` has too many recent failures."""
        with self._lock:
            now = self._clock()
            attempts = self._recent(key, now)
            if len(attempts) >= self.max_failures:
                retry_after = math.ceil(self.window_seconds - (now - attempts[0]))
                raise TooManyRequestsError(
                    "Too many failed login attempts. Try again later.",
                    retry_after=retry_after,
                )

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._recent(key, now).append(now)

    def reset(self, key: str | None = None) -> None:
        """Forget failures for `key` (after a successful login), or everything."""
        with self._lock:
            if key is None:
                self._failures.clear()
            else:
                self._failures.pop(key, None)
