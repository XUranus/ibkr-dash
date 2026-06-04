# Architecture

## Overview

IBKR Dash is a personal investment portfolio dashboard that combines Interactive Brokers account data with AI-powered analysis agents.

## Modules

```
ibkr-dash/
├── ibkr_dash_backend/    # FastAPI server + AI agents
├── ibkr_dash_worker/     # Data ETL (IBKR Flex CSV → SQLite)
├── ibkr_dash_frontend/   # React + TypeScript dashboard
├── docker/               # Dockerfiles and nginx config
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Data Flow

```
IBKR Flex CSV → Worker (parse/transform) → SQLite ← Backend (API) ← Frontend
                                                     ↓
                                               AI Agents (LLM)
```

## Storage

| Component | Storage | Why |
|-----------|---------|-----|
| Financial data | SQLite | Single user, ~300K rows max, structured queries only |
| Agent outputs | SQLite | Same DB, no need for separate store |
| Cache | In-memory dict | Single process, TTL-based expiration |

## Agent Architecture

Agents follow a common pattern:
1. **Build evidence** — query SQLite for account/position/trade data
2. **Call LLM** — with structured output contract
3. **Validate** — Pydantic model validation
4. **Repair** — if JSON is malformed, retry with repair prompt
5. **Fallback** — if still failing, produce a safe default
6. **Save** — persist to SQLite

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/health` | Health check |
| `/api/account` | Account overview and snapshots |
| `/api/positions` | Position listing and detail |
| `/api/trades` | Trade history |
| `/api/cash-flows` | Cash flow records |
| `/api/dividends` | Dividend records |
| `/api/charts` | Equity curve and performance calendar |
| `/api/copilot` | AI copilot chat |
| `/api/agent/*` | Agent task management |
| `/api/admin/*` | Admin endpoints |
