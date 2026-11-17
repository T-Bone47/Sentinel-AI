"""
Failed-login throttle: after MAX_FAILURES wrong passwords for one email the
account is locked for LOCK_SECONDS, and even the correct password is refused.

Keyed by the submitted email whether or not such an account exists, so the
lockout cannot be used to find out which addresses are registered.

# ponytail: in-memory and per-process. State is lost on restart and each
# worker counts separately, so N workers allow N x MAX_FAILURES guesses per
# window. Move to a shared store (database or Redis) and add per-IP limiting
# at the reverse proxy before running more than one worker.

Known trade-off: anyone who knows an email address can lock that account for
LOCK_SECONDS by failing on purpose. That is accepted here in exchange for
stopping password guessing; the lock expires on its own.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60
LOCK_SECONDS = 15 * 60
MAX_TRACKED = 10_000


class LoginThrottle:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._entries: dict[str, tuple[int, float]] = {}  # key -> (failures, expires_at)

    @staticmethod
    def _key(email: str) -> str:
        return email.strip().lower()

    def retry_after(self, email: str) -> int:
        """Seconds until this email may try again; 0 when it is not locked."""
        entry = self._entries.get(self._key(email))
        if entry is None:
            return 0
        failures, expires_at = entry
        remaining = expires_at - self._clock()
        if remaining <= 0:
            self._entries.pop(self._key(email), None)
            return 0
        return math.ceil(remaining) if failures >= MAX_FAILURES else 0

    def record_failure(self, email: str) -> None:
        key, now = self._key(email), self._clock()
        failures, expires_at = self._entries.get(key, (0, 0.0))
        if expires_at <= now:
            failures, expires_at = 0, now + WINDOW_SECONDS
        failures += 1
        if failures >= MAX_FAILURES:
            expires_at = now + LOCK_SECONDS
        self._entries.pop(key, None)  # re-insert so eviction order is by last failure
        self._entries[key] = (failures, expires_at)
        while len(self._entries) > MAX_TRACKED:
            self._entries.pop(self._eviction_candidate(now))

    def _eviction_candidate(self, now: float) -> str:
        """Oldest entry that is not an active lock. Evicting locks first would
        let anyone lift a lockout by failing on enough throwaway addresses.
        # ponytail: linear scan over the oldest entries, at most MAX_TRACKED;
        # negligible next to the bcrypt check every failure already costs.
        Only when every tracked entry is an active lock is the oldest lock
        dropped — reaching that takes MAX_FAILURES x MAX_TRACKED failed
        sign-ins inside one lock period."""
        for key, (failures, expires_at) in self._entries.items():
            if failures < MAX_FAILURES or expires_at <= now:
                return key
        return next(iter(self._entries))

    def record_success(self, email: str) -> None:
        self._entries.pop(self._key(email), None)

    def reset(self) -> None:
        self._entries.clear()


throttle = LoginThrottle()
