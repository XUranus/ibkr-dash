"""Eval correctness rubrics — global dimensions and agent-specific rubrics.

Provides:
1. GLOBAL_CORRECTNESS_DIMENSIONS: eight global correctness dimensions
2. AGENT_TYPE_MAPPING: agent name → agent type classification
3. Per-agent rubrics for judge evaluation
"""

from __future__ import annotations

from typing import Any


AGENT_TYPE_MAPPING: dict[str, str] = {
    "trade_decision": "decision_agent",
    "daily_position_review": "review_agent",
    "trade_review": "review_agent",
    "risk_assessment": "risk_agent",
    "account_copilot": "account_agent",
}


def get_agent_type(agent_name: str) -> str:
    return AGENT_TYPE_MAPPING.get(agent_name, "unknown")


GLOBAL_CORRECTNESS_DIMENSIONS: dict[str, dict[str, Any]] = {
    "factual_accuracy": {
        "dimension": "factual_accuracy",
        "title": "事实准确性",
        "description": "输出中所有事实陈述与当时可用信息保持一致；不得编造不存在的指标或事件。",
        "severity": "critical",
    },
    "data_grounding": {
        "dimension": "data_grounding",
        "title": "数据依据",
        "description": "结论必须基于提供的账户、行情、工具或上下文信息；不得无依据臆测。",
        "severity": "critical",
    },
    "reasoning_consistency": {
        "dimension": "reasoning_consistency",
        "title": "逻辑一致性",
        "description": "结论、论据、归因、建议之间没有内部矛盾。",
        "severity": "high",
    },
    "risk_awareness": {
        "dimension": "risk_awareness",
        "title": "风险意识",
        "description": "投资相关输出应明确指出潜在风险、下行情景、失效条件。",
        "severity": "high",
    },
    "actionability": {
        "dimension": "actionability",
        "title": "可执行性",
        "description": "建议是否可执行，是否给出条件、仓位、观察点或下一步。",
        "severity": "medium",
    },
    "no_overclaiming": {
        "dimension": "no_overclaiming",
        "title": "不过度承诺",
        "description": "避免稳赚、必涨、无风险、确定性收益等过度承诺。",
        "severity": "high",
    },
    "completeness": {
        "dimension": "completeness",
        "title": "完整性",
        "description": "输出是否覆盖了所有必要维度（如风险、仓位、条件等）。",
        "severity": "medium",
    },
    "data_limitation_transparency": {
        "dimension": "data_limitation_transparency",
        "title": "数据限制透明",
        "description": "当数据不足时是否明确声明，而非用默认值或编造数据填充。",
        "severity": "medium",
    },
}


TRADE_DECISION_RUBRIC: dict[str, dict[str, Any]] = {
    "action_rationality": {
        "dimension": "action_rationality",
        "title": "操作合理性",
        "description": "action（buy/sell/hold/wait）与分析结论一致。",
        "severity": "critical",
    },
    "position_risk_completeness": {
        "dimension": "position_risk_completeness",
        "title": "仓位风险完整性",
        "description": "是否给出仓位建议、止损、失效条件。",
        "severity": "high",
    },
}


DAILY_POSITION_REVIEW_RUBRIC: dict[str, dict[str, Any]] = {
    "attribution_accuracy": {
        "dimension": "attribution_accuracy",
        "title": "归因准确性",
        "description": "涨跌归因是否基于实际数据，不过度归因。",
        "severity": "critical",
    },
}


TRADE_REVIEW_RUBRIC: dict[str, dict[str, Any]] = {
    "historical_accuracy": {
        "dimension": "historical_accuracy",
        "title": "历史准确性",
        "description": "复盘中引用的交易数据是否与实际一致。",
        "severity": "critical",
    },
}


ACCOUNT_COPILOT_RUBRIC: dict[str, dict[str, Any]] = {
    "data_accuracy": {
        "dimension": "data_accuracy",
        "title": "数据准确性",
        "description": "是否准确引用账户数据，不编造。",
        "severity": "critical",
    },
}


AGENT_RUBRIC_REGISTRY: dict[str, dict[str, dict[str, Any]]] = {
    "trade_decision": TRADE_DECISION_RUBRIC,
    "daily_position_review": DAILY_POSITION_REVIEW_RUBRIC,
    "trade_review": TRADE_REVIEW_RUBRIC,
    "account_copilot": ACCOUNT_COPILOT_RUBRIC,
}


def get_rubric_for_agent(agent_name: str) -> dict[str, dict[str, Any]]:
    if not agent_name:
        return {}
    return AGENT_RUBRIC_REGISTRY.get(agent_name, {})


def get_dimensions_for_agent(agent_name: str) -> list[dict[str, Any]]:
    """Return combined global + agent-specific dimensions."""
    agent_type = get_agent_type(agent_name)
    dims = []
    for dim_id, info in GLOBAL_CORRECTNESS_DIMENSIONS.items():
        applies = info.get("applies_to", [])
        if not applies or agent_type in applies:
            dims.append(info)
    agent_rubric = get_rubric_for_agent(agent_name)
    for dim_id, info in agent_rubric.items():
        dims.append(info)
    return dims


__all__ = [
    "GLOBAL_CORRECTNESS_DIMENSIONS",
    "AGENT_TYPE_MAPPING",
    "AGENT_RUBRIC_REGISTRY",
    "TRADE_DECISION_RUBRIC",
    "DAILY_POSITION_REVIEW_RUBRIC",
    "TRADE_REVIEW_RUBRIC",
    "ACCOUNT_COPILOT_RUBRIC",
    "get_agent_type",
    "get_rubric_for_agent",
    "get_dimensions_for_agent",
]
