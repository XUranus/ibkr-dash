"""Admin settings endpoints.

Provides a unified API for managing all application settings.
Settings are stored in the admin_settings key-value table.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.services.settings_service import (
    SETTINGS_SCHEMA,
    get_all_settings,
    get_setting_with_default,
    reset_settings,
    update_settings,
)

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("")
def list_settings(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Get all settings organized by category."""
    return get_all_settings(db)


@router.put("")
def update_settings_endpoint(
    payload: dict[str, str],
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Update multiple settings.

    Request body: {"LLM_API_KEY": "sk-...", "FLEX_TOKEN": "..."}
    """
    count = update_settings(db, payload)
    return {"updated": count}


@router.post("/reset")
def reset_settings_endpoint(
    payload: dict[str, list[str] | None] | None = None,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Reset settings to defaults.

    Request body: {"keys": ["LLM_API_KEY", "FLEX_TOKEN"]} to reset specific keys.
    Empty body or {"keys": null} to reset all.
    """
    keys = payload.get("keys") if payload else None
    count = reset_settings(db, keys)
    return {"reset": count}


@router.get("/categories")
def list_categories(
    _user: str | None = Depends(get_current_user),
) -> dict:
    """List all setting categories with their keys."""
    categories: dict[str, list[str]] = {}
    for key, meta in SETTINGS_SCHEMA.items():
        cat = meta["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(key)
    return {"categories": categories}
