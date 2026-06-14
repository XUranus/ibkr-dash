"""Tests for TechnicalSignalEngine."""

from app.services.technical_signal_engine import (
    TechnicalSignalEngine,
    TechnicalSignals,
    parse_candles,
    TREND_BREAK_LEVELS,
)


def _make_candles(n: int, base_price: float = 100.0, step: float = 0.5) -> list[dict]:
    """Generate synthetic OHLCV candles."""
    candles = []
    for i in range(n):
        p = base_price + i * step
        candles.append({
            "open": p - 0.1,
            "high": p + 0.5,
            "low": p - 0.5,
            "close": p,
            "volume": 1000 + i * 10,
        })
    return candles


class TestParseCandles:
    def test_empty(self):
        assert parse_candles(None) == []
        assert parse_candles([]) == []
        assert parse_candles("bad") == []

    def test_list_of_dicts(self):
        raw = [{"close": 100, "open": 99, "high": 101, "low": 98, "volume": 500}]
        result = parse_candles(raw)
        assert len(result) == 1
        assert result[0]["close"] == 100.0

    def test_dict_with_items_key(self):
        raw = {"items": [{"c": 50, "o": 49, "h": 51, "l": 48, "v": 100}]}
        result = parse_candles(raw)
        assert len(result) == 1
        assert result[0]["close"] == 50.0

    def test_skips_items_without_close(self):
        raw = [{"open": 10}, {"close": 20}]
        result = parse_candles(raw)
        assert len(result) == 1
        assert result[0]["close"] == 20.0

    def test_aliases(self):
        raw = [{"c": 42, "o": 40, "h": 43, "l": 39, "v": 100}]
        result = parse_candles(raw)
        assert result[0]["close"] == 42.0
        assert result[0]["open"] == 40.0


class TestTechnicalSignalEngine:
    def setup_method(self):
        self.engine = TechnicalSignalEngine()

    def test_empty_candles(self):
        signals = self.engine.compute()
        assert signals.trend_break_level == "unknown"
        assert "缺少标的 K 线数据" in signals.data_limitations[0]

    def test_basic_compute(self):
        candles = _make_candles(250, base_price=100.0, step=0.1)
        signals = self.engine.compute(symbol_candles=candles)
        assert signals.ma20 is not None
        assert signals.ma50 is not None
        assert signals.ma200 is not None
        assert signals.atr14 is not None
        assert signals.volume_ratio is not None
        assert signals.trend_break_level in TREND_BREAK_LEVELS

    def test_short_candles_limitations(self):
        candles = _make_candles(10)
        signals = self.engine.compute(symbol_candles=candles)
        assert signals.ma20 is None
        assert "MA20 数据不足" in signals.data_limitations

    def test_relative_strength(self):
        candles = _make_candles(250, base_price=100.0, step=0.2)
        bench = _make_candles(250, base_price=100.0, step=0.1)
        signals = self.engine.compute(
            symbol_candles=candles,
            benchmark_candles={"SPY": bench},
        )
        assert "SPY" in signals.relative_strength_20d

    def test_support_resistance(self):
        candles = _make_candles(25)
        signals = self.engine.compute(symbol_candles=candles)
        assert len(signals.support_levels) > 0
        assert len(signals.resistance_levels) > 0

    def test_trend_break_none(self):
        # Uptrend: price well above all MAs
        candles = _make_candles(250, base_price=100.0, step=0.5)
        signals = self.engine.compute(symbol_candles=candles)
        assert signals.trend_break_level == "none"

    def test_to_dict(self):
        candles = _make_candles(250)
        signals = self.engine.compute(symbol_candles=candles)
        d = signals.to_dict()
        assert isinstance(d, dict)
        assert "ma20" in d
        assert "trend_break_level" in d
