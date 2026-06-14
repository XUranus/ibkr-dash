"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.database import init_database
from app.core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize DB on startup."""
    import logging
    settings = get_settings()
    setup_logging()
    init_database(settings)

    # Auto-seed market events on first startup (harmless if already seeded)
    try:
        from app.core.database import Database
        from app.services.market_event_service import seed_market_events
        db = Database(settings.sqlite_path)
        count = seed_market_events(db)
        logging.getLogger(__name__).info("Auto-seeded %d market events", count)
    except Exception as exc:
        logging.getLogger(__name__).warning("Market events auto-seed failed: %s", exc)

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
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # GZip compression for large JSON responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Limit request body size to prevent abuse
    class BodySizeLimitMiddleware(BaseHTTPMiddleware):
        """ASGI middleware that rejects requests exceeding a configurable body size."""
        def __init__(self, app, max_bytes: int = 1_000_000):
            super().__init__(app)
            self.max_bytes = max_bytes

        async def dispatch(self, request, call_next):
            """Reject oversized requests before forwarding to the next middleware."""
            content_length = request.headers.get('content-length')
            if content_length:
                try:
                    if int(content_length) > self.max_bytes:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": "Request body too large"},
                        )
                except (ValueError, TypeError):
                    # Invalid content-length header — reject
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header"},
                    )
            # For requests without content-length (chunked encoding),
            # read the body with a size limit
            if request.method in ("POST", "PUT", "PATCH") and not content_length:
                body = b""
                async for chunk in request.stream():
                    body += chunk
                    if len(body) > self.max_bytes:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": "Request body too large"},
                        )
                # Replace the stream so downstream can read it
                async def receive():
                    """Replay the buffered body so downstream handlers can read it."""
                    return {"type": "http.request", "body": body}
                request._receive = receive
            return await call_next(request)

    app.add_middleware(BodySizeLimitMiddleware, max_bytes=1_000_000)

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
    from app.api.routes.admin_settings import router as admin_settings_router
    from app.api.routes.admin_monitoring import router as admin_monitoring_router
    from app.api.routes.admin_scheduler import router as admin_scheduler_router
    from app.api.routes.position_analysis import router as position_analysis_router
    from app.api.routes.market_events import router as market_events_router

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
    app.include_router(admin_settings_router, prefix="/api")
    app.include_router(admin_monitoring_router, prefix="/api")
    app.include_router(admin_scheduler_router, prefix="/api")
    app.include_router(position_analysis_router, prefix="/api")
    app.include_router(market_events_router, prefix="/api")

    return app


app = create_app()
