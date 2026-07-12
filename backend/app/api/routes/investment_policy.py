"""Investment policy endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_investment_policy_service
from app.schemas.investment_policy import (
    GlobalInvestmentPolicy,
    GlobalInvestmentPolicyUpsert,
    InvestmentPolicySeedDefaultsResponse,
    SymbolInvestmentPolicy,
    SymbolInvestmentPolicyListResponse,
    SymbolInvestmentPolicyUpsert,
)
from app.services.investment_policy_service import InvestmentPolicyError, InvestmentPolicyService

router = APIRouter(prefix="/investment-policy", tags=["investment-policy"])


@router.get("/global", response_model=GlobalInvestmentPolicy)
def get_global_policy(
    _user: str | None = Depends(get_current_user),
    svc: InvestmentPolicyService = Depends(get_investment_policy_service),
):
    """Get the global investment policy."""
    return svc.get_global_policy()


@router.put("/global", response_model=GlobalInvestmentPolicy)
def upsert_global_policy(
    body: GlobalInvestmentPolicyUpsert,
    _user: str | None = Depends(get_current_user),
    svc: InvestmentPolicyService = Depends(get_investment_policy_service),
):
    """Create or update the global investment policy."""
    return svc.upsert_global_policy(body)


@router.get("/symbols", response_model=SymbolInvestmentPolicyListResponse)
def list_symbol_policies(
    include_disabled: bool = Query(default=True),
    _user: str | None = Depends(get_current_user),
    svc: InvestmentPolicyService = Depends(get_investment_policy_service),
):
    """List all per-symbol investment policies."""
    return {"items": svc.list_symbol_policies(include_disabled=include_disabled)}


@router.get("/symbols/{symbol}", response_model=SymbolInvestmentPolicy)
def get_symbol_policy(
    symbol: str,
    _user: str | None = Depends(get_current_user),
    svc: InvestmentPolicyService = Depends(get_investment_policy_service),
):
    """Get investment policy for a specific symbol."""
    try:
        policy = svc.get_symbol_policy(symbol)
    except InvestmentPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if policy is None:
        raise HTTPException(status_code=404, detail="Symbol policy not found")
    return policy


@router.put("/symbols/{symbol}", response_model=SymbolInvestmentPolicy)
def upsert_symbol_policy(
    symbol: str,
    body: SymbolInvestmentPolicyUpsert,
    _user: str | None = Depends(get_current_user),
    svc: InvestmentPolicyService = Depends(get_investment_policy_service),
):
    """Create or update investment policy for a specific symbol."""
    try:
        return svc.upsert_symbol_policy(symbol, body)
    except InvestmentPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/symbols/{symbol}/disable", response_model=SymbolInvestmentPolicy)
def disable_symbol_policy(
    symbol: str,
    _user: str | None = Depends(get_current_user),
    svc: InvestmentPolicyService = Depends(get_investment_policy_service),
):
    """Disable investment policy for a specific symbol."""
    try:
        return svc.disable_symbol_policy(symbol)
    except InvestmentPolicyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/seed-defaults", response_model=InvestmentPolicySeedDefaultsResponse)
def seed_default_policies(
    force: bool = Query(default=False),
    _user: str | None = Depends(get_current_user),
    svc: InvestmentPolicyService = Depends(get_investment_policy_service),
):
    """Seed default policies from investment thesis for all configured symbols."""
    created, skipped = svc.seed_defaults(force=force)
    return {
        "created": created,
        "skipped": skipped,
        "message": f"created {len(created)} default symbol policies; skipped {len(skipped)} existing policies",
    }
