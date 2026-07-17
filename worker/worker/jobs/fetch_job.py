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

from worker.clients.flex_client import FlexClient, FlexClientError
from worker.core.config import get_settings

logger = logging.getLogger(__name__)


def fetch_flex_statements(
    data_dir: Path | str | None = None,
    query_ids: list[str] | None = None,
) -> list[Path]:
    """Pull Flex statements from IBKR and archive by date.

    For each query_id, saves as {query_id}_{YYYY-MM-DD}.xml.
    If today's file already exists and has meaningful content (>1KB), skips the pull.
    Each query is fetched independently — a failure on one does not block others.

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
    for query_id in query_ids:
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
            saved_files.append(save_path)
        except FlexClientError as exc:
            elapsed = time.monotonic() - t_send
            # Log but continue — other queries may still succeed
            logger.warning(
                "IBKR query %s: FAILED send_time=%s elapsed=%.1fs error=%s",
                query_id, send_time, elapsed, exc,
            )

    logger.info("IBKR fetch completed: %d/%d queries succeeded", len(saved_files), len(query_ids))
    return saved_files
