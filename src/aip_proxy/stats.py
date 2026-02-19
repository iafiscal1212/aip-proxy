"""
Stats tracker for AIP Proxy.

Tracks request counts, latency, cache hits, and token savings.
"""

import time
from typing import Dict, List


class StatsTracker:
    """Track proxy request statistics."""

    def __init__(self):
        self._requests: List[dict] = []
        self._started = time.time()

    def record(
        self,
        path: str,
        duration: float,
        cached: bool = False,
        streamed: bool = False,
        status: int = 200,
    ) -> None:
        """Record a proxied request."""
        self._requests.append({
            "path": path,
            "duration": duration,
            "cached": cached,
            "streamed": streamed,
            "status": status,
            "ts": time.time(),
        })

        # Keep last 10000 entries max
        if len(self._requests) > 10000:
            self._requests = self._requests[-5000:]

    def summary(self) -> Dict:
        """Return aggregated statistics."""
        total = len(self._requests)
        if total == 0:
            return {
                "total_requests": 0,
                "uptime_seconds": round(time.time() - self._started),
            }

        chat_reqs = [r for r in self._requests if "chat/completions" in r.get("path", "")]
        cached = sum(1 for r in self._requests if r["cached"])
        streamed = sum(1 for r in self._requests if r["streamed"])
        errors = sum(1 for r in self._requests if r["status"] >= 400)
        durations = [r["duration"] for r in self._requests]

        return {
            "total_requests": total,
            "chat_requests": len(chat_reqs),
            "cached_responses": cached,
            "streamed_responses": streamed,
            "errors": errors,
            "avg_latency_ms": round(sum(durations) / len(durations) * 1000, 1),
            "p95_latency_ms": round(sorted(durations)[int(len(durations) * 0.95)] * 1000, 1),
            "uptime_seconds": round(time.time() - self._started),
        }
