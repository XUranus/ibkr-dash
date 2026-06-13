"""Client to trigger position analysis via the backend API.

After a successful data import, this client sends a POST request to the
backend's position analysis endpoint to generate a new analysis.
"""

from __future__ import annotations

import logging

import requests

from worker.core.config import Settings

logger = logging.getLogger(__name__)


def trigger_position_analysis(settings: Settings) -> dict | None:
    """Trigger position analysis generation via the backend API.

    This is a non-blocking call that returns immediately.
    The backend will generate the analysis in the background.

    Returns:
        The response dict on success, or None on failure.
    """
    try:
        base_url = settings.backend_base_url.rstrip("/")
        url = f"{base_url}/api/position-analysis/generate"
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
        logger.info("Position analysis triggered: %s", payload.get("id"))
        return payload
    except requests.RequestException as exc:
        logger.warning("Position analysis trigger skipped: %s", exc)
        return None
