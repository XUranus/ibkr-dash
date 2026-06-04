"""Client to trigger daily position review via the backend API.

After a successful data import, this client sends a POST request to the
backend's agent endpoint to trigger a daily position review task.
"""

from __future__ import annotations

import logging

import requests

from worker.core.config import Settings

logger = logging.getLogger(__name__)


class DailyPositionReviewTrigger:
    """Triggers the backend to create a daily position review task."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def trigger_latest(self) -> dict:
        """Send a POST request to trigger the latest daily position review.

        Returns:
            The JSON response from the backend.

        Raises:
            requests.RequestException: If the request fails.
        """
        base_url = self.settings.backend_base_url.rstrip("/")
        url = f"{base_url}/api/agent/daily-position-review/internal/latest/tasks"
        headers = {}
        if self.settings.daily_review_internal_token:
            headers["x-internal-token"] = self.settings.daily_review_internal_token
        response = requests.post(url, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json()
        logger.info("daily position review task triggered: %s", payload)
        return payload


def trigger_latest_daily_position_review(settings: Settings) -> dict | None:
    """Convenience function to trigger the latest daily position review.

    Catches request exceptions so the caller can continue even if the
    review trigger fails (non-critical path).

    Returns:
        The response dict on success, or None on failure.
    """
    try:
        return DailyPositionReviewTrigger(settings).trigger_latest()
    except requests.RequestException as exc:
        logger.warning("daily position review trigger skipped: %s", exc)
        return None
