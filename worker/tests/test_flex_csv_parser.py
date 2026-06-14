"""Tests for the IBKR Flex CSV parser."""

from pathlib import Path

from worker.parsers.flex_csv_parser import parse_flex_csv

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "worker" / "fixtures"


def test_parse_flex_csv_extracts_sections_and_metadata() -> None:
    """Test that parsing a sample CSV extracts correct sections and metadata."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    assert statement.metadata.query_name == "Daily Snapshot"
    assert statement.metadata.from_date == "2026-04-17"
    assert statement.metadata.to_date == "2026-04-18"
    assert statement.metadata.account_ids == ["U1234567"]
    assert "POST" in statement.sections
    assert statement.get_section("TRNT") is not None
    assert len(statement.get_section("POST").rows) == 2
    assert statement.record_counts["DATA"] >= 1


def test_parse_flex_csv_extracts_account_section() -> None:
    """Test that the ACCT section is parsed with account metadata."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    acct = statement.get_section("ACCT")
    assert acct is not None
    assert len(acct.rows) == 1
    assert acct.rows[0]["AccountId"] == "U1234567"
    assert acct.rows[0]["BaseCurrency"] == "USD"


def test_parse_flex_csv_extracts_equity_section() -> None:
    """Test that the EQUT section is parsed with correct values."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    equt = statement.get_section("EQUT")
    assert equt is not None
    assert len(equt.rows) == 1
    assert equt.rows[0]["TotalEquity"] == "100000"
    assert equt.rows[0]["Cash"] == "20000"
    assert equt.rows[0]["StockValue"] == "75000"


def test_parse_flex_csv_extracts_fifo_section() -> None:
    """Test that the FIFO section is parsed with position PnL data."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    fifo = statement.get_section("FIFO")
    assert fifo is not None
    assert len(fifo.rows) == 2
    assert fifo.rows[0]["Symbol"] == "AAPL"
    assert fifo.rows[0]["RealizedPNL"] == "120.5"
    assert fifo.rows[1]["Symbol"] == "MSFT"


def test_parse_flex_csv_extracts_trade_section() -> None:
    """Test that the TRNT section is parsed with trade data."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    trnt = statement.get_section("TRNT")
    assert trnt is not None
    assert len(trnt.rows) == 1
    assert trnt.rows[0]["Symbol"] == "AAPL"
    assert trnt.rows[0]["TradeID"] == "T1"
    assert trnt.rows[0]["Buy/Sell"] == "BUY"


def test_parse_flex_csv_extracts_cash_flow_section() -> None:
    """Test that the CTRN section is parsed with cash flow data."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    ctrn = statement.get_section("CTRN")
    assert ctrn is not None
    assert len(ctrn.rows) == 2
    assert ctrn.rows[0]["TransactionID"] == "CF1"
    assert ctrn.rows[0]["Amount"] == "5000"
    assert ctrn.rows[1]["Type"] == "Ordinary Dividend"


def test_parse_flex_csv_extracts_price_history_section() -> None:
    """Test that the PPPO section is parsed with price history data."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    pppo = statement.get_section("PPPO")
    assert pppo is not None
    assert len(pppo.rows) == 4
    dates = [row["Date"] for row in pppo.rows]
    assert "2026-04-17" in dates
    assert "2026-04-18" in dates


def test_parse_flex_csv_extracts_security_section() -> None:
    """Test that the SECU section is parsed with security identifiers."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    secu = statement.get_section("SECU")
    assert secu is not None
    assert len(secu.rows) == 2
    assert secu.rows[0]["ISIN"] == "US0378331005"
    assert secu.rows[0]["Symbol"] == "AAPL"
    assert secu.rows[1]["ISIN"] == "US5949181045"


def test_parse_flex_csv_handles_missing_section() -> None:
    """Test that requesting a non-existent section returns None."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    assert statement.get_section("NONEXISTENT") is None


def test_parse_flex_csv_extracts_unbc_section() -> None:
    """Test that the UNBC section is parsed with commission breakdown."""
    fixture = FIXTURES_DIR / "daily_sample.csv"
    statement = parse_flex_csv(fixture)

    unbc = statement.get_section("UNBC")
    assert unbc is not None
    assert len(unbc.rows) == 1
    assert unbc.rows[0]["TradeID"] == "T1"
    assert unbc.rows[0]["TotalCommission"] == "1.2"
