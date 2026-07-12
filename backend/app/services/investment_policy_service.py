"""Investment policy service -- global and per-symbol policy management.

Adapted from ibkr-show-public to use SQLite instead of Elasticsearch.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.database import Database
from app.utils.dates import utc_now_iso
from app.schemas.investment_policy import (
    GlobalInvestmentPolicy,
    GlobalInvestmentPolicyUpsert,
    SymbolInvestmentPolicy,
    SymbolInvestmentPolicyUpsert,
    normalize_policy_symbol,
)
from app.services import investment_thesis

logger = logging.getLogger(__name__)


class InvestmentPolicyError(ValueError):
    """Raised when an investment policy request cannot be fulfilled."""


class InvestmentPolicyService:
    """Manages global and per-symbol investment policies in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Global policy
    # ------------------------------------------------------------------

    def get_global_policy(self) -> GlobalInvestmentPolicy:
        row = self.db.execute_one(
            "SELECT * FROM investment_policies WHERE id = 'global'"
        )
        if row:
            return self._row_to_global_policy(row)
        # Return default if none saved
        now = utc_now_iso()
        return GlobalInvestmentPolicy(
            created_at=now,
            updated_at=now,
            risk_profile="balanced",
            target_annual_return_pct=0.20,
            max_drawdown_tolerance_pct=0.25,
            allow_concentrated_position=True,
            allow_single_position_over_20_pct=True,
            allow_leverage=False,
            cash_reserve_pct=0.05,
            preferred_add_styles=["pullback_add", "batch_add"],
            preferred_sell_style="thesis_or_risk_trigger",
            holding_period="medium_to_long",
            notes="Default template. Save to create your own investment policy.",
            enabled=True,
        )

    def upsert_global_policy(self, payload: GlobalInvestmentPolicyUpsert) -> GlobalInvestmentPolicy:
        now = utc_now_iso()
        data = payload.model_dump()
        # Serialize list fields to JSON
        data["preferred_add_styles"] = json.dumps(data.get("preferred_add_styles", []))
        data["id"] = "global"
        data["policy_type"] = "global"
        data["updated_at"] = now
        data.setdefault("created_at", now)

        # Convert booleans to int for SQLite
        for bool_field in [
            "allow_concentrated_position", "allow_single_position_over_20_pct",
            "allow_leverage", "enabled",
        ]:
            if bool_field in data:
                data[bool_field] = int(data[bool_field])

        self.db.upsert("investment_policies", data, conflict_cols=["id"])
        return self.get_global_policy()

    # ------------------------------------------------------------------
    # Symbol policies
    # ------------------------------------------------------------------

    def list_symbol_policies(self, include_disabled: bool = True) -> list[SymbolInvestmentPolicy]:
        if include_disabled:
            rows = self.db.execute(
                "SELECT * FROM investment_policies WHERE policy_type = 'symbol' ORDER BY symbol ASC"
            )
        else:
            rows = self.db.execute(
                "SELECT * FROM investment_policies WHERE policy_type = 'symbol' AND enabled = 1 ORDER BY symbol ASC"
            )
        return [self._row_to_symbol_policy(r) for r in rows]

    def get_symbol_policy(self, symbol: str) -> SymbolInvestmentPolicy | None:
        normalized = normalize_policy_symbol(symbol)
        if not normalized:
            raise InvestmentPolicyError("symbol is required")
        doc_id = f"symbol:{normalized}"
        row = self.db.execute_one(
            "SELECT * FROM investment_policies WHERE id = ?", (doc_id,)
        )
        if row:
            return self._row_to_symbol_policy(row)
        # Fallback: try to build from investment thesis
        fallback = self._fallback_policy_from_thesis(normalized)
        return fallback if fallback.symbol.upper() == normalized.upper() else None

    def get_policy_for_symbol(self, symbol: str) -> dict:
        """Get policy as a backward-compatible dict for agent consumption."""
        normalized = normalize_policy_symbol(symbol)
        if not normalized:
            raise InvestmentPolicyError("symbol is required")
        doc_id = f"symbol:{normalized}"
        row = self.db.execute_one(
            "SELECT * FROM investment_policies WHERE id = ?", (doc_id,)
        )
        if row and row.get("enabled", 1):
            policy = self._row_to_symbol_policy(row)
            return self._compatible_policy_dict(policy, source="user_config")
        fallback = self._fallback_policy_from_thesis(normalized)
        return self._compatible_policy_dict(fallback, source="default_template")

    def upsert_symbol_policy(self, symbol: str, payload: SymbolInvestmentPolicyUpsert) -> SymbolInvestmentPolicy:
        normalized = normalize_policy_symbol(symbol)
        if not normalized:
            raise InvestmentPolicyError("symbol is required")
        now = utc_now_iso()
        doc_id = f"symbol:{normalized}"
        data = payload.model_dump()
        data["symbol"] = normalized
        data["id"] = doc_id
        data["policy_type"] = "symbol"
        data["updated_at"] = now
        data.setdefault("created_at", now)

        # Serialize list fields
        for list_field in ["add_rules", "no_add_triggers", "sell_triggers", "hard_constraints", "soft_preferences", "preferred_add_styles"]:
            if list_field in data:
                data[list_field] = json.dumps(data[list_field])

        # Booleans to int
        data["enabled"] = int(data.get("enabled", True))

        self.db.upsert("investment_policies", data, conflict_cols=["id"])
        result = self.get_symbol_policy(normalized)
        assert result is not None, f"Policy should exist after upsert for {normalized}"
        return result

    def disable_symbol_policy(self, symbol: str) -> SymbolInvestmentPolicy:
        normalized = normalize_policy_symbol(symbol)
        if not normalized:
            raise InvestmentPolicyError("symbol is required")
        doc_id = f"symbol:{normalized}"
        row = self.db.execute_one("SELECT * FROM investment_policies WHERE id = ?", (doc_id,))
        if row is None:
            raise InvestmentPolicyError(f"Symbol policy not found: {normalized}")
        self.db.execute(
            "UPDATE investment_policies SET enabled = 0, updated_at = ? WHERE id = ?",
            (utc_now_iso(), doc_id),
        )
        result = self.get_symbol_policy(normalized)
        assert result is not None, f"Policy should exist after disable for {normalized}"
        return result

    def seed_defaults(self, force: bool = False) -> tuple[list[SymbolInvestmentPolicy], list[SymbolInvestmentPolicy]]:
        """Seed default policies from investment_thesis for all configured symbols."""
        created: list[SymbolInvestmentPolicy] = []
        skipped: list[SymbolInvestmentPolicy] = []
        for symbol in investment_thesis.all_configured_symbols():
            doc_id = f"symbol:{symbol}"
            existing = self.db.execute_one(
                "SELECT * FROM investment_policies WHERE id = ?", (doc_id,)
            )
            template = self._fallback_policy_from_thesis(symbol)
            if existing is not None and not force:
                skipped.append(template)
                continue
            self.upsert_symbol_policy(symbol, SymbolInvestmentPolicyUpsert.model_validate(template.model_dump()))
            created.append(template)
        return created, skipped

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fallback_policy_from_thesis(self, symbol: str) -> SymbolInvestmentPolicy:
        thesis = investment_thesis.get_thesis(symbol)
        now = utc_now_iso()
        asset_role = _asset_role_from_thesis(thesis.role)
        conviction = _conviction_from_risk_class(thesis.risk_class)
        user_preferred_target = thesis.target_position_pct
        user_preferred_max = thesis.max_position_pct
        if user_preferred_target is not None and user_preferred_target > user_preferred_max:
            user_preferred_target = user_preferred_max
        return SymbolInvestmentPolicy(
            id=f"symbol:{thesis.symbol}",
            symbol=thesis.symbol,
            asset_role=asset_role,
            conviction=conviction,
            user_preferred_min_position_pct=0.0,
            user_preferred_target_position_pct=user_preferred_target,
            user_preferred_max_position_pct=user_preferred_max,
            add_rules=list(thesis.add_rules),
            no_add_triggers=list(thesis.no_add_triggers),
            sell_triggers=list(thesis.sell_triggers),
            hard_constraints=[],
            soft_preferences=list(thesis.hold_rules),
            notes="\n".join(thesis.core_thesis),
            enabled=True,
            created_at=now,
            updated_at=now,
            ai_review_status="unknown",
            ai_review_summary=None,
            ai_review_updated_at=None,
        )

    @staticmethod
    def _compatible_policy_dict(policy: SymbolInvestmentPolicy, source: str) -> dict:
        """Build backward-compatible policy dict for agent consumption."""
        data = policy.model_dump()
        user_preference = {
            "asset_role": policy.asset_role,
            "conviction": policy.conviction,
            "user_preferred_target_position_pct": policy.user_preferred_target_position_pct,
            "user_preferred_max_position_pct": policy.user_preferred_max_position_pct,
            "user_preferred_min_position_pct": policy.user_preferred_min_position_pct,
            "add_rules": list(policy.add_rules),
            "no_add_triggers": list(policy.no_add_triggers),
            "sell_triggers": list(policy.sell_triggers),
            "hard_constraints": list(policy.hard_constraints),
            "soft_preferences": list(policy.soft_preferences),
            "notes": policy.notes,
            "enabled": policy.enabled,
            "ai_review_status": policy.ai_review_status,
            "ai_review_summary": policy.ai_review_summary,
            "ai_review_updated_at": policy.ai_review_updated_at,
        }
        data.update({
            "source": source,
            "user_investment_preference": user_preference,
            "role": policy.asset_role,
            "risk_class": policy.conviction,
            "target_position_pct": policy.user_preferred_target_position_pct,
            "max_position_pct": policy.user_preferred_max_position_pct,
            "min_position_pct": policy.user_preferred_min_position_pct,
            "core_thesis": [line for line in policy.notes.splitlines() if line.strip()],
            "hold_rules": list(policy.soft_preferences),
            "review_frequency": "weekly",
        })
        return data

    def _row_to_global_policy(self, row: dict) -> GlobalInvestmentPolicy:
        return GlobalInvestmentPolicy(
            id=row.get("id", "global"),
            risk_profile=row.get("risk_profile", "balanced"),
            target_annual_return_pct=row.get("target_annual_return_pct"),
            max_drawdown_tolerance_pct=row.get("max_drawdown_tolerance_pct"),
            allow_concentrated_position=bool(row.get("allow_concentrated_position", 0)),
            allow_single_position_over_20_pct=bool(row.get("allow_single_position_over_20_pct", 0)),
            allow_leverage=bool(row.get("allow_leverage", 0)),
            cash_reserve_pct=row.get("cash_reserve_pct"),
            preferred_add_styles=_parse_json_list(row.get("preferred_add_styles", "[]")),
            preferred_sell_style=row.get("preferred_sell_style", ""),
            holding_period=row.get("holding_period", ""),
            notes=row.get("notes", ""),
            enabled=bool(row.get("enabled", 1)),
            created_at=row.get("created_at", utc_now_iso()),
            updated_at=row.get("updated_at", utc_now_iso()),
        )

    def _row_to_symbol_policy(self, row: dict) -> SymbolInvestmentPolicy:
        return SymbolInvestmentPolicy(
            id=row.get("id", ""),
            symbol=row.get("symbol", ""),
            asset_role=row.get("asset_role", "unknown"),
            conviction=row.get("conviction", "medium"),
            user_preferred_target_position_pct=row.get("user_preferred_target_position_pct"),
            user_preferred_max_position_pct=row.get("user_preferred_max_position_pct", 0.05),
            user_preferred_min_position_pct=row.get("user_preferred_min_position_pct", 0.0),
            add_rules=_parse_json_list(row.get("add_rules", "[]")),
            no_add_triggers=_parse_json_list(row.get("no_add_triggers", "[]")),
            sell_triggers=_parse_json_list(row.get("sell_triggers", "[]")),
            hard_constraints=_parse_json_list(row.get("hard_constraints", "[]")),
            soft_preferences=_parse_json_list(row.get("soft_preferences", "[]")),
            notes=row.get("notes", ""),
            enabled=bool(row.get("enabled", 1)),
            ai_review_status=row.get("ai_review_status", "unknown"),
            ai_review_summary=row.get("ai_review_summary"),
            ai_review_updated_at=row.get("ai_review_updated_at"),
            created_at=row.get("created_at", utc_now_iso()),
            updated_at=row.get("updated_at", utc_now_iso()),
        )


