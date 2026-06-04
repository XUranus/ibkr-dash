"""Account Copilot tool registry: registers IBKR data tools."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.agents.account_copilot.tool_schemas import IBKR_ACCOUNT_TOOL_SCHEMAS_BY_NAME


@dataclass(frozen=True)
class AccountCopilotToolSpec:
    """Specification for a single Account Copilot tool."""

    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[..., Any] | None = None
    category: str = "general"
    data_sensitivity: str = "unknown"
    read_only: bool = True
    output_budget_chars: int | None = None


class AccountCopilotToolRegistry:
    """Registry of tools available to the Account Copilot planner."""

    def __init__(self) -> None:
        self._tools: dict[str, AccountCopilotToolSpec] = {}

    def register(self, spec: AccountCopilotToolSpec) -> None:
        self._tools[spec.name] = spec

    def list_specs(self) -> list[AccountCopilotToolSpec]:
        return list(self._tools.values())

    def list_exposed_specs(self) -> list[AccountCopilotToolSpec]:
        return self.list_specs()

    def get(self, name: str) -> AccountCopilotToolSpec | None:
        return self._tools.get(name)

    def to_openai_tools(self, tool_names: list[str] | None = None) -> list[dict]:
        names = tool_names or list(self._tools.keys())
        tools = []
        for name in names:
            spec = self.get(name)
            if spec is None:
                continue
            tools.append({
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.schema.get("parameters", {"type": "object", "properties": {}}),
                },
            })
        return tools


def build_default_tool_registry(
    ibkr_tool_service: object | None = None,
) -> AccountCopilotToolRegistry:
    """Build the default tool registry with IBKR account data tools."""
    registry = AccountCopilotToolRegistry()
    if ibkr_tool_service is not None:
        handlers = {
            "ibkr_get_account_overview": ibkr_tool_service.get_account_overview,
            "ibkr_get_current_positions": ibkr_tool_service.get_current_positions,
            "ibkr_get_symbol_position": ibkr_tool_service.get_symbol_position,
            "ibkr_get_symbol_trades": ibkr_tool_service.get_symbol_trades,
            "ibkr_get_position_history": ibkr_tool_service.get_position_history,
            "ibkr_get_equity_curve": ibkr_tool_service.get_equity_curve,
            "ibkr_get_daily_attribution": ibkr_tool_service.get_daily_attribution,
            "ibkr_get_risk_snapshot": ibkr_tool_service.get_risk_snapshot,
            "ibkr_get_cash_flow_summary": ibkr_tool_service.get_cash_flow_summary,
        }
        for name, handler in handlers.items():
            schema = IBKR_ACCOUNT_TOOL_SCHEMAS_BY_NAME[name]
            registry.register(AccountCopilotToolSpec(
                name=name,
                description=schema["description"],
                schema=schema,
                handler=handler,
                category=schema["category"],
                data_sensitivity=schema["data_sensitivity"],
                read_only=True,
                output_budget_chars=12000,
            ))
    return registry
