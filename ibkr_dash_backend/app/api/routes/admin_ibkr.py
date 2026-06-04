"""Admin IBKR connection settings endpoints.

Provides routes for viewing and updating IBKR settings and testing the
IBKR connection.  In the simplified SQLite backend, IBKR settings are
read from environment configuration.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.schemas.admin_ibkr import IbkrSettings, IbkrSettingsUpdate, IbkrTestResponse

router = APIRouter(prefix="/admin/ibkr", tags=["admin-ibkr"])


@router.get("/settings", response_model=IbkrSettings)
def get_ibkr_settings(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> IbkrSettings:
    """Get current IBKR connection settings.

    Settings are stored in the ``admin_settings`` key-value table.
    Falls back to empty defaults when keys are missing.
    """
    keys = ["ibkr_flex_token", "ibkr_flex_query_id", "ibkr_account_id"]
    values: dict[str, str | None] = {}
    for key in keys:
        row = db.execute_one("SELECT value FROM admin_settings WHERE key = ?", (key,))
        values[key] = row["value"] if row else None

    return IbkrSettings(
        flex_token=values.get("ibkr_flex_token"),
        flex_query_id=values.get("ibkr_flex_query_id"),
        account_id=values.get("ibkr_account_id"),
    )


@router.put("/settings", response_model=IbkrSettings)
def update_ibkr_settings(
    payload: IbkrSettingsUpdate,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> IbkrSettings:
    """Update IBKR connection settings."""
    updates = {
        "ibkr_flex_token": payload.flex_token,
        "ibkr_flex_query_id": payload.flex_query_id,
        "ibkr_account_id": payload.account_id,
    }

    for key, value in updates.items():
        if value is not None:
            db.upsert(
                "admin_settings",
                {"key": key, "value": value},
                conflict_cols=["key"],
            )

    # Return the updated settings
    return get_ibkr_settings(_user=_user, db=db)


@router.post("/test", response_model=IbkrTestResponse)
def test_ibkr_connection(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> IbkrTestResponse:
    """Test the IBKR connection.

    In the simplified backend this checks whether the required settings
    are present and that the database has recent data.
    """
    flex_token_row = db.execute_one("SELECT value FROM admin_settings WHERE key = 'ibkr_flex_token'")
    flex_token = flex_token_row["value"] if flex_token_row else None

    if not flex_token:
        return IbkrTestResponse(
            success=False,
            message="IBKR Flex token is not configured. Please update IBKR settings first.",
        )

    # Check if we have recent data
    latest = db.execute_one(
        "SELECT report_date FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
    )

    if latest:
        return IbkrTestResponse(
            success=True,
            message=f"IBKR connection is active. Latest data from: {latest['report_date']}",
            account_id=None,
        )

    return IbkrTestResponse(
        success=True,
        message="IBKR settings are configured but no data has been imported yet.",
    )
