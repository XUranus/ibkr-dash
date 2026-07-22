"""Shared symbol classification constants.

Single source of truth for cash-equivalent instruments, theme buckets,
and benchmark ETFs. All modules should import from here instead of
defining their own copies.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Cash-equivalent instruments (short-term Treasury ETFs / money market)
# Used to exclude from equity analysis, concentration risk, and PnL rankings.
# ---------------------------------------------------------------------------
CASH_EQUIVALENT_SYMBOLS: set[str] = {
    "SGOV", "STRC", "BIL", "SHV", "USFR", "TFLO", "BOXX",
    "ICSH", "SHY", "MINT", "NEAR", "JPST", "GSY",
}

# ---------------------------------------------------------------------------
# Theme classification — used by risk assessment and daily review agents.
# ---------------------------------------------------------------------------

THEME_SEMICONDUCTOR: set[str] = {
    "AMD", "NVDA", "INTC", "TSM", "ASML", "AVGO", "MU", "SMCI", "QCOM", "MRVL",
    "AMAT", "LRCX", "KLAC", "ON", "TXN", "MCHP", "WOLF", "ARM",
}

THEME_AI: set[str] = {
    "NVDA", "MSFT", "GOOGL", "AMZN", "META", "ORCL", "CRM", "PLTR", "SNOW",
    "AI", "SYM", "PATH", "MDB", "NET", "DDOG", "PANW", "CRWD", "ZS",
}

THEME_CHINA: set[str] = {
    "BABA", "JD", "PDD", "BIDU", "XIACY", "TCEHY", "NIO", "LI", "XPEV",
    "BILI", "IQ", "MNSO", "FUTU", "TIGR", "EDU", "TAL", "YMM", "ZTO",
    "KC", "DADA", "QFIN", "LX", "FINV",
}

MEGA_CAP_TECH: set[str] = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
}

# ---------------------------------------------------------------------------
# Benchmark / index ETFs
# ---------------------------------------------------------------------------

BENCHMARK_ETFS: set[str] = {"SPY", "QQQ", "SMH"}
RS_BENCHMARKS: set[str] = {"QQQ", "SMH"}  # Relative strength comparison targets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_cash_equivalent(symbol: str) -> bool:
    """Check if a symbol is a cash-equivalent instrument."""
    base = str(symbol or "").upper().split(".", 1)[0]
    return base in CASH_EQUIVALENT_SYMBOLS


def classify_symbol_theme(symbol: str) -> dict[str, bool]:
    """Classify a symbol into themes using the shared constant sets."""
    base = str(symbol or "").upper().split(".", 1)[0]
    return {
        "semiconductor": base in THEME_SEMICONDUCTOR,
        "ai": base in THEME_AI,
        "china": base in THEME_CHINA,
        "mega_cap_tech": base in MEGA_CAP_TECH,
        "cash_equivalent": base in CASH_EQUIVALENT_SYMBOLS,
    }
