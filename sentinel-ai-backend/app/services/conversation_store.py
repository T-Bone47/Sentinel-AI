"""
Short-lived memory for multi-turn AI questions: for each conversation, the
previous question and a one-line summary of its answer.

Every entry belongs to exactly one user. The lookup key is
(user id, conversation id), so knowing or guessing another person's
conversation id gets you nothing — you would be looking in your own
namespace. Entries expire after `ttl_seconds` and the store is bounded.

# ponytail: in-memory and per-process, lost on restart. That is the intended
# lifetime for this data (it is a convenience, not a record). Use a shared
# cache with the same key shape if the API ever runs more than one worker.
"""
from __future__ import annotations

import time
from collections.abc import Callable

TTL_SECONDS = 30 * 60
MAX_ENTRIES = 500


class ConversationStore:
    def __init__(
        self,
        ttl_seconds: float = TTL_SECONDS,
        max_entries: int = MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._entries: dict[tuple[str, str], tuple[str, float]] = {}

    def get(self, user_id: str, conversation_id: str) -> str | None:
        key = (user_id, conversation_id)
        entry = self._entries.get(key)
        if entry is None:
            return None
        summary, expires_at = entry
        if expires_at <= self._clock():
            del self._entries[key]
            return None
        return summary

    def put(self, user_id: str, conversation_id: str, summary: str) -> None:
        key = (user_id, conversation_id)
        self._entries.pop(key, None)  # re-insert so eviction order is by last use
        self._entries[key] = (summary, self._clock() + self._ttl)
        while len(self._entries) > self._max:
            self._entries.pop(next(iter(self._entries)))

    def delete(self, user_id: str, conversation_id: str) -> bool:
        return self._entries.pop((user_id, conversation_id), None) is not None


conversations = ConversationStore()
