"""Prompt registry: static registry of all prompt definitions.

Provides a frozen dataclass for prompt definitions and a registry
for display, auditing, and monitoring. Does NOT require runtime
instantiation of prompts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptDefinitionRecord:
    """Immutable record of a prompt definition."""
    prompt_key: str
    display_name: str
    module_name: str
    agent_name: str
    description: str
    default_content: str

    def to_dict(self) -> dict:
        return {
            "prompt_key": self.prompt_key,
            "display_name": self.display_name,
            "module_name": self.module_name,
            "agent_name": self.agent_name,
            "description": self.description,
            "default_content": self.default_content,
        }


# ---- Prompt definitions registry ----

PROMPT_DEFINITIONS: dict[str, PromptDefinitionRecord] = {
    "account_copilot_planner": PromptDefinitionRecord(
        prompt_key="account_copilot_planner",
        display_name="Account Copilot Planner",
        module_name="account_copilot",
        agent_name="planner",
        description="Account Copilot multi-round ReAct planner system prompt.",
        default_content="[loaded from app.agents.account_copilot.planner_prompts.SYSTEM_PROMPT]",
    ),
    "account_copilot_after_approval_final": PromptDefinitionRecord(
        prompt_key="account_copilot_after_approval_final",
        display_name="Account Copilot After-Approval Final Answer",
        module_name="account_copilot",
        agent_name="after_approval_final",
        description="Account Copilot final answer generation after skill approval.",
        default_content="[loaded from app.agents.account_copilot.planner_prompts.ACCOUNT_COPILOT_AFTER_APPROVAL_FINAL_SYSTEM_PROMPT]",
    ),
    "daily_position_review_main": PromptDefinitionRecord(
        prompt_key="daily_position_review_main",
        display_name="Daily Position Review Main",
        module_name="daily_position_review",
        agent_name="main_agent",
        description="Daily position review main agent system prompt for evidence card mode.",
        default_content="[loaded from app.services.daily_position_review_agent]",
    ),
    "daily_symbol_evidence_card": PromptDefinitionRecord(
        prompt_key="daily_symbol_evidence_card",
        display_name="Daily Symbol Evidence Card",
        module_name="daily_position_review",
        agent_name="symbol_evidence_card_agent",
        description="Daily review symbol evidence card sub-agent system prompt.",
        default_content="[loaded from app.services.daily_review_symbol_evidence_agent]",
    ),
    "daily_macro_evidence_card": PromptDefinitionRecord(
        prompt_key="daily_macro_evidence_card",
        display_name="Daily Macro Evidence Card",
        module_name="daily_position_review",
        agent_name="macro_evidence_card_agent",
        description="Daily review macro evidence card sub-agent system prompt.",
        default_content="[loaded from app.services.daily_review_macro_evidence_agent]",
    ),
    "trade_review_main": PromptDefinitionRecord(
        prompt_key="trade_review_main",
        display_name="Trade Review Main",
        module_name="trade_review",
        agent_name="main_agent",
        description="Trade review main agent system prompt.",
        default_content="[loaded from app.agents.trade_review_graph.prompts]",
    ),
    "trade_review_behavior_pattern": PromptDefinitionRecord(
        prompt_key="trade_review_behavior_pattern",
        display_name="Trade Review Behavior Pattern",
        module_name="trade_review",
        agent_name="behavior_pattern_sub_agent",
        description="Trade review behavior pattern analysis sub-agent system prompt.",
        default_content="[loaded from app.agents.trade_review_graph.prompts]",
    ),
    "trade_review_opportunity_cost": PromptDefinitionRecord(
        prompt_key="trade_review_opportunity_cost",
        display_name="Trade Review Opportunity Cost",
        module_name="trade_review",
        agent_name="opportunity_cost_sub_agent",
        description="Opportunity cost analysis sub-agent system prompt.",
        default_content="[loaded from app.agents.trade_review_graph.prompts]",
    ),
    "trade_decision_market_trend": PromptDefinitionRecord(
        prompt_key="trade_decision_market_trend",
        display_name="Trade Decision Market Trend",
        module_name="trade_decision",
        agent_name="market_trend_sub_agent",
        description="Trade decision market trend sub-agent system prompt.",
        default_content="[loaded from app.services.trade_decision_sub_agents]",
    ),
    "trade_decision_fundamental_valuation": PromptDefinitionRecord(
        prompt_key="trade_decision_fundamental_valuation",
        display_name="Trade Decision Fundamental Valuation",
        module_name="trade_decision",
        agent_name="fundamental_valuation_sub_agent",
        description="Trade decision fundamental valuation sub-agent system prompt.",
        default_content="[loaded from app.services.trade_decision_sub_agents]",
    ),
    "trade_decision_event_catalyst": PromptDefinitionRecord(
        prompt_key="trade_decision_event_catalyst",
        display_name="Trade Decision Event Catalyst",
        module_name="trade_decision",
        agent_name="event_catalyst_sub_agent",
        description="Trade decision event catalyst sub-agent system prompt.",
        default_content="[loaded from app.services.trade_decision_sub_agents]",
    ),
}


def list_prompt_definitions() -> list[PromptDefinitionRecord]:
    """Return all registered prompt definitions."""
    return list(PROMPT_DEFINITIONS.values())


def get_prompt_definition(prompt_key: str) -> PromptDefinitionRecord | None:
    """Look up a prompt definition by key."""
    return PROMPT_DEFINITIONS.get(prompt_key)
