"""Simple in-memory cache with TTL (time-to-live) support.

Used for caching frequently accessed data like model lists and provider
metadata to reduce database queries and improve response times.
"""
from __future__ import annotations

import time
import threading
from typing import Any


class TTLCache:
    """Thread-safe in-memory cache with per-entry TTL."""

    def __init__(self, default_ttl: int = 60):
        self.default_ttl = default_ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expiry, value = entry
            if time.time() > expiry:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        with self._lock:
            self._store[key] = (expiry, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Global cache instance with 60-second default TTL
cache = TTLCache(default_ttl=60)
