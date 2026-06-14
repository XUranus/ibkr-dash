"""Tests for InvestmentThesis."""

from app.services.investment_thesis import (
    InvestmentThesis,
    get_thesis,
    all_configured_symbols,
    is_thesis_known,
    evaluate_no_add_triggers,
    evaluate_sell_triggers,
    DEFAULT_THESIS,
    ROLE_UNKNOWN,
    ROLE_CORE_GROWTH,
    RISK_CLASS_EXTREME,
)


class TestGetThesis:
    def test_known_symbol(self):
        thesis = get_thesis("AMD")
        assert thesis.symbol == "AMD"
        assert thesis.role == ROLE_CORE_GROWTH
        assert thesis.max_position_pct > 0
        assert len(thesis.core_thesis) > 0

    def test_unknown_symbol_returns_default(self):
        thesis = get_thesis("UNKNOWN_XYZ")
        assert thesis.role == ROLE_UNKNOWN
        assert thesis.metadata.get("default") is True

    def test_case_insensitive(self):
        thesis = get_thesis("amd")
        assert thesis.symbol == "AMD"

    def test_suffix_stripped(self):
        thesis = get_thesis("MSTR.US")
        assert thesis.symbol == "MSTR"
        assert thesis.risk_class == RISK_CLASS_EXTREME

    def test_returns_copy(self):
        t1 = get_thesis("AMD")
        t1.max_position_pct = 999
        t2 = get_thesis("AMD")
        assert t2.max_position_pct != 999

    def test_all_configured_symbols(self):
        symbols = all_configured_symbols()
        assert "AMD" in symbols
        assert "MSTR" in symbols
        assert isinstance(symbols, list)


class TestIsThesisKnown:
    def test_known(self):
        assert is_thesis_known(get_thesis("AMD")) is True

    def test_unknown(self):
        assert is_thesis_known(DEFAULT_THESIS) is False


class TestEvaluateNoAddTriggers:
    def test_trend_break_triggers(self):
        thesis = get_thesis("AMD")
        triggered = evaluate_no_add_triggers(thesis, trend_break_level="broken")
        assert len(triggered) > 0


class TestEvaluateSellTriggers:
    def test_severe_triggers(self):
        thesis = get_thesis("AMD")
        triggered = evaluate_sell_triggers(thesis, trend_break_level="severe")
        assert len(triggered) > 0

    def test_no_trigger_on_none(self):
        thesis = get_thesis("AMD")
        triggered = evaluate_sell_triggers(thesis, trend_break_level="none")
        assert len(triggered) == 0
