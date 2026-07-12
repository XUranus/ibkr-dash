"""Simple in-memory TTL cache for query results.

Data from IBKR updates once per day, so queries can be cached aggressively.
Cache is invalidated when new data is imported (via invalidate_all).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Global cache store
_cache: dict[str, tuple[float, Any]] = {}
_default_ttl: float = 86400  # 24 hours


def set_default_ttl(seconds: float) -> None:
    """Set the default TTL for cache entries."""
    global _default_ttl
    _default_ttl = seconds


def get(key: str) -> Any | None:
    """Get a value from cache. Returns None if missing or expired."""
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        del _cache[key]
        return None
    return value


def put(key: str, value: Any, ttl: float | None = None) -> None:
    """Store a value in cache with TTL."""
    expires_at = time.time() + (ttl if ttl is not None else _default_ttl)
    _cache[key] = (expires_at, value)


def invalidate(prefix: str) -> int:
    """Invalidate all cache entries matching a prefix. Returns count removed."""
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for k in keys_to_delete:
        del _cache[k]
    return len(keys_to_delete)


def invalidate_all() -> int:
    """Invalidate all cache entries. Called after data import."""
    count = len(_cache)
    _cache.clear()
    logger.info("Cache invalidated: %d entries cleared", count)
    return count


def make_key(*parts: Any) -> str:
    """Build a deterministic cache key from parts."""
    raw = json.dumps(parts, default=str, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def cached(prefix: str, ttl: float | None = None):
    """Decorator that caches function results.

    Usage:
        @cached("equity_curve", ttl=3600)
        def get_equity_curve(self, start_date, end_date):
            ...
    """
    def decorator(func: Callable) -> Callable:
        """Wrap func with TTL-based caching."""
        def wrapper(*args, **kwargs) -> Any:
            """Execute func or return cached result if available."""
            # Build key from function name + args (skip 'self')
            key_parts = [prefix, func.__name__]
            for a in args[1:]:  # skip self
                key_parts.append(a)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            key = make_key(*key_parts)

            result = get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            if result is not None:
                put(key, result, ttl)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


def stats() -> dict[str, int]:
    """Return cache statistics."""
    now = time.time()
    total = len(_cache)
    expired = sum(1 for _, (exp, _) in _cache.items() if now > exp)
    return {"total": total, "active": total - expired, "expired": expired}


# Data freshness check — invalidate cache when new data arrives
_last_data_fingerprint: str = ""


def check_data_freshness(db) -> None:
    """Check if data has changed since last cache build.

    Queries the latest report_date and count from account_snapshots.
    If changed, invalidates all cache entries.
    Called once per request (cheap single-row query).
    """
    global _last_data_fingerprint
    row = db.execute_one(
        "SELECT report_date, COUNT(*) OVER () AS total FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
    )
    if row:
        fingerprint = f"{row['report_date']}:{row['total']}"
    else:
        fingerprint = ""
    if fingerprint and fingerprint != _last_data_fingerprint:
        if _last_data_fingerprint:  # skip first call
            invalidate_all()
            logger.info("Data freshness check: new data detected, cache cleared")
        _last_data_fingerprint = fingerprint
