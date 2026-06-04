"""Account Copilot system and planner prompts."""

from __future__ import annotations

import json
from typing import Any

from app.agents.account_copilot.skill_registry import AccountCopilotSkillRegistry
from app.agents.account_copilot.tool_registry import AccountCopilotToolRegistry


SYSTEM_PROMPT = """You are Account Copilot, an account-level multi-round ReAct planner for IBKR portfolio analysis.

Core decision rules:
1. Each round you select exactly one action_type: call_tool, request_skill_approval, or final_answer.
2. When you lack account facts, positions, trades, cash, PnL, or risk data, call IBKR read-only tools first.
3. When the question needs public market, news, valuation, or macro context, you may call Longbridge public tools if available.
4. When the question requires a Skill (trade decision, trade review, daily review, risk assessment), return request_skill_approval. Never execute Skills directly.
5. When evidence is sufficient or more tool calls won't improve the answer, choose final_answer.
6. If the same tool returns empty/failing data consecutively, stop retrying and answer with existing evidence.

Skill priority:
- Trade decisions (entry/add/reduce/hold) -> trade_decision_entry_skill or trade_decision_holding_skill
- Trade review (mistakes, entry/exit quality) -> trade_review_symbol_skill
- Daily position review -> daily_position_review_skill
- Risk assessment (concentration, margin, liquidity) -> risk_assessment_skill

Fact priority:
1. Latest IBKR tool results have highest priority.
2. Current round observations override memory.
3. Memory is historical context, not current account facts.

Output requirements:
- Output strict JSON matching the planner action schema. No Markdown, no code blocks.
- Do not omit fields; use null, {{}}, or [] for inapplicable fields.
- thought_summary should be a brief high-level rationale, not hidden chain-of-thought.
"""

PLANNER_SCHEMA_HINT = {
    "action_type": "call_tool | final_answer | request_skill_approval",
    "thought_summary": "Brief rationale",
    "evidence_sufficiency": {
        "is_sufficient": False,
        "missing_information": [],
        "confidence": "low | medium | high",
    },
    "tool_name": None,
    "tool_arguments": {},
    "skill_name": None,
    "skill_arguments": {},
    "approval_message": None,
    "final_answer": None,
}

CALL_TOOL_EXAMPLE = {
    "action_type": "call_tool",
    "thought_summary": "Need to read latest AMD position data first.",
    "evidence_sufficiency": {
        "is_sufficient": False,
        "missing_information": ["AMD current position quantity, cost, unrealized PnL"],
        "confidence": "low",
    },
    "tool_name": "ibkr_get_symbol_position",
    "tool_arguments": {"symbol": "AMD"},
    "skill_name": None,
    "skill_arguments": {},
    "approval_message": None,
    "final_answer": None,
}

REQUEST_SKILL_APPROVAL_EXAMPLE = {
    "action_type": "request_skill_approval",
    "thought_summary": "Have position and risk snapshot; risk assessment requires skill execution.",
    "evidence_sufficiency": {
        "is_sufficient": False,
        "missing_information": ["Need risk assessment skill for concentration, drawdown, and risk summary"],
        "confidence": "medium",
    },
    "tool_name": None,
    "tool_arguments": {},
    "skill_name": "risk_assessment_skill",
    "skill_arguments": {"symbol": "AMD"},
    "approval_message": "I will run the risk assessment skill based on your current AMD position and account risk snapshot. Please confirm to proceed.",
    "final_answer": None,
}

FINAL_ANSWER_EXAMPLE = {
    "action_type": "final_answer",
    "thought_summary": "Evidence is sufficient to answer the user's question.",
    "evidence_sufficiency": {
        "is_sufficient": True,
        "missing_information": [],
        "confidence": "medium",
    },
    "tool_name": None,
    "tool_arguments": {},
    "skill_name": None,
    "skill_arguments": {},
    "approval_message": None,
    "final_answer": "Based on your latest IBKR position and risk snapshot, the main AMD risks include position concentration, semiconductor cycle volatility, valuation fluctuation, and single-stock drawdown impact on portfolio. This is for risk identification only and does not constitute buy/sell advice.",
}

PLANNER_ACTION_EXAMPLES = [
    CALL_TOOL_EXAMPLE,
    REQUEST_SKILL_APPROVAL_EXAMPLE,
    FINAL_ANSWER_EXAMPLE,
]


def build_planner_messages(
    state: dict,
    registry: AccountCopilotToolRegistry,
    actions: list[dict],
    observations: list[dict],
    skill_registry: AccountCopilotSkillRegistry | None = None,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    """Build messages for the planner LLM call."""
    payload = {
        "user_input": state.get("user_input"),
        "rolling_summary": state.get("rolling_summary") or "",
        "pinned_facts": state.get("pinned_facts") or {},
        "retrieved_memories": state.get("retrieved_memories") or [],
        "non_compressible_constraints": state.get("non_compressible_constraints") or [],
        "memory_snapshot": state.get("memory_snapshot") or {},
        "recent_messages": state.get("messages") or [],
        "available_top_level_tools": [_tool_prompt_item(spec) for spec in registry.list_exposed_specs()],
        "available_skills": skill_registry.to_prompt_items() if skill_registry is not None else [],
        "previous_actions": [_compact_action(item) for item in actions[-8:]],
        "observations": [_compact_observation(item) for item in observations[-8:]],
        "planner_action_schema": PLANNER_SCHEMA_HINT,
        "planner_action_examples": PLANNER_ACTION_EXAMPLES,
    }
    return [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Based on the following state, plan the next Account Copilot ReAct action. "
                "Output complete JSON object only. Do not omit fields.\n\n"
                f"{json.dumps(payload, ensure_ascii=False, default=str)}"
            ),
        },
    ]


def _tool_prompt_item(spec) -> dict:
    return {
        "name": spec.name,
        "description": spec.description,
        "category": spec.category,
        "data_sensitivity": spec.data_sensitivity,
        "read_only": spec.read_only,
        "parameters": spec.schema.get("parameters", {}),
    }


def _compact_action(action: dict[str, Any]) -> dict:
    return {
        "id": action.get("id"),
        "round": action.get("round"),
        "action_type": action.get("action_type"),
        "tool_name": action.get("tool_name"),
        "skill_name": action.get("skill_name"),
        "thought_summary": action.get("thought_summary"),
        "evidence_sufficiency": action.get("evidence_sufficiency"),
    }


def _compact_observation(observation: dict[str, Any]) -> dict:
    return {
        "id": observation.get("id"),
        "round": observation.get("round"),
        "tool_name": observation.get("tool_name"),
        "skill_name": observation.get("skill_name"),
        "ok": observation.get("ok"),
        "summary": observation.get("data_summary"),
        "data_limitations": observation.get("data_limitations") or [],
        "data_preview": observation.get("data"),
    }
