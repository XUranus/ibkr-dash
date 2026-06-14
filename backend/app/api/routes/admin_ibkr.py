"""Admin IBKR connection settings endpoints.

Settings are persisted via the JSON settings manager.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.schemas.admin_ibkr import IbkrSettings, IbkrSettingsUpdate, IbkrTestResponse
from app.services.settings_service import get_setting, update_settings

router = APIRouter(prefix="/admin/ibkr", tags=["admin-ibkr"])


@router.get("/settings", response_model=IbkrSettings)
def get_ibkr_settings(
    _user: str | None = Depends(get_current_user),
) -> IbkrSettings:
    """Get current IBKR connection settings."""
    return IbkrSettings(
        flex_token=get_setting("FLEX_TOKEN"),
        flex_query_id=get_setting("FLEX_QUERY_IDS"),
        account_id=None,
    )


@router.put("/settings", response_model=IbkrSettings)
def update_ibkr_settings(
    payload: IbkrSettingsUpdate,
    _user: str | None = Depends(get_current_user),
) -> IbkrSettings:
    """Update IBKR connection settings."""
    updates: dict[str, str] = {}
    if payload.flex_token is not None:
        updates["FLEX_TOKEN"] = payload.flex_token
    if payload.flex_query_id is not None:
        updates["FLEX_QUERY_IDS"] = payload.flex_query_id
    if updates:
        update_settings(updates)
    return get_ibkr_settings(_user=_user)


@router.post("/test", response_model=IbkrTestResponse)
def test_ibkr_connection(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> IbkrTestResponse:
    """Test the IBKR connection."""
    flex_token = get_setting("FLEX_TOKEN")

    if not flex_token:
        return IbkrTestResponse(
            success=False,
            message="IBKR Flex token is not configured. Please update IBKR settings first.",
        )

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
