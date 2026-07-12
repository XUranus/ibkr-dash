"""Tests for investment policy service and routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.database import Database
from app.services.investment_policy_service import InvestmentPolicyService, InvestmentPolicyError
from app.schemas.investment_policy import (
    GlobalInvestmentPolicyUpsert,
    SymbolInvestmentPolicyUpsert,
    normalize_policy_symbol,
)


@pytest.fixture()
def db():
    """Create an in-memory database with schema."""
    d = Database(":memory:")
    d.init_schema()
    return d


@pytest.fixture()
def svc(db):
    """Create an InvestmentPolicyService."""
    return InvestmentPolicyService(db)


# --- Schema tests ---

def test_normalize_policy_symbol():
    assert normalize_policy_symbol("aapl") == "AAPL"
    assert normalize_policy_symbol("AAPL.NASDAQ") == "AAPL"
    assert normalize_policy_symbol("  tsla  ") == "TSLA"
    assert normalize_policy_symbol("") == ""


def test_global_policy_defaults():
    policy = GlobalInvestmentPolicyUpsert()
    assert policy.risk_profile == "balanced"
    assert policy.allow_leverage is False
    assert policy.enabled is True


def test_symbol_policy_validation():
    policy = SymbolInvestmentPolicyUpsert(symbol="AAPL")
    assert policy.symbol == "AAPL"
    assert policy.asset_role == "unknown"
    assert policy.conviction == "medium"
    assert policy.user_preferred_max_position_pct == 0.05


def test_symbol_policy_position_order():
    """min <= target <= max must hold."""
    with pytest.raises(ValueError, match="min <= target <= max"):
        SymbolInvestmentPolicyUpsert(
            symbol="AAPL",
            user_preferred_min_position_pct=0.1,
            user_preferred_max_position_pct=0.05,
        )


# --- Service tests ---

def test_get_global_policy_default(svc):
    """When no global policy saved, returns default template."""
    policy = svc.get_global_policy()
    assert policy.id == "global"
    assert policy.risk_profile == "balanced"
    assert policy.target_annual_return_pct == 0.20


def test_upsert_global_policy(svc):
    payload = GlobalInvestmentPolicyUpsert(
        risk_profile="aggressive_growth",
        allow_leverage=True,
        notes="Custom policy",
    )
    result = svc.upsert_global_policy(payload)
    assert result.risk_profile == "aggressive_growth"
    assert result.allow_leverage is True

    # Verify persistence
    fetched = svc.get_global_policy()
    assert fetched.risk_profile == "aggressive_growth"
    assert fetched.notes == "Custom policy"


def test_list_symbol_policies_empty(svc):
    result = svc.list_symbol_policies()
    assert result == []


def test_upsert_symbol_policy(svc):
    payload = SymbolInvestmentPolicyUpsert(
        symbol="AAPL",
        asset_role="core_growth",
        conviction="high",
        user_preferred_target_position_pct=0.08,
        user_preferred_max_position_pct=0.10,
        notes="Apple core holding",
    )
    result = svc.upsert_symbol_policy("AAPL", payload)
    assert result.symbol == "AAPL"
    assert result.asset_role == "core_growth"
    assert result.id == "symbol:AAPL"


def test_get_symbol_policy(svc):
    payload = SymbolInvestmentPolicyUpsert(symbol="TSLA", asset_role="speculative")
    svc.upsert_symbol_policy("TSLA", payload)

    result = svc.get_symbol_policy("TSLA")
    assert result is not None
    assert result.symbol == "TSLA"
    assert result.asset_role == "speculative"


def test_get_symbol_policy_case_insensitive(svc):
    payload = SymbolInvestmentPolicyUpsert(symbol="MSFT")
    svc.upsert_symbol_policy("msft", payload)

    result = svc.get_symbol_policy("MSFT")
    assert result is not None
    assert result.symbol == "MSFT"


def test_disable_symbol_policy(svc):
    payload = SymbolInvestmentPolicyUpsert(symbol="GOOG", enabled=True)
    svc.upsert_symbol_policy("GOOG", payload)

    result = svc.disable_symbol_policy("GOOG")
    assert result.enabled is False

    # Should not appear in non-disabled list
    policies = svc.list_symbol_policies(include_disabled=False)
    assert all(p.symbol != "GOOG" for p in policies)


def test_disable_nonexistent_symbol(svc):
    with pytest.raises(InvestmentPolicyError, match="not found"):
        svc.disable_symbol_policy("NONEXIST")


def test_get_policy_for_symbol_backward_compat(svc):
    """get_policy_for_symbol returns backward-compatible dict."""
    payload = SymbolInvestmentPolicyUpsert(
        symbol="AAPL",
        asset_role="core_growth",
        conviction="high",
    )
    svc.upsert_symbol_policy("AAPL", payload)

    result = svc.get_policy_for_symbol("AAPL")
    assert result["source"] == "user_config"
    assert result["role"] == "core_growth"
    assert result["risk_class"] == "high"
    assert "user_investment_preference" in result


def test_seed_defaults(svc):
    """seed_defaults creates policies from investment thesis."""
    created, skipped = svc.seed_defaults()
    # Should create at least some policies
    assert len(created) > 0 or len(skipped) > 0


def test_list_symbol_policies_after_create(svc):
    svc.upsert_symbol_policy("AAPL", SymbolInvestmentPolicyUpsert(symbol="AAPL"))
    svc.upsert_symbol_policy("TSLA", SymbolInvestmentPolicyUpsert(symbol="TSLA"))

    result = svc.list_symbol_policies()
    symbols = [p.symbol for p in result]
    assert "AAPL" in symbols
    assert "TSLA" in symbols
