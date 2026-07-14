"""Admin NotifyHub settings schemas."""

from __future__ import annotations

from pydantic import BaseModel


class NotifyHubSettings(BaseModel):
    """NotifyHub configuration settings (read view)."""
    enabled: bool = False
    url: str | None = None
    api_key_set: bool = False  # Never expose actual key
    topic: str = "ibkr"


class NotifyHubSettingsUpdate(BaseModel):
    """Request to update NotifyHub settings."""
    enabled: bool | None = None
    url: str | None = None
    api_key: str | None = None
    topic: str | None = None


class NotifyHubTestResponse(BaseModel):
    """Response from a NotifyHub test send."""
    success: bool
    message: str
