from __future__ import annotations

from app.services.eval_simulation_repository import (
    InMemorySyntheticSimulationRepository,
    SyntheticSimulationRepository,
)
from tests.pm_helpers import make_test_db


def test_in_memory_simulation_repository_saves_runs_and_results() -> None:
    repo = InMemorySyntheticSimulationRepository()
    run = {
        "simulation_run_id": "run-1",
        "agent_names": ["trade_decision"],
        "status": "completed",
        "started_at": "2026-01-01T00:00:00+00:00",
    }
    result = {
        "simulation_result_id": "result-1",
        "simulation_run_id": "run-1",
        "agent_name": "trade_decision",
        "status": "skipped",
        "created_at": "2026-01-01T00:00:01+00:00",
    }

    assert repo.save_run(run) == run
    assert repo.get_run("run-1")["simulation_run_id"] == "run-1"
    assert repo.list_runs(agent_name="trade_decision")[0]["simulation_run_id"] == "run-1"
    assert repo.list_runs(status="completed")[0]["simulation_run_id"] == "run-1"

    assert repo.save_result(result) == result
    assert repo.get_result("result-1")["simulation_result_id"] == "result-1"
    assert repo.list_results("run-1")[0]["simulation_result_id"] == "result-1"
    assert repo.get_run("missing") is None
    assert repo.get_result("missing") is None


def test_sqlite_simulation_repository_saves_runs_and_results() -> None:
    db = make_test_db()
    repo = SyntheticSimulationRepository(db)
    run = {
        "simulation_run_id": "run-1",
        "agent_names": ["trade_decision"],
        "status": "completed",
        "started_at": "2026-01-01T00:00:00+00:00",
    }
    result = {
        "simulation_result_id": "result-1",
        "simulation_run_id": "run-1",
        "agent_name": "trade_decision",
        "status": "passed",
        "output": {"many": {"nested": {"fields": "stored in json"}}},
    }

    assert repo.save_run(run) == run
    saved = repo.get_run("run-1")
    assert saved["simulation_run_id"] == "run-1"
    assert saved["agent_names"] == ["trade_decision"]
    assert repo.list_runs(agent_name="trade_decision")[0]["simulation_run_id"] == "run-1"
    assert repo.list_runs(status="completed")[0]["simulation_run_id"] == "run-1"

    assert repo.save_result(result) == result
    saved_result = repo.get_result("result-1")
    assert saved_result["simulation_result_id"] == "result-1"
    assert saved_result["output"]["many"]["nested"]["fields"] == "stored in json"
    assert repo.list_results("run-1")[0]["simulation_result_id"] == "result-1"
    assert repo.get_run("missing") is None
    assert repo.get_result("missing") is None


def test_sqlite_simulation_repository_does_not_embed_results_in_run() -> None:
    db = make_test_db()
    repo = SyntheticSimulationRepository(db)
    run = {
        "simulation_run_id": "run-1",
        "agent_names": ["trade_decision"],
        "status": "completed",
        "results": [{"output": {"position_advice": {"max_position_pct": 12.5}}}],
    }

    repo.save_run(run)
    saved = repo.get_run("run-1")
    assert "results" not in saved
