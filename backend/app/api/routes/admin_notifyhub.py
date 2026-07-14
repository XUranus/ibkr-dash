"""Admin NotifyHub settings endpoints.

Provides routes for viewing and updating NotifyHub push notification
configuration and sending test notifications.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.admin_notifyhub import (
    NotifyHubSettings,
    NotifyHubSettingsUpdate,
    NotifyHubTestResponse,
)
from app.services.settings_service import get_setting, update_settings

router = APIRouter(prefix="/admin/notifyhub", tags=["admin-notifyhub"])


def _build_response() -> NotifyHubSettings:
    """Build a NotifyHubSettings response from current config."""
    return NotifyHubSettings(
        enabled=str(get_setting("NOTIFYHUB_ENABLED") or "false").lower() in ("true", "1", "yes"),
        url=get_setting("NOTIFYHUB_URL") or None,
        api_key_set=bool(get_setting("NOTIFYHUB_API_KEY")),
        topic=get_setting("NOTIFYHUB_TOPIC") or "ibkr",
    )


@router.get("/settings", response_model=NotifyHubSettings)
def get_notifyhub_settings(
    _user: str | None = Depends(get_current_user),
) -> NotifyHubSettings:
    """Get current NotifyHub configuration."""
    return _build_response()


@router.put("/settings", response_model=NotifyHubSettings)
def update_notifyhub_settings(
    payload: NotifyHubSettingsUpdate,
    _user: str | None = Depends(get_current_user),
) -> NotifyHubSettings:
    """Update NotifyHub configuration."""
    updates: dict[str, str] = {}
    if payload.enabled is not None:
        updates["NOTIFYHUB_ENABLED"] = str(payload.enabled).lower()
    if payload.url is not None:
        updates["NOTIFYHUB_URL"] = payload.url
    if payload.api_key is not None:
        updates["NOTIFYHUB_API_KEY"] = payload.api_key
    if payload.topic is not None:
        updates["NOTIFYHUB_TOPIC"] = payload.topic

    if updates:
        update_settings(updates)

    return _build_response()


@router.post("/test", response_model=NotifyHubTestResponse)
def test_notifyhub(
    _user: str | None = Depends(get_current_user),
) -> NotifyHubTestResponse:
    """Send a test notification via NotifyHub."""
    from app.services.notifyhub_service import is_configured, send_notification

    if not is_configured():
        return NotifyHubTestResponse(
            success=False,
            message="NotifyHub is not fully configured. Please set URL, API key, and enable the service.",
        )

    result = send_notification(
        subject="IBKR Dash - Push Test",
        body="This is a test notification from IBKR Dash. Your NotifyHub configuration is working correctly.",
    )

    return NotifyHubTestResponse(
        success=result.success,
        message=result.message,
    )
