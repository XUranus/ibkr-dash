"""MCP (Model Context Protocol) data access routes.

These endpoints are authenticated via Bearer API tokens and expose
read-only portfolio data for external integrations (MCP servers,
AI agents, automation tools, etc.).

Scopes:
  - read:positions  → position data
  - read:account    → account overview & snapshots
  - read:trades     → trade history
  - read:cashflows  → cash flow & dividend data
  - read:charts     → equity curve & performance calendar
  - read:reviews    → daily position reviews
  - read            → all read scopes (default)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_db
from app.core.database import Database
from app.services.api_token_service import ApiTokenService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def _get_token_info(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Validate Bearer token and return token info."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Bearer <token>",
        )

    svc = ApiTokenService(db)
    info = svc.validate_token(credentials.credentials)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API token.",
        )
    return info


def _check_scope(token_info: dict, required: str) -> None:
    """Check if the token has the required scope. Raises 403 if not."""
    scopes_str = token_info.get("scopes", "[]")
    try:
        scopes = json.loads(scopes_str) if isinstance(scopes_str, str) else scopes_str
    except (json.JSONDecodeError, TypeError):
        scopes = []

    if "read" in scopes:
        return  # "read" grants all read scopes
    if required in scopes:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Token lacks required scope: {required}",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/positions")
def mcp_positions(
    report_date: str | None = Query(default=None, description="Filter by report date (YYYY-MM-DD)"),
    symbol: str | None = Query(default=None, description="Filter by symbol"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get current positions."""
    _check_scope(token_info, "read:positions")

    conditions = []
    params: list[Any] = []
    if report_date:
        conditions.append("report_date = ?")
        params.append(report_date)
    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    rows = db.execute(
        f"SELECT report_date, symbol, description, asset_class, currency, "
        f"quantity, mark_price, position_value, average_cost_price, cost_basis_money, "
        f"percent_of_nav, fifo_pnl_unrealized, total_unrealized_pnl, total_realized_pnl, "
        f"previous_day_change_percent "
        f"FROM position_snapshots {where} "
        f"ORDER BY report_date DESC, position_value DESC LIMIT ?",
        tuple(params),
    )

    return {"positions": rows, "count": len(rows)}


