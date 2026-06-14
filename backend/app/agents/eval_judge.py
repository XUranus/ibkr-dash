"""LLM-as-Judge evaluation service.

Uses LLM to evaluate agent output quality against correctness rubrics.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.eval_correctness_rubrics import (
    GLOBAL_CORRECTNESS_DIMENSIONS,
    get_agent_type,
    get_dimensions_for_agent,
    get_rubric_for_agent,
)

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_RUBRIC = {
    "answer_relevance": {"max_score": 20, "description": "是否直接回答用户问题"},
    "grounding": {"max_score": 20, "description": "结论是否基于提供的数据"},
    "risk_awareness": {"max_score": 20, "description": "是否充分说明风险"},
    "actionability": {"max_score": 20, "description": "建议是否可执行"},
    "no_overclaiming": {"max_score": 20, "description": "是否避免过度承诺"},
}

CORRECTNESS_JUDGE_SYSTEM_PROMPT = (
    "你是一个严格的 AI 输出质量评测裁判，专门评估 Agent 输出是否符合 correctness 标准。"
    "你必须基于提供的 input、context、case、output 做出判断。"
    "你不能因为自己不同意投资方向就判失败。"
    "你必须使用 0~1 的小数打分；0.6 以下视为该维度失败。"
    "你必须严格按 JSON Schema 输出，不要包裹 markdown。"
)


def _truncate(text: str, max_len: int = 4000) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def _format_dimensions(dimensions: dict[str, dict[str, Any]]) -> str:
    if not dimensions:
        return "- （无）"
    lines = []
    for dim_id, info in dimensions.items():
        title = info.get("title", dim_id)
        desc = info.get("description", "")
        severity = info.get("severity", "")
        lines.append(f"- **{dim_id}** ({title}, severity={severity}): {desc}")
    return "\n".join(lines)


def build_correctness_judge_prompt(
    *,
    agent_name: str,
    eval_scope: str = "agent",
    node_name: str | None = None,
    case: dict,
    output: dict | str,
) -> str:
    """Build user prompt for correctness judge."""
    case = case if isinstance(case, dict) else {}
    input_data = case.get("input") or {}
    expected_behavior = case.get("expected_behavior") or {}
    forbidden = case.get("forbidden_behavior") or []
    expected_dl = case.get("expected_data_limitations") or []
    case_title = case.get("title", "")
    case_description = case.get("description", "") or ""

    agent_type = get_agent_type(agent_name)
    agent_rubric = get_rubric_for_agent(agent_name)
    global_dims = GLOBAL_CORRECTNESS_DIMENSIONS

    if isinstance(output, dict):
        output_text = json.dumps(output, ensure_ascii=False, indent=2)
    else:
        output_text = str(output)

    dim_keys = list(global_dims.keys())[:2]
    agent_keys = list(agent_rubric.keys())[:1] if agent_rubric else dim_keys[1:2]

    prompt = f"""请对以下 Agent 输出进行 correctness 评测。

## Agent 信息
- agent_name: {agent_name}
- agent_type: {agent_type}
- eval_scope: {eval_scope}

## Case 概况
- case_title: {case_title}
- case_description: {_truncate(case_description, 500)}

## 全局正确性维度
{_format_dimensions(global_dims)}

## Agent 专属 Rubric
{_format_dimensions(agent_rubric)}

## 用户输入
{_truncate(json.dumps(input_data, ensure_ascii=False, indent=2), 2000)}

## 期望行为
{_truncate(json.dumps(expected_behavior, ensure_ascii=False, indent=2), 1000)}

## 禁止行为
{json.dumps(forbidden, ensure_ascii=False)}

## Agent 输出
{_truncate(output_text, 4000)}

## JSON 输出 Schema
{{
  "passed": true,
  "overall_score": 0.82,
  "dimension_scores": {{
    "{dim_keys[0]}": 0.9,
    "{agent_keys[0] if agent_keys else dim_keys[0]}": 0.8
  }},
  "failed_dimensions": [],
  "warnings": [],
  "failure_reasons": [],
  "confidence": 0.8
}}

