"""Fetch job: pull data from IBKR Flex Web Service and archive by date.

This module handles ONLY the network I/O — no parsing, no database writes.
Downloaded files are saved with date-based naming for archival:
    data/flex_exports/{query_id}_{YYYY-MM-DD}.xml

If the file for today already exists and has meaningful content, the fetch is skipped.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from pathlib import Path

from worker.clients.flex_client import (
    FlexClient,
    FlexClientError,
    FlexRateLimited,
)
from worker.core.config import get_settings

logger = logging.getLogger(__name__)

# Delay between queries to avoid rate limiting (seconds)
_INTER_QUERY_DELAY = 5

# Retry configuration for rate-limited queries
_RATE_LIMIT_MAX_RETRIES = 3
_RATE_LIMIT_INITIAL_DELAY = 60  # seconds
_RATE_LIMIT_BACKOFF_FACTOR = 2  # exponential backoff: 60s, 120s, 240s


def _is_rate_limited(exc: Exception) -> bool:
    """Check if an exception indicates rate limiting."""
    return isinstance(exc, FlexRateLimited) or (
        isinstance(exc, FlexClientError)
        and "too many requests" in str(exc).lower()
    )


def _fetch_single_query(
    flex_client: FlexClient,
    query_id: str,
    save_path: Path,
    max_retries: int = _RATE_LIMIT_MAX_RETRIES,
    initial_delay: float = _RATE_LIMIT_INITIAL_DELAY,
) -> bool:
    """Fetch a single flex query with retry logic for rate limiting.

    Args:
        flex_client: The Flex client instance.
        query_id: The flex query ID to fetch.
        save_path: Path to save the downloaded file.
        max_retries: Maximum retry attempts for rate-limited queries.
        initial_delay: Initial delay in seconds before retrying.

    Returns:
        True if fetch succeeded, False otherwise.
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        t_send = time.monotonic()
        send_time = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            flex_client.download_flex_statement(query_id, save_path)
            elapsed = time.monotonic() - t_send
            file_size = save_path.stat().st_size if save_path.exists() else 0
            logger.info(
                "IBKR query %s: fetched successfully file=%s size=%d bytes "
                "send_time=%s elapsed=%.1fs",
                query_id, save_path.name, file_size, send_time, elapsed,
            )
            return True
        except FlexRateLimited as exc:
            elapsed = time.monotonic() - t_send
            last_error = exc
            delay = initial_delay * (_RATE_LIMIT_BACKOFF_FACTOR ** (attempt - 1))
            logger.warning(
                "IBKR query %s: rate limited (attempt %d/%d) send_time=%s "
                "elapsed=%.1fs retry_in=%.0fs error=%s",
                query_id, attempt, max_retries, send_time, elapsed, delay, exc,
            )
            if attempt < max_retries:
                time.sleep(delay)
        except FlexClientError as exc:
            elapsed = time.monotonic() - t_send
            # Check if this is also a rate limit error
            if _is_rate_limited(exc):
                last_error = exc
                delay = initial_delay * (_RATE_LIMIT_BACKOFF_FACTOR ** (attempt - 1))
                logger.warning(
                    "IBKR query %s: rate limited (attempt %d/%d) send_time=%s "
                    "elapsed=%.1fs retry_in=%.0fs error=%s",
                    query_id, attempt, max_retries, send_time, elapsed, delay, exc,
                )
                if attempt < max_retries:
                    time.sleep(delay)
            else:
                # Non-rate-limit error — don't retry
                logger.error(
                    "IBKR query %s: FAILED send_time=%s elapsed=%.1fs error=%s",
                    query_id, send_time, elapsed, exc,
                )
                return False

    # All retries exhausted
    logger.error(
        "IBKR query %s: FAILED after %d attempts (rate limited). Last error: %s",
        query_id, max_retries, last_error,
    )
    return False


def fetch_flex_statements(
    data_dir: Path | str | None = None,
    query_ids: list[str] | None = None,
) -> list[Path]:
    """Pull Flex statements from IBKR and archive by date.

    For each query_id, saves as {query_id}_{YYYY-MM-DD}.xml.
    If today's file already exists and has meaningful content (>1KB), skips the pull.
    Each query is fetched independently — a failure on one does not block others.
    Rate-limited queries are retried with exponential backoff.

    Args:
        data_dir: Directory to save files. Defaults to settings.data_dir.
        query_ids: Query IDs to pull. Defaults to settings.flex_query_ids (comma-separated).

    Returns:
        List of paths to fetched (or already-existing) files.
    """
    settings = get_settings()
    data_dir = Path(data_dir or settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    if not settings.flex_token:
        logger.warning("FLEX_TOKEN not configured, skipping fetch")
        return []

    if query_ids is None:
        query_ids = [q.strip() for q in settings.flex_query_ids.split(",") if q.strip()]
    today = date.today().isoformat()  # YYYY-MM-DD
    flex_client = FlexClient(settings)

    logger.info("IBKR fetch started: queries=%s date=%s", query_ids, today)

    saved_files: list[Path] = []
    for i, query_id in enumerate(query_ids):
        save_path = data_dir / f"{query_id}_{today}.xml"

        # Skip only if today's file exists AND has meaningful content (>1KB)
        if save_path.exists() and save_path.stat().st_size > 1024:
            file_size = save_path.stat().st_size
            logger.info(
                "IBKR query %s: skipped (local cache hit) file=%s size=%d bytes",
                query_id, save_path.name, file_size,
            )
            saved_files.append(save_path)
            continue

        # Fetch with retry logic
        if _fetch_single_query(flex_client, query_id, save_path):
            saved_files.append(save_path)

        # Add delay between queries to avoid rate limiting
        if i < len(query_ids) - 1:
            time.sleep(_INTER_QUERY_DELAY)

    logger.info("IBKR fetch completed: %d/%d queries succeeded", len(saved_files), len(query_ids))
    return saved_files
