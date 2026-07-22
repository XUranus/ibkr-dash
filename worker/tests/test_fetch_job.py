"""Tests for fetch_job module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from worker.clients.flex_client import FlexClientError, FlexRateLimited
from worker.jobs.fetch_job import (
    _fetch_single_query,
    _is_rate_limited,
    fetch_flex_statements,
)


class TestIsRateLimited:
    """Tests for _is_rate_limited helper."""

    def test_flex_rate_limited_exception(self):
        """FlexRateLimited should be detected as rate limited."""
        exc = FlexRateLimited("Too many requests")
        assert _is_rate_limited(exc) is True

    def test_flex_client_error_with_rate_limit_message(self):
        """FlexClientError with rate limit message should be detected."""
        exc = FlexClientError("Too many requests have been made")
        assert _is_rate_limited(exc) is True

    def test_flex_client_error_without_rate_limit_message(self):
        """FlexClientError without rate limit message should not be detected."""
        exc = FlexClientError("Some other error")
        assert _is_rate_limited(exc) is False

    def test_generic_exception(self):
        """Generic exceptions should not be detected as rate limited."""
        exc = ValueError("Not rate limited")
        assert _is_rate_limited(exc) is False


class TestFetchSingleQuery:
    """Tests for _fetch_single_query function."""

    def test_successful_fetch(self):
        """Successful fetch should return True."""
        client = MagicMock()
        save_path = Path("/tmp/test.xml")

        with patch.object(client, "download_flex_statement") as mock_download:
            result = _fetch_single_query(client, "123456", save_path)

            assert result is True
            mock_download.assert_called_once_with("123456", save_path)

    def test_rate_limited_with_retry(self):
        """Rate limited should retry and eventually succeed."""
        client = MagicMock()
        save_path = Path("/tmp/test.xml")

        call_count = 0

        def side_effect(qid, path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FlexRateLimited("Too many requests")
            # Second call succeeds

        with patch.object(client, "download_flex_statement", side_effect=side_effect):
            with patch("worker.jobs.fetch_job.time.sleep") as mock_sleep:
                result = _fetch_single_query(
                    client, "123456", save_path,
                    max_retries=3,
                    initial_delay=1,  # Short delay for testing
                )

                assert result is True
                assert call_count == 2
                mock_sleep.assert_called_once_with(1)  # First retry delay

    def test_rate_limited_all_retries_exhausted(self):
        """Rate limited with all retries exhausted should return False."""
        client = MagicMock()
        save_path = Path("/tmp/test.xml")

        with patch.object(
            client, "download_flex_statement",
            side_effect=FlexRateLimited("Too many requests")
        ):
            with patch("worker.jobs.fetch_job.time.sleep"):
                result = _fetch_single_query(
                    client, "123456", save_path,
                    max_retries=2,
                    initial_delay=1,
                )

                assert result is False

    def test_non_rate_limit_error_no_retry(self):
        """Non-rate-limit errors should not be retried."""
        client = MagicMock()
        save_path = Path("/tmp/test.xml")

        with patch.object(
            client, "download_flex_statement",
            side_effect=FlexClientError("Some other error")
        ):
            result = _fetch_single_query(
                client, "123456", save_path,
                max_retries=3,
                initial_delay=1,
            )

            assert result is False

    def test_rate_limited_client_error_with_message(self):
        """FlexClientError with rate limit message should retry."""
        client = MagicMock()
        save_path = Path("/tmp/test.xml")

        call_count = 0

        def side_effect(qid, path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FlexClientError("Too many requests have been made")

        with patch.object(client, "download_flex_statement", side_effect=side_effect):
            with patch("worker.jobs.fetch_job.time.sleep"):
                result = _fetch_single_query(
                    client, "123456", save_path,
                    max_retries=3,
                    initial_delay=1,
                )

                assert result is True
                assert call_count == 2


class TestFetchFlexStatements:
    """Tests for fetch_flex_statements function."""

    def test_skip_existing_file(self):
        """Should skip fetch if file exists with >1KB content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            today = "2026-07-22"
            save_path = data_dir / f"123456_{today}.xml"

            # Create file with >1KB content
            save_path.write_text("x" * 2000)

            with patch("worker.jobs.fetch_job.get_settings") as mock_settings:
                mock_settings.return_value.flex_token = "test_token"
                mock_settings.return_value.flex_query_ids = "123456"

                with patch("worker.jobs.fetch_job.date") as mock_date:
                    mock_date.today.return_value.isoformat.return_value = today

                    result = fetch_flex_statements(data_dir=data_dir)

                    assert len(result) == 1
                    assert result[0] == save_path

    def test_fetch_with_inter_query_delay(self):
        """Should add delay between queries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            today = "2026-07-22"

            with patch("worker.jobs.fetch_job.get_settings") as mock_settings:
                mock_settings.return_value.flex_token = "test_token"
                mock_settings.return_value.flex_query_ids = "111111,222222"

                with patch("worker.jobs.fetch_job.date") as mock_date:
                    mock_date.today.return_value.isoformat.return_value = today

                    with patch("worker.jobs.fetch_job.FlexClient") as mock_client_class:
                        mock_client = MagicMock()
                        mock_client_class.return_value = mock_client

                        with patch("worker.jobs.fetch_job.time.sleep") as mock_sleep:
                            fetch_flex_statements(data_dir=data_dir)

                            # Should sleep between queries (not after the last one)
                            mock_sleep.assert_called_once()
                            assert mock_sleep.call_args[0][0] == 5  # _INTER_QUERY_DELAY
