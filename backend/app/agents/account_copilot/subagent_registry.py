"""Sub-agent registry for Account Copilot.

Provides a registry for sub-agent definitions that the Account Copilot
planner can delegate to.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.agents.account_copilot.subagent_schemas import ACCOUNT_COPILOT_SUBAGENT_SCHEMAS


@dataclass(frozen=True)
class AccountCopilotSubAgentSpec:
    """Immutable specification for an Account Copilot sub-agent."""
    name: str
    display_name: str
    description: str
    when_to_use: list[str]
    when_not_to_use: list[str]
    input_schema: dict[str, Any]
    output_contract: dict[str, Any]
    read_only: bool = True
    approval_required: bool = False
    data_access: list[str] | None = None
    risk_level: Literal["low", "medium", "high"] = "low"
    handler: Callable[..., Any] | None = None

    def prompt_item(self) -> dict[str, Any]:
        """Return a dict suitable for inclusion in planner prompts."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "when_not_to_use": self.when_not_to_use,
            "input_schema": self.input_schema,
            "output_contract": self.output_contract,
            "read_only": self.read_only,
            "approval_required": self.approval_required,
            "data_access": self.data_access or [],
        }


class AccountCopilotSubAgentRegistry:
    """Registry of sub-agents available to the Account Copilot planner."""

    def __init__(self) -> None:
        self._subagents: dict[str, AccountCopilotSubAgentSpec] = {}

    def register(self, spec: AccountCopilotSubAgentSpec) -> None:
        """Register a sub-agent specification.

        Args:
            spec: The sub-agent specification to register.
        """
        self._subagents[spec.name] = spec

    def get(self, name: str | None) -> AccountCopilotSubAgentSpec | None:
        """Retrieve a registered sub-agent by name.

        Args:
            name: The sub-agent name to look up, or None.

        Returns:
            The matching spec, or None if not found or name is falsy.
        """
        if not name:
            return None
        return self._subagents.get(name)

    def list_specs(self) -> list[AccountCopilotSubAgentSpec]:
        """Return all registered sub-agent specifications.

        Returns:
            A list of all registered specs.
        """
        return list(self._subagents.values())

    def list_exposed_specs(self) -> list[AccountCopilotSubAgentSpec]:
        """Return specs that are read-only and do not require approval."""
        return [spec for spec in self._subagents.values() if spec.read_only and not spec.approval_required]

    def to_prompt_items(self) -> list[dict[str, Any]]:
        """Return prompt-ready items for exposed sub-agents."""
        return [spec.prompt_item() for spec in self.list_exposed_specs()]


def build_default_subagent_registry(
    subagent_service: object | None = None,
) -> AccountCopilotSubAgentRegistry:
    """Build the default sub-agent registry from schema definitions."""
    registry = AccountCopilotSubAgentRegistry()
    for schema in ACCOUNT_COPILOT_SUBAGENT_SCHEMAS:
        handler = None
        if (
            subagent_service is not None
            and schema["name"] == "public_market_research_subagent"
        ):
            handler = getattr(subagent_service, "run", None)
        registry.register(
            AccountCopilotSubAgentSpec(
                name=schema["name"],
                display_name=schema["display_name"],
                description=schema["description"],
                when_to_use=list(schema["when_to_use"]),
                when_not_to_use=list(schema["when_not_to_use"]),
                input_schema=schema["input_schema"],
                output_contract=schema["output_contract"],
                read_only=bool(schema["read_only"]),
                approval_required=bool(schema["approval_required"]),
                data_access=list(schema["data_access"]),
                risk_level=schema["risk_level"],
                handler=handler,
            )
        )
    return registry
