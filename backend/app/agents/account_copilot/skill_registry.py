"""Account Copilot skill registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.agents.account_copilot.skills import ACCOUNT_COPILOT_SKILL_SCHEMAS


@dataclass(frozen=True)
class AccountCopilotSkillSpec:
    """Specification for a single Account Copilot skill."""

    name: str
    display_name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    read_only: bool = True
    approval_required: bool = True
    data_access: list[str] | None = None
    risk_level: Literal["low", "medium", "high"] = "medium"
    handler: Callable[..., Any] | None = None

    def exposed_schema(self) -> dict[str, Any]:
        """Return the schema dict safe to expose to the LLM planner.

        Returns:
            Dictionary with skill metadata excluding the handler and risk level.
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "input_schema": self.input_schema,
            "approval_required": self.approval_required,
            "read_only": self.read_only,
            "data_access": self.data_access or [],
        }


class AccountCopilotSkillRegistry:
    """Registry of skills available to the Account Copilot planner."""

    def __init__(self) -> None:
        self._skills: dict[str, AccountCopilotSkillSpec] = {}

    def register(self, spec: AccountCopilotSkillSpec) -> None:
        """Register a skill spec, keyed by its name.

        Args:
            spec: The skill specification to register.
        """
        self._skills[spec.name] = spec

    def get(self, name: str | None) -> AccountCopilotSkillSpec | None:
        """Look up a skill by name.

        Args:
            name: The skill name, or None/empty to skip lookup.

        Returns:
            The matching skill spec, or None if not found or name is falsy.
        """
        if not name:
            return None
        return self._skills.get(name)

    def list_specs(self) -> list[AccountCopilotSkillSpec]:
        """Return all registered skill specs.

        Returns:
            List of every registered skill specification.
        """
        return list(self._skills.values())

    def list_exposed_specs(self) -> list[AccountCopilotSkillSpec]:
        """Return only skills that are safe to expose to the LLM planner.

        Filters to skills that are both read-only and require approval.

        Returns:
            List of exposed skill specifications.
        """
        return [spec for spec in self._skills.values() if spec.read_only and spec.approval_required]

    def to_prompt_items(self) -> list[dict[str, Any]]:
        """Return exposed skill schemas suitable for inclusion in a prompt."""
        return [spec.exposed_schema() for spec in self.list_exposed_specs()]


def build_default_skill_registry(skill_service: object | None = None) -> AccountCopilotSkillRegistry:
    """Build the default skill registry from skill schemas."""
    registry = AccountCopilotSkillRegistry()
    for schema in ACCOUNT_COPILOT_SKILL_SCHEMAS:
        handler = getattr(skill_service, schema["name"], None) if skill_service is not None else None
        registry.register(AccountCopilotSkillSpec(
            name=schema["name"],
            display_name=schema["display_name"],
            description=schema["description"],
            input_schema=schema["input_schema"],
            output_schema=schema["output_schema"],
            read_only=True,
            approval_required=True,
            data_access=list(schema["data_access"]),
            risk_level=schema["risk_level"],
            handler=handler,
        ))
    return registry
