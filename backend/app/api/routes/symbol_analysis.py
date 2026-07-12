"""Symbol analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_db, get_app_settings
from app.core.config import Settings
from app.core.database import Database
from app.schemas.symbol_analysis import (
    SymbolComparisonResponse,
    SymbolFinancialsResponse,
)
from app.services.longbridge_service import (
    LongbridgeExternalDataError,
    LongbridgeUnavailableError,
)
from app.services.symbol_analysis_service import SymbolAnalysisService

router = APIRouter(prefix="/symbol-analysis", tags=["symbol-analysis"])


def _get_service(db: Database = Depends(get_db), settings: Settings = Depends(get_app_settings)) -> SymbolAnalysisService:
    from app.services.longbridge_service import LongbridgeService
    lb = LongbridgeService(settings)
    return SymbolAnalysisService(db, lb)


@router.get("/{symbol}/financials", response_model=SymbolFinancialsResponse)
async def get_symbol_financials(
    symbol: str,
    periods: int = Query(default=8, ge=1, le=12),
    report: str = Query(default="qf"),
    _user: str | None = Depends(get_current_user),
    service: SymbolAnalysisService = Depends(_get_service),
) -> SymbolFinancialsResponse:
    """Get financial statements for a symbol."""
    try:
        data = await service.get_financials(symbol=symbol, periods=periods, report=report)
        return SymbolFinancialsResponse(symbol=symbol, financials=data)
    except LongbridgeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except LongbridgeExternalDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/compare", response_model=SymbolComparisonResponse)
async def compare_symbols(
    left: str = Query(...),
    right: str = Query(...),
    periods: int = Query(default=8, ge=1, le=12),
    report: str = Query(default="qf"),
    _user: str | None = Depends(get_current_user),
    service: SymbolAnalysisService = Depends(_get_service),
) -> SymbolComparisonResponse:
    """Compare financials of two symbols."""
    try:
        data = await service.compare(left_symbol=left, right_symbol=right, periods=periods, report=report)
        return SymbolComparisonResponse(**data)
    except LongbridgeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except LongbridgeExternalDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/{symbol}/portfolio-context")
def get_portfolio_context(
    symbol: str,
    _user: str | None = Depends(get_current_user),
    service: SymbolAnalysisService = Depends(_get_service),
) -> dict:
    """Get portfolio context for a symbol (position, trades, prices)."""
    return service.get_portfolio_context(symbol)