def _parse_json_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _asset_role_from_thesis(role: str) -> str:
    mapping = {
        investment_thesis.ROLE_CORE_GROWTH: "core_growth",
        investment_thesis.ROLE_BTC_PROXY: "btc_proxy",
        investment_thesis.ROLE_CLOUD_INFRA_GROWTH: "satellite_growth",
        investment_thesis.ROLE_SOFTWARE_PLATFORM: "core_growth",
        investment_thesis.SOCIAL_PLATFORM: "satellite_growth",
        investment_thesis.CORE_BALANCE: "cash_like",
        investment_thesis.OPPORTUNISTIC: "speculative",
        investment_thesis.ROLE_TRADE: "speculative",
        investment_thesis.ROLE_UNKNOWN: "unknown",
    }
    return mapping.get(role, "unknown")


def _conviction_from_risk_class(risk_class: str) -> str:
    if risk_class in {investment_thesis.RISK_CLASS_LOW, investment_thesis.RISK_CLASS_MEDIUM}:
        return "medium"
    if risk_class in {investment_thesis.RISK_CLASS_MEDIUM_HIGH, investment_thesis.RISK_CLASS_HIGH_GROWTH}:
        return "high"
    if risk_class == investment_thesis.RISK_CLASS_EXTREME:
        return "low"
    return "low"
