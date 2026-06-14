"""Symbol suggestion response schemas."""

from pydantic import BaseModel


class SymbolSuggestion(BaseModel):
    """A single symbol suggestion."""
    symbol: str
    description: str | None = None
    source: str = "positions"  # "positions" or "trades"


class SymbolSuggestResponse(BaseModel):
    """Response for the symbol suggest endpoint."""
    suggestions: list[SymbolSuggestion]
    query: str
