"""Symbol analysis schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SymbolFinancialsResponse(BaseModel):
    """Response for symbol financials."""
    symbol: str
    financials: dict[str, Any] = Field(default_factory=dict)


class SymbolComparisonResponse(BaseModel):
    """Response for symbol comparison."""
    left: dict[str, Any] = Field(default_factory=dict)
    right: dict[str, Any] = Field(default_factory=dict)


class SymbolAiAdviceRequest(BaseModel):
    """Request for AI advice on a symbol."""
    symbol: str
    question: str = ""


class SymbolAiAdviceResponse(BaseModel):
    """Response for AI advice on a symbol."""
    symbol: str
    advice: str
    model: str | None = None
