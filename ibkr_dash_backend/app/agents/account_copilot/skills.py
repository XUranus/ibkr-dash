"""Skill definitions for Account Copilot."""

from __future__ import annotations

from typing import Any


NULLABLE_STRING = {"type": ["string", "null"]}

TRADE_DECISION_ENTRY_SKILL = {
    "name": "trade_decision_entry_skill",
    "display_name": "Trade Decision - Entry Analysis",
    "description": "Analyze whether a stock is suitable for opening a new position in the current account. Requires user approval.",
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

TRADE_DECISION_HOLDING_SKILL = {
    "name": "trade_decision_holding_skill",
    "display_name": "Trade Decision - Holding Analysis",
    "description": "Analyze whether an existing holding should be added to, reduced, or maintained. Requires user approval.",
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

TRADE_REVIEW_SYMBOL_SKILL = {
    "name": "trade_review_symbol_skill",
    "display_name": "Trade Review - Symbol",
    "description": "Review historical trade performance, entry/exit quality, and behavioral patterns for a symbol. Requires user approval.",
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

DAILY_POSITION_REVIEW_SKILL = {
    "name": "daily_position_review_skill",
    "display_name": "Daily Position Review",
    "description": "Generate a daily position review for a report date. Requires user approval.",
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

RISK_ASSESSMENT_SKILL = {
    "name": "risk_assessment_skill",
    "display_name": "Account Risk Assessment",
    "description": "Generate account-level risk assessment covering concentration, liquidity, margin and major exposures. Requires user approval.",
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

ACCOUNT_COPILOT_SKILL_SCHEMAS_BY_NAME = {
    schema["name"]: schema for schema in ACCOUNT_COPILOT_SKILL_SCHEMAS
}
