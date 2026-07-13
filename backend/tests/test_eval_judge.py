"""Tests for EvalJudge and eval correctness rubrics."""

import json

from app.agents.eval_correctness_rubrics import (
    GLOBAL_CORRECTNESS_DIMENSIONS,
    get_agent_type,
    get_dimensions_for_agent,
    get_rubric_for_agent,
)
from app.agents.eval_judge import (
    EvalJudge,
    build_correctness_judge_prompt,
    normalize_correctness_judge_result,
    _parse_judge_output,
    _coerce_0_1,
)


class TestCorrectnessRubrics:
    def test_global_dimensions_exist(self):
        assert len(GLOBAL_CORRECTNESS_DIMENSIONS) >= 6
        for dim_id, info in GLOBAL_CORRECTNESS_DIMENSIONS.items():
            assert "title" in info
            assert "description" in info
            assert "severity" in info

    def test_get_agent_type(self):
        assert get_agent_type("trade_decision") == "decision_agent"
        assert get_agent_type("daily_position_review") == "review_agent"
        assert get_agent_type("unknown_agent") == "unknown"

    def test_get_rubric_for_agent(self):
        rubric = get_rubric_for_agent("trade_decision")
        assert len(rubric) > 0
        assert "market_context_quality" in rubric

    def test_get_rubric_unknown_agent(self):
        rubric = get_rubric_for_agent("unknown_agent")
        assert rubric == {}

    def test_get_dimensions_for_agent(self):
        dims = get_dimensions_for_agent("trade_decision")
        assert len(dims) >= 6  # global dimensions
        dim_ids = [d["dimension"] for d in dims]
        assert "factual_accuracy" in dim_ids
        assert "data_grounding" in dim_ids


class TestBuildJudgePrompt:
    def test_basic_prompt(self):
        case = {
            "agent_name": "trade_decision",
            "title": "Test case",
            "description": "Test description",
            "input": {"symbol": "AAPL"},
            "expected_behavior": {"action": "hold"},
            "forbidden_behavior": ["No overclaiming"],
        }
        output = {"action": "hold", "summary": "Hold AAPL"}
        prompt = build_correctness_judge_prompt(
            agent_name="trade_decision", case=case, output=output,
        )
        assert "trade_decision" in prompt
        assert "Test case" in prompt
        assert "hold" in prompt

    def test_prompt_with_dict_output(self):
        case = {"agent_name": "trade_decision", "title": "t", "input": {}}
        output = {"action": "buy", "confidence": "high"}
        prompt = build_correctness_judge_prompt(agent_name="trade_decision", case=case, output=output)
        assert "buy" in prompt


class TestParseJudgeOutput:
    def test_valid_json(self):
        raw = '{"passed": true, "overall_score": 0.8}'
        result = _parse_judge_output(raw)
        assert result["passed"] is True
        assert result["overall_score"] == 0.8

    def test_json_with_markdown(self):
        raw = '```json\n{"passed": false, "overall_score": 0.3}\n```'
        result = _parse_judge_output(raw)
        assert result["passed"] is False

    def test_invalid_json(self):
        result = _parse_judge_output("not json at all")
        assert result == {}

    def test_json_embedded_in_text(self):
        raw = 'Here is the result: {"passed": true, "overall_score": 0.9} done.'
        result = _parse_judge_output(raw)
        assert result["passed"] is True


class TestCoerce01:
    def test_within_range(self):
        assert _coerce_0_1(0.5) == 0.5
        assert _coerce_0_1(0.0) == 0.0
        assert _coerce_0_1(1.0) == 1.0

    def test_over_100(self):
        assert _coerce_0_1(80) == 0.8
        assert _coerce_0_1(100) == 1.0

    def test_over_1_under_100(self):
        assert _coerce_0_1(15) == 0.15

    def test_non_numeric(self):
        assert _coerce_0_1(None) == 0.0
        assert _coerce_0_1("abc") == 0.0


class TestNormalizeJudgeResult:
    def test_basic_normalize(self):
        parsed = {
            "passed": True,
            "overall_score": 0.85,
            "dimension_scores": {
                "factual_accuracy": 0.9,
                "data_grounding": 0.8,
            },
            "failed_dimensions": [],
            "warnings": [],
            "failure_reasons": [],
            "confidence": 0.8,
        }
        result = normalize_correctness_judge_result(parsed)
        assert result["passed"] is True
        assert result["overall_score"] == 0.85
        assert result["dimension_scores"]["factual_accuracy"] == 0.9

    def test_auto_failed_dimensions(self):
        parsed = {
            "overall_score": 0.5,
            "dimension_scores": {
                "factual_accuracy": 0.3,
                "data_grounding": 0.9,
            },
        }
        result = normalize_correctness_judge_result(parsed)
        assert "factual_accuracy" in result["failed_dimensions"]
        assert "data_grounding" not in result["failed_dimensions"]
        assert result["passed"] is False

    def test_expected_dimensions_filled(self):
        parsed = {"overall_score": 0.8, "dimension_scores": {"factual_accuracy": 0.9}}
        result = normalize_correctness_judge_result(parsed, expected_dimensions=["factual_accuracy", "data_grounding"])
        assert "data_grounding" in result["dimension_scores"]
        assert result["dimension_scores"]["data_grounding"] == 0.0

    def test_legacy_dict_dimensions(self):
        parsed = {
            "overall_score": 70,
            "dimensions": {
                "factual_accuracy": {"score": 0.8, "max_score": 20, "reason": "ok"},
                "data_grounding": {"score": 0.4, "max_score": 20, "reason": "weak"},
            },
        }
        result = normalize_correctness_judge_result(parsed)
        assert result["dimension_scores"]["factual_accuracy"] == 0.8
        assert result["dimension_scores"]["data_grounding"] == 0.4
        assert "data_grounding" in result["failed_dimensions"]


class TestEvalJudge:
    def test_no_llm_service(self):
        judge = EvalJudge(llm_service=None)
        case = {"agent_name": "trade_decision", "title": "test", "input": {}}
        result = judge.judge_correctness(case=case, output={"action": "hold"})
        assert result["ok"] is False
        assert result["error_code"] == "LLM_JUDGE_SERVICE_UNAVAILABLE"
