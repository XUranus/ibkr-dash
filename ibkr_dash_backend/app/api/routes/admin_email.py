"""Admin email settings endpoints.

Provides routes for viewing and updating email configuration and sending
test emails.  Settings are persisted in a simple key-value table.
"""

from __future__ import annotations

import json
import smtplib
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.schemas.admin_email import EmailSettings, EmailSettingsUpdate, EmailTestResponse

router = APIRouter(prefix="/admin/email", tags=["admin-email"])

# Keys used in the admin_settings table
_EMAIL_KEYS = [
    "email_smtp_host",
    "email_smtp_port",
    "email_smtp_username",
    "email_smtp_password",
    "email_from_address",
    "email_to_addresses",
    "email_enabled",
]


def _read_email_settings(db: Database) -> dict[str, str | None]:
    """Read all email-related settings from the database."""
    values: dict[str, str | None] = {}
    for key in _EMAIL_KEYS:
        row = db.execute_one("SELECT value FROM admin_settings WHERE key = ?", (key,))
        values[key] = row["value"] if row else None
    return values


def _build_email_response(values: dict[str, str | None]) -> EmailSettings:
    """Build an EmailSettings response from raw DB values."""
    to_addresses_raw = values.get("email_to_addresses")
    to_addresses: list[str] = []
    if to_addresses_raw:
        try:
            parsed = json.loads(to_addresses_raw)
            if isinstance(parsed, list):
                to_addresses = [str(a) for a in parsed]
        except (json.JSONDecodeError, TypeError):
            # Fall back to comma-separated
            to_addresses = [a.strip() for a in to_addresses_raw.split(",") if a.strip()]

    smtp_port_raw = values.get("email_smtp_port")
    smtp_port = int(smtp_port_raw) if smtp_port_raw and smtp_port_raw.isdigit() else None

    return EmailSettings(
        smtp_host=values.get("email_smtp_host"),
        smtp_port=smtp_port,
        smtp_username=values.get("email_smtp_username"),
        smtp_password_set=bool(values.get("email_smtp_password")),
        from_address=values.get("email_from_address"),
        to_addresses=to_addresses,
        enabled=values.get("email_enabled") == "true",
    )


@router.get("/settings", response_model=EmailSettings)
def get_email_settings(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> EmailSettings:
    """Get current email configuration."""
    values = _read_email_settings(db)
    return _build_email_response(values)


@router.put("/settings", response_model=EmailSettings)
def update_email_settings(
    payload: EmailSettingsUpdate,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> EmailSettings:
    """Update email configuration."""
    updates: dict[str, str] = {}

    if payload.smtp_host is not None:
        updates["email_smtp_host"] = payload.smtp_host
    if payload.smtp_port is not None:
        updates["email_smtp_port"] = str(payload.smtp_port)
    if payload.smtp_username is not None:
        updates["email_smtp_username"] = payload.smtp_username
    if payload.smtp_password is not None:
        updates["email_smtp_password"] = payload.smtp_password
    if payload.from_address is not None:
        updates["email_from_address"] = payload.from_address
    if payload.to_addresses is not None:
        updates["email_to_addresses"] = json.dumps(payload.to_addresses)
    if payload.enabled is not None:
        updates["email_enabled"] = "true" if payload.enabled else "false"

    for key, value in updates.items():
        db.upsert(
            "admin_settings",
            {"key": key, "value": value},
            conflict_cols=["key"],
        )

    # Return the updated settings
    values = _read_email_settings(db)
    return _build_email_response(values)


@router.post("/test", response_model=EmailTestResponse)
def test_email(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> EmailTestResponse:
    """Send a test email using the current configuration."""
    values = _read_email_settings(db)

    smtp_host = values.get("email_smtp_host")
    smtp_port_raw = values.get("email_smtp_port")
    smtp_username = values.get("email_smtp_username")
    smtp_password = values.get("email_smtp_password")
    from_address = values.get("email_from_address")
    to_addresses_raw = values.get("email_to_addresses")

    if not all([smtp_host, smtp_port_raw, smtp_username, smtp_password, from_address]):
        return EmailTestResponse(
            success=False,
            message="Email is not fully configured. Please set SMTP host, port, username, password, and from address.",
        )

    to_addresses: list[str] = []
    if to_addresses_raw:
        try:
            parsed = json.loads(to_addresses_raw)
            if isinstance(parsed, list):
                to_addresses = [str(a) for a in parsed]
        except (json.JSONDecodeError, TypeError):
            to_addresses = [a.strip() for a in to_addresses_raw.split(",") if a.strip()]

    if not to_addresses:
        return EmailTestResponse(
            success=False,
            message="No recipient addresses configured. Please set at least one to_address.",
        )

    smtp_port = int(smtp_port_raw) if smtp_port_raw and smtp_port_raw.isdigit() else 587

    # Build a test email
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
