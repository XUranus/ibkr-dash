"""In-memory sliding-window rate limiter for LLM-calling endpoints.

No external dependencies -- uses a plain dict with timestamp lists.
Designed to be applied as a FastAPI dependency.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Rate limiter that enforces a maximum number of requests per key
    within a rolling time window.

    Each request timestamp is recorded; expired entries are pruned on
    every check so memory usage stays bounded.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _key(self, request: Request) -> str:
        """Derive the rate-limit key from the request (client IP)."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def check(self, request: Request) -> None:
        """Allow the request or raise HTTP 429."""
        key = self._key(request)
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune expired timestamps
        timestamps = self._hits[key]
        self._hits[key] = [t for t in timestamps if t > cutoff]

        if len(self._hits[key]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded: max {self.max_requests} requests "
                    f"per {self.window_seconds}s. Please try again later."
                ),
            )

        self._hits[key].append(now)


# ---------------------------------------------------------------------------
# Pre-configured instance for LLM-calling endpoints
# ---------------------------------------------------------------------------

llm_rate_limiter = SlidingWindowRateLimiter(max_requests=20, window_seconds=60)


def check_llm_rate_limit(request: Request) -> None:
    """FastAPI dependency that enforces the LLM rate limit.

    Usage::

        @router.post("/chat")
        def chat(
            ...,
            _rate: None = Depends(check_llm_rate_limit),
        ):
            ...
    """
    llm_rate_limiter.check(request)
