"""NotifyHub push notification service.

Wraps the NotifyHub REST API for sending push notifications.
Configuration is read from the JSON settings manager.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.settings_manager import get_manager

logger = logging.getLogger(__name__)


@dataclass
class NotifyHubResult:
    """Result of a NotifyHub send attempt."""
    success: bool
    message: str = ""
    response_data: dict[str, Any] | None = None


def _get_config() -> dict[str, Any]:
    """Read NotifyHub config from settings manager."""
    return {
        "enabled": bool(get_manager().get("notifyhub.enabled", False)),
        "url": str(get_manager().get("notifyhub.url", "")),
        "api_key": str(get_manager().get("notifyhub.api_key", "")),
        "topic": str(get_manager().get("notifyhub.topic", "ibkr")),
    }


def is_configured() -> bool:
    """Check if NotifyHub is configured and enabled."""
    cfg = _get_config()
    return cfg["enabled"] and bool(cfg["url"]) and bool(cfg["api_key"])


def send_notification(
    subject: str,
    body: str,
    *,
    topic: str | None = None,
    fmt: str = "markdown",
    channel: str = "push",
    to: str = "*",
) -> NotifyHubResult:
    """Send a push notification via NotifyHub.

    Args:
        subject: Notification title.
        body: Notification body content.
        topic: Override topic (defaults to configured topic).
        fmt: Content format - "markdown" or "text".
        channel: Delivery channel (default "push").
        to: Recipient target (default "*" for broadcast).

    Returns:
        NotifyHubResult with success status and details.
    """
    cfg = _get_config()

    if not cfg["enabled"]:
        return NotifyHubResult(success=False, message="NotifyHub is not enabled")

    if not cfg["url"]:
        return NotifyHubResult(success=False, message="NotifyHub URL is not configured")

    if not cfg["api_key"]:
        return NotifyHubResult(success=False, message="NotifyHub API key is not configured")

    url = cfg["url"].rstrip("/")
    if not url.endswith("/api/v1/send"):
        url = f"{url}/api/v1/send"

    effective_topic = topic or cfg["topic"]

    payload = {
        "channel": channel,
        "to": to,
        "subject": subject,
        "body": body,
        "topic": effective_topic,
        "format": fmt,
    }

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    try:
        logger.info("NotifyHub sending: topic=%s subject=%s", effective_topic, subject)
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

        try:
            data = resp.json()
        except Exception:
            data = {"status_code": resp.status_code}

        logger.info("NotifyHub sent successfully: status=%d", resp.status_code)
        return NotifyHubResult(
            success=True,
            message=f"Notification sent (HTTP {resp.status_code})",
            response_data=data,
        )

    except httpx.TimeoutException:
        logger.error("NotifyHub request timed out")
        return NotifyHubResult(success=False, message="Request timed out")

    except httpx.HTTPStatusError as exc:
        logger.error("NotifyHub HTTP error: %d %s", exc.response.status_code, exc.response.text[:200])
        return NotifyHubResult(
            success=False,
            message=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
        )

    except Exception as exc:
        logger.error("NotifyHub unexpected error: %s", exc)
        return NotifyHubResult(success=False, message=str(exc)[:200])
