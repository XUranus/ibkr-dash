"""Sub-agent schema definitions for Account Copilot.

Defines the schema for public market research sub-agent and
any future sub-agents.
"""

from __future__ import annotations


PUBLIC_MARKET_RESEARCH_SUBAGENT_SCHEMA: dict = {
    "name": "public_market_research_subagent",
    "display_name": "Public Market Research Sub-Agent",
    "description": (
        "Explores public market information such as news, financials, valuation, "
        "analyst expectations, candlestick data, and company info. Returns compressed "
        "structured evidence."
    ),
    "when_to_use": [
        "User question requires public market research",
        "Need to call multiple public market tools",
        "Task is exploratory with lots of intermediate evidence, should not pollute main agent context",
        "Question does not need user account, position, trade, or risk data",
    ],
    "when_not_to_use": [
        "User asks for position entry/add/reduce/sell/hold recommendations",
        "User asks to review their historical trades",
        "User asks about account risk, position sizing, margin, cash flow analysis",
        "Question can be directly solved by a registered Skill",
    ],
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "minLength": 1},
            "question": {"type": "string", "minLength": 1},
            "intent": {"type": ["string", "null"]},
        },
        "required": ["symbol", "question"],
        "additionalProperties": False,
    },
    "output_contract": {
        "type": "object",
        "required_fields": [
            "summary",
            "key_facts",
            "bull_case_evidence",
            "bear_case_evidence",
            "missing_information",
            "data_limitations",
        ],
    },
    "read_only": True,
    "approval_required": False,
    "data_access": ["LONGBRIDGE_PUBLIC_MARKET"],
    "risk_level": "low",
}


ACCOUNT_COPILOT_SUBAGENT_SCHEMAS: list[dict] = [
    PUBLIC_MARKET_RESEARCH_SUBAGENT_SCHEMA,
]
