"""Admin settings endpoints.

Provides a unified API for managing all application settings.
All settings are persisted to a JSON file via the settings manager.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.services.settings_service import (
    get_all_settings,
    reset_settings,
    update_settings,
)

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("")
def list_settings(
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Get all settings organized by category."""
    return get_all_settings()


@router.put("")
def update_settings_endpoint(
    payload: dict[str, str],
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Update multiple settings.

    Request body: {"LLM_API_KEY": "sk-...", "FLEX_TOKEN": "..."}
    Changes take effect immediately (persisted to JSON).
    """
    count = update_settings(payload)
    return {"updated": count}


@router.post("/reset")
def reset_settings_endpoint(
    payload: dict[str, list[str] | None] | None = None,
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Reset settings to defaults.

    Request body: {"keys": ["LLM_API_KEY", "FLEX_TOKEN"]} to reset specific keys.
    Empty body or {"keys": null} to reset all.
    """
    keys = payload.get("keys") if payload else None
    count = reset_settings(keys)
    return {"reset": count}
