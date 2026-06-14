"""Account overview and snapshot endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_account_service, get_current_user, get_optional_user
from app.schemas.account import AccountOverviewResponse, AccountSnapshotListResponse
from app.services.account_service import AccountService

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/overview", response_model=AccountOverviewResponse)
def get_account_overview(
    service: AccountService = Depends(get_account_service),
    _user: str | None = Depends(get_optional_user),
) -> AccountOverviewResponse:
    """Return the current account overview including balances and margin."""
    overview = service.get_overview()
    if overview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account overview data found.",
        )
    return overview


@router.get("/snapshots", response_model=AccountSnapshotListResponse)
def get_account_snapshots(
    limit: int = Query(default=30, ge=1, le=500),
    service: AccountService = Depends(get_account_service),
    _user: str | None = Depends(get_current_user),
) -> AccountSnapshotListResponse:
    """Return historical account snapshots ordered by date."""
    return service.get_snapshots(limit=limit)
