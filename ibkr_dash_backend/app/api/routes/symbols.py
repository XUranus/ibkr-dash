"""Symbol suggestion endpoint.

Queries the positions and trades tables for symbols matching the user's
partial input, returning autocomplete-style suggestions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.schemas.symbols import SymbolSuggestion, SymbolSuggestResponse

router = APIRouter(prefix="/symbols", tags=["symbols"])


@router.get("/suggest", response_model=SymbolSuggestResponse)
def suggest_symbols(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> SymbolSuggestResponse:
    """Return symbol suggestions from positions and trades tables.

    Searches both ``position_snapshots`` and ``trade_records`` for symbols
    that start with or contain the query string.  Deduplicates and limits
    results.
    """
    pattern = f"%{q}%"
    seen: set[str] = set()
    suggestions: list[SymbolSuggestion] = []

    # Search positions (most recent data first)
    position_rows = db.execute(
        "SELECT DISTINCT symbol, description FROM position_snapshots "
        "WHERE symbol LIKE ? ORDER BY report_date DESC LIMIT ?",
        (pattern, limit * 2),
    )
    for row in position_rows:
        sym = row["symbol"]
        if sym not in seen:
            seen.add(sym)
            suggestions.append(SymbolSuggestion(
                symbol=sym,
                description=row.get("description"),
                source="positions",
            ))
            if len(suggestions) >= limit:
                break

    # Search trades if we need more results
    if len(suggestions) < limit:
        remaining = limit - len(suggestions)
        trade_rows = db.execute(
            "SELECT DISTINCT symbol, description FROM trade_records "
            "WHERE symbol LIKE ? ORDER BY trade_date DESC LIMIT ?",
            (pattern, remaining * 2),
        )
        for row in trade_rows:
            sym = row["symbol"]
            if sym not in seen:
                seen.add(sym)
                suggestions.append(SymbolSuggestion(
                    symbol=sym,
                    description=row.get("description"),
                    source="trades",
                ))
                if len(suggestions) >= limit:
                    break

    return SymbolSuggestResponse(suggestions=suggestions, query=q)
