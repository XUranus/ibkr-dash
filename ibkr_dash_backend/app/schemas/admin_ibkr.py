"""Admin IBKR settings schemas."""

from __future__ import annotations

from pydantic import BaseModel


class IbkrSettings(BaseModel):
    """IBKR connection settings."""
    flex_token: str | None = None
    flex_query_id: str | None = None
    account_id: str | None = None


class IbkrSettingsUpdate(BaseModel):
    """Request to update IBKR settings."""
    flex_token: str | None = None
    flex_query_id: str | None = None
    account_id: str | None = None


class IbkrTestResponse(BaseModel):
    """Response from an IBKR connection test."""
    success: bool
    message: str
    account_id: str | None = None
