"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.database import init_database
from app.core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize DB on startup."""
    settings = get_settings()
    setup_logging()
    init_database(settings)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip compression for large JSON responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # --- Register route blueprints ---
    from app.api.routes.health import router as health_router
    from app.api.routes.account import router as account_router
    from app.api.routes.positions import router as positions_router
    from app.api.routes.trades import router as trades_router
    from app.api.routes.cash_flows import router as cash_flows_router
    from app.api.routes.dividends import router as dividends_router
    from app.api.routes.charts import router as charts_router
    from app.api.routes.copilot import router as copilot_router
    from app.api.routes.agent_tasks import router as agent_tasks_router
    from app.api.routes.admin_system import router as admin_system_router
    from app.api.routes.admin_prompts import router as admin_prompts_router

    # New routes
    from app.api.routes.auth import router as auth_router
    from app.api.routes.symbols import router as symbols_router
    from app.api.routes.daily_position_review import router as daily_position_review_router
    from app.api.routes.trade_decision_agent import router as trade_decision_router
    from app.api.routes.trade_review_agent import router as trade_review_router
    from app.api.routes.risk_assessment_agent import router as risk_assessment_router
    from app.api.routes.admin_llm import router as admin_llm_router
    from app.api.routes.admin_ibkr import router as admin_ibkr_router
    from app.api.routes.admin_email import router as admin_email_router

    app.include_router(health_router, prefix="/api")
    app.include_router(account_router, prefix="/api")
    app.include_router(positions_router, prefix="/api")
    app.include_router(trades_router, prefix="/api")
    app.include_router(cash_flows_router, prefix="/api")
    app.include_router(dividends_router, prefix="/api")
    app.include_router(charts_router, prefix="/api")
    app.include_router(copilot_router, prefix="/api")
    app.include_router(agent_tasks_router, prefix="/api")
    app.include_router(admin_system_router, prefix="/api")
    app.include_router(admin_prompts_router, prefix="/api")

    # New route registrations
    app.include_router(auth_router, prefix="/api")
    app.include_router(symbols_router, prefix="/api")
    app.include_router(daily_position_review_router, prefix="/api")
    app.include_router(trade_decision_router, prefix="/api")
    app.include_router(trade_review_router, prefix="/api")
    app.include_router(risk_assessment_router, prefix="/api")
    app.include_router(admin_llm_router, prefix="/api")
    app.include_router(admin_ibkr_router, prefix="/api")
    app.include_router(admin_email_router, prefix="/api")

    return app


app = create_app()
