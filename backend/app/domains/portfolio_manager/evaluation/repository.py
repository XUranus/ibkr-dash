"""SQLite-backed repository for portfolio evaluation results."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from app.core.database import Database
from app.domains.portfolio_manager.common import SQLiteDocStore, utc_now_iso
from app.domains.portfolio_manager.evaluation.schemas import PortfolioEvaluationSummary
from app.domains.portfolio_manager.universe.repository import normalize_universe_symbol


class PortfolioEvaluationRepository:
    def __init__(self, db: Database) -> None:
        self._store = SQLiteDocStore(
            db, "pm_evaluation_results",
            indexed_columns=["evaluation_date", "source_type", "symbol", "horizon", "evaluation_label", "source_id"],
        )

    def upsert_result(self, result_doc: dict) -> dict:
        return self._store.put(result_doc["id"], result_doc)

    def bulk_upsert_results(self, results: list[dict]) -> list[dict]:
        return [self.upsert_result(r) for r in results]

    def get_result(self, result_id: str) -> dict | None:
        return self._store.get(result_id)

    def list_results(
        self,
        *,
        limit: int = 100,
        source_type: str | None = None,
        symbol: str | None = None,
        horizon: str | None = None,
        label: str | None = None,
        source_id: str | None = None,
    ) -> list[dict]:
        filters: dict[str, str | None] = {}
        if source_type:
            filters["source_type"] = source_type
        if symbol:
            filters["symbol"] = normalize_universe_symbol(symbol)
        if horizon:
            filters["horizon"] = horizon
        if label:
            filters["evaluation_label"] = label
        if source_id:
            filters["source_id"] = source_id
        return self._store.list_docs(filters=filters if filters else None, limit=limit)

    def list_symbol_history(self, symbol: str, *, limit: int = 100) -> list[dict]:
        return self.list_results(limit=limit, symbol=normalize_universe_symbol(symbol))

    def summarize_results(self, *, lookback_days: int = 180, horizons: list[str] | None = None) -> PortfolioEvaluationSummary:
        since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).date().isoformat()
        # Get all results and filter in Python (SQLite doesn't have range on indexed columns easily)
        all_results = self._store.list_docs(limit=5000)
        docs = [d for d in all_results if d.get("evaluation_date", "") >= since]
        if horizons:
            docs = [d for d in docs if d.get("horizon") in horizons]
        return build_summary(docs, lookback_days=lookback_days, horizons=horizons or [])


def build_summary(docs: list[dict], *, lookback_days: int, horizons: list[str]) -> PortfolioEvaluationSummary:
    by_source = Counter(str(doc.get("source_type") or "") for doc in docs)
    by_label = Counter(str(doc.get("evaluation_label") or "") for doc in docs)
    pending = by_label.get("pending", 0)
    completed = len(docs) - pending
    watchtower_docs = [doc for doc in docs if doc.get("source_type") == "watchtower_item"]
    auto_docs = [doc for doc in docs if doc.get("source_type") == "auto_decision_item"]
    report_docs = [doc for doc in docs if doc.get("source_type") == "portfolio_report"]
    return PortfolioEvaluationSummary(
        generated_at=utc_now_iso(),
        lookback_days=lookback_days,
        horizons=horizons,
        total_results=len(docs),
        pending=pending,
        completed=completed,
        by_source_type=dict(by_source),
        by_label=dict(by_label),
        watchtower={
            "useful_attention_rate": _rate(watchtower_docs, "useful_attention"),
            "false_positive_rate": _rate(watchtower_docs, "false_positive"),
            "decision_required_count": sum(1 for doc in watchtower_docs if doc.get("source_status") == "decision_required"),
        },
        auto_decision={
            "good_action_rate": _rate(auto_docs, "good_action"),
            "bad_action_rate": _rate(auto_docs, "bad_action"),
            "pending_rate": _rate(auto_docs, "pending"),
        },
        portfolio_report={"attention_symbol_hit_rate": _rate(report_docs, "useful_attention")},
    )


def _rate(docs: list[dict], label: str) -> float:
    completed = [doc for doc in docs if doc.get("evaluation_label") != "pending"]
    if not completed:
        return 0.0
    return round(sum(1 for doc in completed if doc.get("evaluation_label") == label) / len(completed), 6)
