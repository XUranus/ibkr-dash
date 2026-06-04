"""Admin email settings schemas."""

from __future__ import annotations

from pydantic import BaseModel


class EmailSettings(BaseModel):
    """Email configuration settings."""
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password_set: bool = False  # Never expose actual password
    from_address: str | None = None
    to_addresses: list[str] = []
    enabled: bool = False


class EmailSettingsUpdate(BaseModel):
    """Request to update email settings."""
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    from_address: str | None = None
    to_addresses: list[str] | None = None
    enabled: bool | None = None


class EmailTestResponse(BaseModel):
    """Response from an email send test."""
    success: bool
    message: str
