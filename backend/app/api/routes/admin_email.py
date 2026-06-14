"""Admin email settings endpoints.

Provides routes for viewing and updating email configuration and sending
test emails.  Settings are persisted via the JSON settings manager.
"""

from __future__ import annotations

import json
import smtplib
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.admin_email import EmailSettings, EmailSettingsUpdate, EmailTestResponse
from app.services.settings_service import get_email_settings, update_email_settings

router = APIRouter(prefix="/admin/email", tags=["admin-email"])


def _build_email_response(raw: dict) -> EmailSettings:
    """Build an EmailSettings response from raw config values."""
    to_addresses_raw = raw.get("to_addresses")
    to_addresses: list[str] = []
    if isinstance(to_addresses_raw, list):
        to_addresses = [str(a) for a in to_addresses_raw]
    elif isinstance(to_addresses_raw, str) and to_addresses_raw:
        try:
            parsed = json.loads(to_addresses_raw)
            if isinstance(parsed, list):
                to_addresses = [str(a) for a in parsed]
        except (json.JSONDecodeError, TypeError):
            to_addresses = [a.strip() for a in to_addresses_raw.split(",") if a.strip()]

    smtp_port = raw.get("smtp_port")
    if isinstance(smtp_port, str) and smtp_port.isdigit():
        smtp_port = int(smtp_port)
    elif not isinstance(smtp_port, int):
        smtp_port = None

    return EmailSettings(
        smtp_host=raw.get("smtp_host") or None,
        smtp_port=smtp_port,
        smtp_username=raw.get("smtp_username") or None,
        smtp_password_set=bool(raw.get("smtp_password")),
        from_address=raw.get("from_address") or None,
        to_addresses=to_addresses,
        enabled=bool(raw.get("enabled")),
    )


@router.get("/settings", response_model=EmailSettings)
def get_email_settings_endpoint(
    _user: str | None = Depends(get_current_user),
) -> EmailSettings:
    """Get current email configuration."""
    return _build_email_response(get_email_settings())


@router.put("/settings", response_model=EmailSettings)
def update_email_settings_endpoint(
    payload: EmailSettingsUpdate,
    _user: str | None = Depends(get_current_user),
) -> EmailSettings:
    """Update email configuration."""
    updates: dict[str, object] = {}
    if payload.smtp_host is not None:
        updates["smtp_host"] = payload.smtp_host
    if payload.smtp_port is not None:
        updates["smtp_port"] = payload.smtp_port
    if payload.smtp_username is not None:
        updates["smtp_username"] = payload.smtp_username
    if payload.smtp_password is not None:
        updates["smtp_password"] = payload.smtp_password
    if payload.from_address is not None:
        updates["from_address"] = payload.from_address
    if payload.to_addresses is not None:
        updates["to_addresses"] = payload.to_addresses
    if payload.enabled is not None:
        updates["enabled"] = payload.enabled

    if updates:
        update_email_settings(updates)

    return _build_email_response(get_email_settings())


@router.post("/test", response_model=EmailTestResponse)
def test_email(
    _user: str | None = Depends(get_current_user),
) -> EmailTestResponse:
    """Send a test email using the current configuration."""
    raw = get_email_settings()

    smtp_host = raw.get("smtp_host")
    smtp_port = raw.get("smtp_port", 587)
    smtp_username = raw.get("smtp_username")
    smtp_password = raw.get("smtp_password")
    from_address = raw.get("from_address")

    if not all([smtp_host, smtp_username, smtp_password, from_address]):
        return EmailTestResponse(
            success=False,
            message="Email is not fully configured. Please set SMTP host, username, password, and from address.",
        )

    to_addresses_raw = raw.get("to_addresses")
    to_addresses: list[str] = []
    if isinstance(to_addresses_raw, list):
        to_addresses = [str(a) for a in to_addresses_raw]
    elif isinstance(to_addresses_raw, str) and to_addresses_raw:
        to_addresses = [a.strip() for a in to_addresses_raw.split(",") if a.strip()]

    if not to_addresses:
        return EmailTestResponse(
            success=False,
            message="No recipient addresses configured. Please set at least one to_address.",
        )

    if isinstance(smtp_port, str) and smtp_port.isdigit():
        smtp_port = int(smtp_port)
    elif not isinstance(smtp_port, int):
        smtp_port = 587

    msg = MIMEText("This is a test email from IBKR Dash. Your email configuration is working correctly.", "plain", "utf-8")
    msg["Subject"] = "IBKR Dash - Email Test"
    msg["From"] = from_address
    msg["To"] = ", ".join(to_addresses)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_address, to_addresses, msg.as_string())
        return EmailTestResponse(
            success=True,
            message=f"Test email sent successfully to {', '.join(to_addresses)}",
        )
    except smtplib.SMTPAuthenticationError:
        return EmailTestResponse(
            success=False,
            message="SMTP authentication failed. Please check your username and password.",
        )
    except smtplib.SMTPException as exc:
        return EmailTestResponse(
            success=False,
            message=f"Failed to send email: {str(exc)[:200]}",
        )
    except Exception as exc:
        return EmailTestResponse(
            success=False,
            message=f"Unexpected error: {str(exc)[:200]}",
        )
