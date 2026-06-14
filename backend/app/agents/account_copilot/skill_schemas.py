"""Skill schema definitions for Account Copilot.

Defines the schemas for all skills that the Account Copilot planner
can request user approval to execute.
"""

from __future__ import annotations

from typing import Any


NULLABLE_STRING: dict = {"type": ["string", "null"]}

TRADE_DECISION_ENTRY_SKILL: dict = {
    "name": "trade_decision_entry_skill",
    "display_name": "Trade Decision - Entry Analysis",
    "description": (
        "Analyze whether a stock is suitable for opening a position in the current account. "
        "Requires user approval. Read-only access to IBKR account facts and Longbridge public market data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "minLength": 1},
            "question": NULLABLE_STRING,
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
    "output_schema": {"type": "object", "additionalProperties": True},
    "data_access": ["IBKR_ACCOUNT_FACTS", "LONGBRIDGE_PUBLIC_MARKET"],
    "risk_level": "medium",
}

TRADE_DECISION_HOLDING_SKILL: dict = {
    "name": "trade_decision_holding_skill",
    "display_name": "Trade Decision - Holding Analysis",
    "description": (
        "Analyze whether an already-held stock should continue to be held, added to, or reduced. "
        "Requires user approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "minLength": 1},
            "question": NULLABLE_STRING,
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
    "output_schema": {"type": "object", "additionalProperties": True},
    "data_access": ["IBKR_ACCOUNT_FACTS", "IBKR_POSITION_FACTS", "LONGBRIDGE_PUBLIC_MARKET"],
    "risk_level": "medium",
}

TRADE_REVIEW_SYMBOL_SKILL: dict = {
    "name": "trade_review_symbol_skill",
    "display_name": "Trade Review - Symbol",
    "description": (
        "Review historical trade performance, buy/sell points, behavioral issues, "
        "and improvement directions for a symbol. Requires user approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "minLength": 1},
            "start_date": NULLABLE_STRING,
            "end_date": NULLABLE_STRING,
            "question": NULLABLE_STRING,
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
    "output_schema": {"type": "object", "additionalProperties": True},
    "data_access": ["IBKR_TRADE_HISTORY", "IBKR_POSITION_FACTS", "LONGBRIDGE_PUBLIC_MARKET"],
    "risk_level": "medium",
}

DAILY_POSITION_REVIEW_SKILL: dict = {
    "name": "daily_position_review_skill",
    "display_name": "Daily Position Review",
    "description": (
        "Generate daily portfolio review for a given report date. "
        "Requires user approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "report_date": NULLABLE_STRING,
            "question": NULLABLE_STRING,
        },
        "required": [],
        "additionalProperties": False,
    },
    "output_schema": {"type": "object", "additionalProperties": True},
    "data_access": ["IBKR_ACCOUNT_FACTS", "IBKR_POSITION_FACTS", "LONGBRIDGE_PUBLIC_MARKET"],
    "risk_level": "low",
}

RISK_ASSESSMENT_SKILL: dict = {
    "name": "risk_assessment_skill",
    "display_name": "Account Risk Assessment",
    "description": (
        "Generate account-level risk assessment covering concentration, liquidity, "
        "margin, and major risk exposures. Requires user approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": NULLABLE_STRING,
        },
        "required": [],
        "additionalProperties": False,
    },
    "output_schema": {"type": "object", "additionalProperties": True},
    "data_access": ["IBKR_ACCOUNT_FACTS", "IBKR_POSITION_FACTS", "LONGBRIDGE_PUBLIC_MARKET"],
    "risk_level": "low",
}

ACCOUNT_COPILOT_SKILL_SCHEMAS: list[dict[str, Any]] = [
    TRADE_DECISION_ENTRY_SKILL,
    TRADE_DECISION_HOLDING_SKILL,
    TRADE_REVIEW_SYMBOL_SKILL,
    DAILY_POSITION_REVIEW_SKILL,
    RISK_ASSESSMENT_SKILL,
]

ACCOUNT_COPILOT_SKILL_SCHEMAS_BY_NAME: dict[str, dict[str, Any]] = {
    schema["name"]: schema for schema in ACCOUNT_COPILOT_SKILL_SCHEMAS
}
