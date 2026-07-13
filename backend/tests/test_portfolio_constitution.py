"""Tests for PortfolioConstitutionRepository and PortfolioConstitutionService with SQLite."""

from __future__ import annotations

from app.domains.portfolio_manager.constitution.repository import PortfolioConstitutionRepository
from app.domains.portfolio_manager.constitution.schemas import InvestmentConstitutionUpdate
from app.domains.portfolio_manager.constitution.service import PortfolioConstitutionService
from tests.pm_helpers import make_test_db


def make_service() -> PortfolioConstitutionService:
    db = make_test_db()
    repository = PortfolioConstitutionRepository(db)
    return PortfolioConstitutionService(repository)


def test_get_current_returns_default_when_no_document() -> None:
    service = make_service()
    constitution = service.get_current()
    assert constitution.id == "default"
    assert constitution.target_account_value_usd == 1500000
    assert constitution.target_date == "2035-12-31"
    assert constitution.primary_theme == "AI"
    assert constitution.deposits_count_as_primary_driver is False
    assert "panic_sell_core_ai_assets" in constitution.forbidden_behaviors
    assert constitution.disclaimer
    assert constitution.created_at
    assert constitution.updated_at


def test_update_constitution_success() -> None:
    service = make_service()
    original = service.get_current()
    payload = InvestmentConstitutionUpdate(
        **{
            **original.model_dump(exclude={"id", "created_at", "updated_at", "disclaimer"}),
            "target_account_value_usd": 1600000,
            "primary_theme": "AI infrastructure",
        }
    )
    updated = service.update_current(payload)
    assert updated.target_account_value_usd == 1600000
    assert updated.primary_theme == "AI infrastructure"
    assert updated.disclaimer


def test_reset_restores_default() -> None:
    service = make_service()
    original = service.get_current()
    service.update_current(
        InvestmentConstitutionUpdate(
            **{
                **original.model_dump(exclude={"id", "created_at", "updated_at", "disclaimer"}),
                "target_account_value_usd": 42,
            }
        )
    )
    reset = service.reset_default()
    assert reset.target_account_value_usd == 1500000
    assert reset.target_date == "2035-12-31"
    assert reset.primary_theme == "AI"