@router.get("/account/overview")
def mcp_account_overview(
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get the latest account overview."""
    _check_scope(token_info, "read:account")

    row = db.execute_one(
        "SELECT report_date, account_id, currency, total_equity, cash, "
        "stock_value, options_value, funds_value, crypto_value, "
        "cnav_mtm, cnav_twr, cnav_deposits, "
        "cnav_starting_value, cnav_ending_value, "
        "cnav_realized, cnav_change_in_unrealized, "
        "fifo_total_realized_pnl, fifo_total_unrealized_pnl "
        "FROM account_snapshots "
        "WHERE total_equity > 0 "
        "ORDER BY report_date DESC LIMIT 1"
    )
    if not row:
        raise HTTPException(status_code=404, detail="No account data available")
    return {"overview": row}


@router.get("/account/snapshots")
def mcp_account_snapshots(
    limit: int = Query(default=30, ge=1, le=500),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get historical account snapshots."""
    _check_scope(token_info, "read:account")

    conditions = ["total_equity > 0"]
    params: list[Any] = []
    if start_date:
        conditions.append("report_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("report_date <= ?")
        params.append(end_date)

    where = "WHERE " + " AND ".join(conditions)
    params.append(limit)

    rows = db.execute(
        f"SELECT report_date, total_equity, cash, stock_value, options_value, "
        f"cnav_mtm, cnav_twr, fifo_total_realized_pnl, fifo_total_unrealized_pnl "
        f"FROM account_snapshots {where} "
        f"ORDER BY report_date DESC LIMIT ?",
        tuple(params),
    )

    return {"snapshots": rows, "count": len(rows)}


@router.get("/trades")
def mcp_trades(
    symbol: str | None = Query(default=None),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get trade history."""
    _check_scope(token_info, "read:trades")

    conditions = []
    params: list[Any] = []
    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if start_date:
        conditions.append("trade_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("trade_date <= ?")
        params.append(end_date)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    rows = db.execute(
        f"SELECT trade_date, symbol, description, asset_class, buy_sell, "
        f"quantity, trade_price, trade_money, net_cash, fifo_pnl_realized, "
        f"currency, exchange, order_type "
        f"FROM trade_records {where} "
        f"ORDER BY trade_date DESC LIMIT ?",
        tuple(params),
    )

    return {"trades": rows, "count": len(rows)}


@router.get("/cash-flows")
def mcp_cash_flows(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    flow_type: str | None = Query(default=None, description="DIV, INT, DEP, etc."),
    limit: int = Query(default=50, ge=1, le=500),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get cash flow history (dividends, interest, deposits, etc.)."""
    _check_scope(token_info, "read:cashflows")

    conditions = []
    params: list[Any] = []
    if start_date:
        conditions.append("date_time >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date_time <= ?")
        params.append(end_date)
    if flow_type:
        conditions.append("flow_type = ?")
        params.append(flow_type)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    rows = db.execute(
        f"SELECT date_time, symbol, description, currency, amount, amount_in_base, "
        f"flow_type, flow_direction, settle_date "
        f"FROM cash_flows {where} "
        f"ORDER BY date_time DESC LIMIT ?",
        tuple(params),
    )

    return {"cash_flows": rows, "count": len(rows)}


@router.get("/dividends")
def mcp_dividends(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get dividend history (convenience shortcut)."""
    _check_scope(token_info, "read:cashflows")

    conditions = ["flow_type = 'DIV'"]
    params: list[Any] = []
    if start_date:
        conditions.append("date_time >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date_time <= ?")
        params.append(end_date)

    where = "WHERE " + " AND ".join(conditions)
    params.append(limit)

    rows = db.execute(
        f"SELECT date_time, symbol, description, currency, amount, amount_in_base "
        f"FROM cash_flows {where} "
        f"ORDER BY date_time DESC LIMIT ?",
        tuple(params),
    )

    return {"dividends": rows, "count": len(rows)}


@router.get("/charts/equity-curve")
def mcp_equity_curve(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get equity curve data."""
    _check_scope(token_info, "read:charts")

    conditions = ["total_equity > 0"]
    params: list[Any] = []
    if start_date:
        conditions.append("report_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("report_date <= ?")
        params.append(end_date)

    where = "WHERE " + " AND ".join(conditions)

    rows = db.execute(
        f"SELECT report_date, total_equity, cash, stock_value, "
        f"cnav_twr, cnav_mtm "
        f"FROM account_snapshots {where} "
        f"ORDER BY report_date ASC",
        tuple(params),
    )

    return {"equity_curve": rows, "count": len(rows)}


@router.get("/charts/performance-calendar")
def mcp_performance_calendar(
    view: str = Query(default="month", description="month, year, or all"),
    anchor: str | None = Query(default=None, description="YYYY-MM or YYYY"),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get performance calendar data (daily P&L for heatmap)."""
    _check_scope(token_info, "read:charts")

    conditions = ["total_equity > 0"]
    params: list[Any] = []

    if view == "month" and anchor:
        conditions.append("report_date LIKE ?")
        params.append(f"{anchor}%")
    elif view == "year" and anchor:
        conditions.append("report_date LIKE ?")
        params.append(f"{anchor}%")
    # "all" has no date filter

    where = "WHERE " + " AND ".join(conditions)

    rows = db.execute(
        f"SELECT report_date, total_equity, cnav_mtm, cnav_twr "
        f"FROM account_snapshots {where} "
        f"ORDER BY report_date ASC",
        tuple(params),
    )

    return {"calendar": rows, "count": len(rows)}


@router.get("/reviews")
def mcp_reviews(
    report_date: str | None = Query(default=None, description="Get review for a specific date"),
    limit: int = Query(default=10, ge=1, le=100),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get daily position reviews."""
    _check_scope(token_info, "read:reviews")

    if report_date:
        row = db.execute_one(
            "SELECT id, report_date, review_output, metadata, created_at "
            "FROM daily_position_reviews WHERE report_date = ? ORDER BY created_at DESC LIMIT 1",
            (report_date,),
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"No review found for {report_date}")
        # Parse JSON fields
        for field in ("review_output", "metadata"):
            if row.get(field) and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return {"review": row}

    rows = db.execute(
        "SELECT id, report_date, review_output, metadata, created_at "
        "FROM daily_position_reviews ORDER BY report_date DESC LIMIT ?",
        (limit,),
    )
    for row in rows:
        for field in ("review_output", "metadata"):
            if row.get(field) and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    pass

    return {"reviews": rows, "count": len(rows)}


@router.get("/portfolio/review")
def mcp_portfolio_review(
    report_date: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Database = Depends(get_db),
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """Get portfolio review reports (from Portfolio Manager)."""
    _check_scope(token_info, "read:reviews")

    if report_date:
        row = db.execute_one(
            "SELECT id, report_date, report_type, status, data_json "
            "FROM pm_portfolio_reports WHERE report_date = ? ORDER BY created_at DESC LIMIT 1",
            (report_date,),
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"No portfolio review found for {report_date}")
        if row.get("data_json") and isinstance(row["data_json"], str):
            try:
                row["data_json"] = json.loads(row["data_json"])
            except (json.JSONDecodeError, TypeError):
                pass
        return {"review": row}

    rows = db.execute(
        "SELECT id, report_date, report_type, status, data_json "
        "FROM pm_portfolio_reports ORDER BY report_date DESC LIMIT ?",
        (limit,),
    )
    for row in rows:
        if row.get("data_json") and isinstance(row["data_json"], str):
            try:
                row["data_json"] = json.loads(row["data_json"])
            except (json.JSONDecodeError, TypeError):
                pass

    return {"reviews": rows, "count": len(rows)}


# ---------------------------------------------------------------------------
# API discovery
# ---------------------------------------------------------------------------


@router.get("")
def mcp_index(
    token_info: dict = Depends(_get_token_info),
) -> dict:
    """List available MCP endpoints."""
    return {
        "service": "IBKR Dash MCP API",
        "version": "1.0.0",
        "authenticated_as": token_info.get("name", "unknown"),
        "endpoints": {
            "GET /api/mcp/positions": "Current positions",
            "GET /api/mcp/account/overview": "Latest account overview",
            "GET /api/mcp/account/snapshots": "Historical account snapshots",
            "GET /api/mcp/trades": "Trade history",
            "GET /api/mcp/cash-flows": "Cash flow history",
            "GET /api/mcp/dividends": "Dividend history",
            "GET /api/mcp/charts/equity-curve": "Equity curve time-series",
            "GET /api/mcp/charts/performance-calendar": "Performance calendar heatmap",
            "GET /api/mcp/reviews": "Daily position reviews",
            "GET /api/mcp/portfolio/review": "Portfolio review reports",
        },
        "docs": "/api/docs",
    }
