"""Memory utilities for Account Copilot."""

from __future__ import annotations

import re
from typing import Any


# Common stock ticker pattern
_TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b")


def extract_symbols(text: str) -> list[str]:
    """Extract potential stock symbols from text."""
    if not text:
        return []
    matches = _TICKER_PATTERN.findall(text.upper())
    # Filter common English words that look like tickers
    stopwords = {
        "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER",
        "WAS", "ONE", "OUR", "OUT", "HAS", "HIS", "HOW", "ITS", "MAY", "NEW",
        "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "GET", "HAD", "LET", "SAY",
        "SHE", "TOO", "USE", "USD", "ETF", "IPO", "CEO", "CFO", "GDP", "CPI",
        "PCE", "FED", "SEC", "API", "LLM", "AI", "ML", "EV", "PE", "PS",
    }
    return list(dict.fromkeys(m for m in matches if m not in stopwords))


def extract_topics(text: str) -> list[str]:
    """Extract high-level topics from user text."""
    if not text:
        return []

    topic_keywords = {
        "risk": ["risk", "concentration", "drawdown", "loss", "danger", "exposure"],
        "performance": ["performance", "return", "pnl", "profit", "loss", "gain"],
        "trade_decision": ["buy", "sell", "add", "reduce", "hold", "entry", "exit", "position"],
        "review": ["review", "mistake", "behavior", "pattern", "improve"],
        "market": ["market", "trend", "sector", "industry", "macro"],
        "valuation": ["valuation", "pe", "pb", "earnings", "revenue", "growth"],
        "daily_review": ["daily", "today", "yesterday", "attribution", "contributor", "drag"],
    }

    text_lower = text.lower()
    topics = []
    for topic, keywords in topic_keywords.items():
        if any(kw in text_lower for kw in keywords):
            topics.append(topic)
    return topics


class AccountCopilotMemoryManager:
    """Builds and updates memory snapshots for Account Copilot runs."""

    def build_snapshot(self, *, session: dict, messages: list[dict]) -> dict:
        """Return a lightweight memory snapshot from a session and its messages."""
        return {
            "session_id": session.get("id"),
            "rolling_summary": session.get("rolling_summary") or "",
            "compressed_until_message_id": session.get("compressed_until_message_id"),
            "pinned_facts": session.get("pinned_facts") or {},
            "message_count": len(messages),
        }