要求：
1. passed: 严格基于 evidence。
2. overall_score: 0~1 之间。
3. dimension_scores: 至少包含上文中提到的所有相关维度，每项 0~1。
4. failed_dimensions: dimension_scores < 0.6 的维度名。
5. failure_reasons: 失败的具体原因。
6. warnings: 警告但未失败的维度。
7. confidence: 0~1，你对判断的把握。
8. 只输出 JSON，不要 markdown 包裹。
"""
    return prompt


def _parse_judge_output(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {}


def _coerce_0_1(value: Any) -> float:
    if not isinstance(value, (int, float)):
        return 0.0
    if value > 1.0:
        return max(0.0, min(1.0, float(value) / 100.0))
    return max(0.0, min(1.0, float(value)))


def normalize_correctness_judge_result(parsed: dict, expected_dimensions: list[str] | None = None) -> dict:
    """Normalize judge JSON to unified structure with 0~1 scores."""
    if not isinstance(parsed, dict):
        parsed = {}
    overall_score = _coerce_0_1(parsed.get("overall_score"))
    passed = parsed.get("passed")
    if not isinstance(passed, bool):
        passed = overall_score >= 0.6

    dim_scores_in = parsed.get("dimension_scores") or parsed.get("dimensions") or {}
    dimension_scores: dict[str, float] = {}
    if isinstance(dim_scores_in, dict):
        for k, v in dim_scores_in.items():
            if isinstance(v, dict):
                score = v.get("score")
                if score is not None:
                    dimension_scores[str(k)] = _coerce_0_1(score)
            elif isinstance(v, (int, float)):
                dimension_scores[str(k)] = _coerce_0_1(v)

    if expected_dimensions:
        for dim in expected_dimensions:
            dimension_scores.setdefault(dim, 0.0)

    failed_dimensions: list[str] = [str(d) for d in (parsed.get("failed_dimensions") or []) if d]
    for dim, score in dimension_scores.items():
        if score < 0.6 and dim not in failed_dimensions:
            failed_dimensions.append(dim)

    warnings = [str(w) for w in (parsed.get("warnings") or []) if w]
    failure_reasons = [str(r) for r in (parsed.get("failure_reasons") or []) if r]
    confidence = _coerce_0_1(parsed.get("confidence"))

    return {
        "passed": bool(passed),
        "overall_score": float(overall_score),
        "dimension_scores": dimension_scores,
        "failed_dimensions": failed_dimensions,
        "warnings": warnings,
        "failure_reasons": failure_reasons,
        "confidence": float(confidence),
    }


def _build_correctness_judge_messages(
    agent_name: str,
    eval_scope: str,
    node_name: str | None,
    case: dict,
    output: dict | str,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": CORRECTNESS_JUDGE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_correctness_judge_prompt(
                agent_name=agent_name,
                eval_scope=eval_scope,
                node_name=node_name,
                case=case,
                output=output,
            ),
        },
    ]


class EvalJudge:
    """LLM-based eval judge for agent output quality.

    Usage:
        judge = EvalJudge(llm_service)
        result = judge.judge_correctness(case=case, output=output)
    """

    def __init__(self, llm_service: Any = None) -> None:
        self.llm_service = llm_service

    def judge_correctness(
        self,
        *,
        case: dict,
        output: dict,
        eval_scope: str = "agent",
        node_name: str | None = None,
    ) -> dict:
        """Evaluate agent output against correctness rubrics.

        Returns dict with: ok, score, max_score, passed, verdict, raw.
        """
        agent_name = str(case.get("agent_name", "unknown") or "unknown")
        expected_dims = [d["dimension"] for d in get_dimensions_for_agent(agent_name)]

        if self.llm_service is None:
            return {
                "ok": False, "score": 0.0, "max_score": 1.0,
                "passed": False, "verdict": "fail",
                "raw": {"failure_reasons": ["LLM_JUDGE_SERVICE_UNAVAILABLE"]},
                "error_code": "LLM_JUDGE_SERVICE_UNAVAILABLE",
            }

        messages = _build_correctness_judge_messages(
            agent_name=agent_name, eval_scope=eval_scope,
            node_name=node_name, case=case, output=output,
        )

        try:
            from app.agents.runtime import ToolCallingRuntime
            runtime = ToolCallingRuntime(self.llm_service, max_rounds=1, agent_name="eval_judge")
            result = runtime.run(messages=messages, tools=[], response_format={"type": "json_object"})
            raw_output = result.get("content", "")
        except Exception as exc:
            logger.warning("Eval judge LLM call failed: %s", exc)
            return {
                "ok": False, "score": 0.0, "max_score": 1.0,
                "passed": False, "verdict": "fail",
                "raw": {"failure_reasons": [f"LLM_JUDGE_CALL_FAILED: {str(exc)[:200]}"]},
                "error_code": "LLM_JUDGE_CALL_FAILED",
            }

        parsed = _parse_judge_output(raw_output)
        if not parsed:
            return {
                "ok": False, "score": 0.0, "max_score": 1.0,
                "passed": False, "verdict": "fail",
                "raw": {"raw_output": raw_output[:1000]},
                "error_code": "LLM_JUDGE_PARSE_FAILED",
            }

        normalized = normalize_correctness_judge_result(parsed, expected_dimensions=expected_dims)
        return {
            "ok": True,
            "score": normalized["overall_score"],
            "max_score": 1.0,
            "passed": normalized["passed"],
            "verdict": "pass" if normalized["passed"] else "fail",
            "raw": normalized,
            "error_code": None,
        }


__all__ = [
    "EvalJudge",
    "build_correctness_judge_prompt",
    "normalize_correctness_judge_result",
    "CORRECTNESS_JUDGE_SYSTEM_PROMPT",
    "DEFAULT_JUDGE_RUBRIC",
]
