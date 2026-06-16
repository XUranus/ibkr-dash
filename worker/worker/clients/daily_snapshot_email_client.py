"""Client to trigger daily account snapshot email via the backend API.

After a successful data import, this client sends a POST request to the
backend's email endpoint to trigger sending the latest account snapshot email.
"""

from __future__ import annotations

import logging

import requests

from worker.core.config import Settings

logger = logging.getLogger(__name__)


class DailySnapshotEmailTrigger:
    """Triggers the backend to send the latest daily snapshot email."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def trigger_latest(self) -> dict:
        """Send a POST request to trigger the latest daily snapshot email.

        Returns:
            The JSON response from the backend.

        Raises:
            requests.RequestException: If the request fails.
        """
        base_url = self.settings.backend_base_url.rstrip("/")
        url = f"{base_url}/api/account-snapshot-email/internal/latest"
        response = requests.post(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        logger.info("daily account snapshot email triggered: %s", payload)
        return payload


def trigger_latest_daily_account_snapshot_email(settings: Settings) -> dict | None:
    """Convenience function to trigger the latest daily snapshot email.

    Catches request exceptions so the caller can continue even if the
    email trigger fails (non-critical path).

    Returns:
        The response dict on success, or None on failure.
    """
    try:
        return DailySnapshotEmailTrigger(settings).trigger_latest()
    except requests.RequestException as exc:
        logger.warning("daily account snapshot email trigger skipped: %s", exc)
        return None
