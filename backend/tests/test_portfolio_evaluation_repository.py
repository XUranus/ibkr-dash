"""Tests for PortfolioEvaluationRepository with SQLite."""

from __future__ import annotations

import uuid

from app.domains.portfolio_manager.evaluation.repository import PortfolioEvaluationRepository
from tests.pm_helpers import make_test_db


def make_repo() -> PortfolioEvaluationRepository:
    return PortfolioEvaluationRepository(make_test_db())


def test_upsert_and_get_result() -> None:
    repo = make_repo()
    result_id = str(uuid.uuid4())
    doc = {"id": result_id, "evaluation_date": "2026-07-13", "source_type": "watchtower_item", "symbol": "AAPL", "horizon": "5d", "evaluation_label": "good_action"}
    upserted = repo.upsert_result(doc)
    assert upserted["id"] == result_id
    fetched = repo.get_result(result_id)
    assert fetched is not None
    assert fetched["evaluation_label"] == "good_action"


def test_list_results_with_filters() -> None:
    repo = make_repo()
    repo.upsert_result({"id": str(uuid.uuid4()), "evaluation_date": "2026-07-13", "source_type": "watchtower_item", "symbol": "AAPL", "horizon": "5d"})
    repo.upsert_result({"id": str(uuid.uuid4()), "evaluation_date": "2026-07-13", "source_type": "auto_decision_item", "symbol": "TSLA", "horizon": "5d"})
    results = repo.list_results(source_type="watchtower_item")
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"


def test_list_symbol_history() -> None:
    repo = make_repo()
    repo.upsert_result({"id": str(uuid.uuid4()), "symbol": "AAPL", "evaluation_date": "2026-07-13", "horizon": "5d"})
    repo.upsert_result({"id": str(uuid.uuid4()), "symbol": "AAPL", "evaluation_date": "2026-07-12", "horizon": "5d"})
    history = repo.list_symbol_history("AAPL")
    assert len(history) == 2


def test_summarize_results() -> None:
    repo = make_repo()
    summary = repo.summarize_results(lookback_days=30)
    assert summary.total_results == 0
    assert summary.pending == 0
