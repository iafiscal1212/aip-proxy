"""
Response cache for AIP Proxy.

Caches identical (or semantically equivalent) requests to avoid
redundant API calls. Uses content hash of messages for cache keys.
"""

import time
import json
import hashlib
from typing import Dict, Optional


class ResponseCache:
    """Simple in-memory LRU cache for API responses."""

    def __init__(self, enabled: bool = True, ttl: int = 300, max_size: int = 200):
        """
        Args:
            enabled: Whether caching is active.
            ttl: Time-to-live in seconds for cache entries.
            max_size: Maximum number of cached responses.
        """
        self.enabled = enabled
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, dict] = {}
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _make_key(self, request_data: dict) -> str:
        """Create a cache key from the request."""
        # Key based on model + messages + key parameters
        key_parts = {
            "model": request_data.get("model", ""),
            "messages": request_data.get("messages", []),
            "temperature": request_data.get("temperature", 1.0),
            "max_tokens": request_data.get("max_tokens"),
        }
        raw = json.dumps(key_parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, request_data: dict) -> Optional[dict]:
        """Look up a cached response."""
        if not self.enabled:
            return None

        key = self._make_key(request_data)
        entry = self._cache.get(key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        # Check TTL
        if time.time() - entry["ts"] > self.ttl:
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        entry["ts"] = time.time()  # Refresh on access
        return entry["data"]

    def put(self, request_data: dict, response_data: dict) -> None:
        """Store a response in cache."""
        if not self.enabled:
            return

        # Don't cache if temperature > 0 (non-deterministic)
        temp = request_data.get("temperature", 1.0)
        if temp is not None and temp > 0:
            return

        key = self._make_key(request_data)

        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = min(self._cache, key=lambda k: self._cache[k]["ts"])
            del self._cache[oldest_key]
            self._stats["evictions"] += 1

        self._cache[key] = {"data": response_data, "ts": time.time()}

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def get_stats(self) -> dict:
        """Return cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        return {
            "entries": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_pct": round(hit_rate, 1),
            "evictions": self._stats["evictions"],
        }
