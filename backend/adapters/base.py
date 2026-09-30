"""
Base Data Adapter with Caching, Exponential Backoff, Rate-Limiting & Stale Detection.
"""
import time
import random
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("freightwise.adapters")


class BaseAdapter:
    """
    Modular Base Provider Adapter.
    Encapsulates TTL caching, rate-limit protection, and stale-data classification.
    """

    def __init__(self, name: str, default_ttl_seconds: int = 900, max_stale_seconds: int = 86400):
        self.name = name
        self.default_ttl = default_ttl_seconds
        self.max_stale_seconds = max_stale_seconds
        self._cached_data: Optional[Dict[str, Any]] = None
        self._cached_at: float = 0.0
        self._source_timestamp: Optional[str] = None
        self._rate_limited_until: float = 0.0
        self._consecutive_failures: int = 0
        self._last_error: Optional[str] = None

    def is_cached_valid(self) -> bool:
        """True if cached data is fresh within TTL."""
        if not self._cached_data:
            return False
        return (time.time() - self._cached_at) < self.default_ttl

    def is_stale(self) -> bool:
        """True if cached data exists but exceeds TTL."""
        if not self._cached_data:
            return False
        age = time.time() - self._cached_at
        return age >= self.default_ttl

    def get_status(self) -> str:
        """Returns 'live', 'stale', 'rate_limited', or 'error'."""
        if time.time() < self._rate_limited_until:
            return "rate_limited" if self._cached_data else "error"
        if self._cached_data:
            return "live" if self.is_cached_valid() else "stale"
        if self._last_error:
            return "error"
        return "uninitialized"

    def backoff_sleep(self):
        """Calculate exponential backoff with jitter."""
        self._consecutive_failures += 1
        base = min(60.0, 2.0 ** min(self._consecutive_failures, 6))
        jitter = random.uniform(0.5, 1.5)
        delay = base * jitter
        log.warning("[%s] Failure #%d. Backing off for %.2fs", self.name, self._consecutive_failures, delay)
        time.sleep(delay)

    def mark_rate_limited(self, retry_after_seconds: int = 3600):
        """Handle 429 Rate Limit responses without spamming."""
        self._rate_limited_until = time.time() + retry_after_seconds
        self._last_error = f"Rate limited. Next allowed request in {retry_after_seconds}s"
        log.warning("[%s] %s", self.name, self._last_error)

    def set_cache(self, data: Dict[str, Any], source_timestamp: Optional[str] = None):
        """Store fresh data."""
        self._cached_data = data
        self._cached_at = time.time()
        self._source_timestamp = source_timestamp or datetime.now(timezone.utc).isoformat()
        self._consecutive_failures = 0
        self._last_error = None

    def get_cached(self) -> Tuple[Optional[Dict[str, Any]], str, Optional[str]]:
        """Return (data, status, source_timestamp)."""
        return self._cached_data, self.get_status(), self._source_timestamp
