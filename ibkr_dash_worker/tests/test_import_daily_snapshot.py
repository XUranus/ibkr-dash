"""Tests for the full daily snapshot import pipeline."""

import sqlite3
from pathlib import Path

from worker.core.config import Settings
from worker.importers.daily_snapshot_importer import DailySnapshotImporter

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "worker" / "fixtures"


def _make_settings(tmp_path: Path) -> Settings:
    """Create test settings with a temporary SQLite database."""
    return Settings(
        app_env="test",
        debug=True,
        sqlite_path=str(tmp_path / "test.db"),
        data_dir=str(FIXTURES_DIR),
        scheduler_enabled=False,
        scheduler_hour=12,
        scheduler_minute=30,
        scheduler_timezone="UTC",
        log_level="DEBUG",
        flex_base_url="https://example.com/flex",
        flex_token="test-token",
        flex_query_id_daily="12345",
        flex_poll_interval_seconds=1,
        flex_max_poll_retries=3,
        backend_base_url="http://localhost:8000",
        daily_review_internal_token="test-token",
    )


def test_import_file_writes_all_entity_types(tmp_path: None) -> None:
    """Test that importing a CSV file writes all entity types to SQLite."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        settings = _make_settings(tmp_path)
        importer = DailySnapshotImporter(settings)

        csv_path = FIXTURES_DIR / "daily_sample.csv"
        counts = importer.import_file(csv_path)

        # Verify counts
        assert counts["account_snapshots"] >= 1
        assert counts["position_snapshots"] >= 2
        assert counts["trade_records"] >= 1
        assert counts["cash_flows"] >= 2
        assert counts["price_history"] >= 4

        # Verify data was actually written
        conn = sqlite3.connect(settings.sqlite_path)
        conn.row_factory = sqlite3.Row

        # Check account snapshots
        rows = conn.execute("SELECT * FROM account_snapshots").fetchall()
        assert len(rows) >= 1
        assert rows[0]["account_id"] == "U1234567"

        # Check position snapshots
        rows = conn.execute("SELECT * FROM position_snapshots ORDER BY symbol").fetchall()
        assert len(rows) >= 2
        symbols = [r["symbol"] for r in rows]
        assert "AAPL" in symbols
        assert "MSFT" in symbols

        # Check trade records
        rows = conn.execute("SELECT * FROM trade_records").fetchall()
        assert len(rows) >= 1
        assert rows[0]["symbol"] == "AAPL"

        # Check cash flows
        rows = conn.execute("SELECT * FROM cash_flows ORDER BY transaction_id").fetchall()
        assert len(rows) >= 2

        # Check price history
        rows = conn.execute("SELECT * FROM price_history").fetchall()
        assert len(rows) >= 4

        conn.close()


def test_import_file_is_idempotent(tmp_path: None) -> None:
    """Test that importing the same file twice does not duplicate data."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        settings = _make_settings(tmp_path)
        importer = DailySnapshotImporter(settings)

        csv_path = FIXTURES_DIR / "daily_sample.csv"

        # Import twice
        counts1 = importer.import_file(csv_path)
        counts2 = importer.import_file(csv_path)

        # Verify data is not duplicated (upsert semantics)
        conn = sqlite3.connect(settings.sqlite_path)
        conn.row_factory = sqlite3.Row

        # Account snapshots use UNIQUE(account_id, report_date)
        rows = conn.execute("SELECT COUNT(*) as cnt FROM account_snapshots").fetchone()
        assert rows["cnt"] == counts1["account_snapshots"]

        # Position snapshots use UNIQUE(account_id, report_date, symbol)
        rows = conn.execute("SELECT COUNT(*) as cnt FROM position_snapshots").fetchone()
        assert rows["cnt"] == counts1["position_snapshots"]

        conn.close()


def test_import_latest_finds_most_recent_csv(tmp_path: None) -> None:
    """Test that import_latest finds and imports the most recent CSV file."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Copy fixture to tmp data dir
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        import shutil
        shutil.copy(FIXTURES_DIR / "daily_sample.csv", data_dir / "snapshot.csv")

        settings = Settings(
            app_env="test",
            debug=True,
            sqlite_path=str(tmp_path / "test.db"),
            data_dir=str(data_dir),
            scheduler_enabled=False,
            scheduler_hour=12,
            scheduler_minute=30,
            scheduler_timezone="UTC",
            log_level="DEBUG",
            flex_base_url="https://example.com/flex",
            flex_token="test-token",
            flex_query_id_daily="12345",
            flex_poll_interval_seconds=1,
            flex_max_poll_retries=3,
            backend_base_url="http://localhost:8000",
            daily_review_internal_token="test-token",
        )
        importer = DailySnapshotImporter(settings)

        result = importer.import_latest()
        assert result is not None
        assert result["account_snapshots"] >= 1
