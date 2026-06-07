---
sidebar_position: 2
title: API Routes
description: Complete list of all backend REST endpoints.
---

# API Routes

All routes are prefixed with `/api` and return JSON. Most endpoints require authentication (unless `AUTH_PASSWORD` is empty).

## Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check. Returns `{ "status": "ok" }`. |

## Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Validate credentials, set session cookie. |
| `POST` | `/api/auth/logout` | Clear session cookie. |
| `GET` | `/api/auth/session` | Check current session status. |

### Example: Login

**Request:**
```json
POST /api/auth/login
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "authenticated": true,
  "username": "admin"
}
```

The response sets an `ibkr_dash_session` httpOnly cookie containing an HMAC-signed token.

## Account

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/account/overview` | Latest account snapshot with day-over-day deltas. |
| `GET` | `/api/account/snapshots` | List recent account snapshots. Query: `limit` (1-500, default 30). |

### Example: Account Overview

**Response:**
```json
{
  "account_id": "U1234567",
  "report_date": "2025-06-01",
  "currency": "USD",
  "total_equity": 125000.50,
  "cash": 15000.00,
  "stock_value": 100000.50,
  "fifo_total_realized_pnl": 5200.00,
  "fifo_total_unrealized_pnl": 3100.75,
  "total_equity_delta": {
    "amount_change": 1200.50,
    "percent_change": 0.97
  }
}
```

## Positions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/positions` | List positions with filtering, sorting, pagination. |
| `GET` | `/api/positions/summary` | Aggregated position summary (top 5, asset distribution). |
| `GET` | `/api/positions/{symbol}` | Position detail with OHLC bars and trade markers. |

**Query parameters for list:**
- `report_date` -- Filter by date (defaults to latest)
- `symbol` -- Filter by symbol
- `asset_class` -- Filter by asset class
- `sort_by` -- Sort field (default: `position_value`)
- `sort_order` -- `asc` or `desc` (default: `desc`)
- `page` / `page_size` -- Pagination (default: 1/20, max page_size: 200)
- `include_summary` -- Include aggregated summary (default: `false`)

## Trades

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/trades` | List trades with filtering, sorting, pagination. |
| `GET` | `/api/trades/summary` | Aggregated trade summary. |

**Query parameters:**
- `start_date` / `end_date` -- Date range filter
- `symbol` -- Filter by symbol
- `asset_class` -- Filter by asset class
- `buy_sell` -- Filter by direction (`BUY` / `SELL`)
- `sort_by` / `sort_order` -- Sorting
- `page` / `page_size` -- Pagination

## Cash Flows

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/cash-flows` | List cash flows (deposits, withdrawals, dividends). |

**Query parameters:** `start_date`, `end_date`, `currency`, `flow_direction`, `sort_by`, `sort_order`, `page`, `page_size`.

## Dividends

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/dividends` | List dividend payments. |

**Query parameters:** `start_date`, `end_date`, `currency`, `symbol`, `sort_by`, `sort_order`, `page`, `page_size`.

## Charts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/charts/equity-curve` | Equity curve time series with net cost, PnL, daily MTM/TWR. |
| `GET` | `/api/charts/performance-calendar` | Performance calendar (month/year/all-years view). |

**Query parameters for equity curve:** `start_date`, `end_date`.

**Query parameters for performance calendar:** `view` (`month` / `year` / `all-years`), `anchor` (e.g., `2025-06` for month view).

## Symbols

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/symbols/suggest` | Autocomplete symbol suggestions. |

**Query parameters:** `q` (required, min 1 char), `limit` (1-50, default 10).

## Copilot (AI Chat)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/copilot/chat` | Send a message to the Account Copilot. |
| `GET` | `/api/copilot/sessions` | List copilot sessions. |
| `GET` | `/api/copilot/sessions/{id}/messages` | List messages in a session. |
| `DELETE` | `/api/copilot/sessions/{id}` | Delete a session and its messages. |

### Example: Copilot Chat

**Request:**
```json
POST /api/copilot/chat
{
  "session_id": null,
  "message": "What is my largest position?"
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "abc-123",
  "answer": "Your largest position is AAPL with a value of $45,000...",
  "actions": [],
  "tool_calls": [{"tool": "query_positions", "args": {"sort_by": "position_value"}}],
  "pending_approval": null,
  "errors": []
}
```

## Agent Tasks (Background)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/agent/run` | Run an agent in background. Returns task ID. |
| `GET` | `/api/agent/tasks` | List tasks. Query: `agent_name`, `status`, `limit`. |
| `GET` | `/api/agent/tasks/{id}` | Get task status by ID. |
| `POST` | `/api/agent/tasks/{id}/cancel` | Cancel a running task. |

**Supported agents:** `daily_review`, `trade_decision`, `trade_review`, `risk_assessment`.

## Daily Position Review Agent

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/daily-position-review/generate` | Generate a daily review (synchronous). |
| `GET` | `/api/daily-position-review/dates` | List dates with reviews. |
| `GET` | `/api/daily-position-review/reviews/{date}` | Get review for a specific date. |
| `GET` | `/api/daily-position-review/health` | Agent health check. |

## Trade Decision Agent

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/trade-decision/analyze` | Analyze a trade decision (synchronous). |
| `GET` | `/api/trade-decision/decisions` | List recent decisions. Query: `symbol`, `decision_type`. |
| `GET` | `/api/trade-decision/decisions/{id}` | Get decision by ID. |
| `GET` | `/api/trade-decision/health` | Agent health check. |

## Trade Review Agent

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/trade-review/review` | Trigger a trade review (synchronous). |
| `GET` | `/api/trade-review/reviews` | List recent reviews. Query: `symbol`, `review_type`. |
| `GET` | `/api/trade-review/reviews/{id}` | Get review by ID. |
| `GET` | `/api/trade-review/health` | Agent health check. |

## Risk Assessment Agent

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/risk-assessment/assess` | Trigger a risk assessment (synchronous). |
| `GET` | `/api/risk-assessment/assessments` | List recent assessments. |
| `GET` | `/api/risk-assessment/assessments/{id}` | Get assessment by ID. |
| `GET` | `/api/risk-assessment/health` | Agent health check. |

## Admin

### System Status

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/system/status` | System health, DB status, record counts, runtime info. |

### Prompt Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/prompts` | List all prompt versions. Query: `prompt_key`. |
| `POST` | `/api/admin/prompts` | Create a new prompt version. |
| `GET` | `/api/admin/prompts/{key}/active` | Get the active version of a prompt. |

### LLM Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/llm/providers` | List configured LLM providers. |
| `POST` | `/api/admin/llm/providers` | Register a new LLM provider (no-op in current backend). |
| `POST` | `/api/admin/llm/test` | Test LLM connection with a simple prompt. |
| `GET` | `/api/admin/llm/health` | Check LLM configuration health. |

### IBKR Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/ibkr/settings` | Get IBKR connection settings. |
| `PUT` | `/api/admin/ibkr/settings` | Update IBKR settings. |
| `POST` | `/api/admin/ibkr/test` | Test IBKR connection. |

### Email Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/email/settings` | Get email configuration. |
| `PUT` | `/api/admin/email/settings` | Update email configuration. |
| `POST` | `/api/admin/email/test` | Send a test email. |

## How Routes Use DI

Every protected route includes `_user: str | None = Depends(get_current_user)`. This dependency:

1. Checks if `auth_password` is configured. If not, allows anonymous access.
2. Looks for the `ibkr_dash_session` cookie and verifies the HMAC signature.
3. Falls back to HTTP Basic auth credentials.
4. Raises `401 Unauthorized` if no valid credential is found.

LLM-calling endpoints also include `_rate: None = Depends(check_llm_rate_limit)`, which enforces a sliding-window rate limit of 20 requests per 60 seconds per client IP.

:::info
Admin endpoints are not separately protected. They share the same `get_current_user` dependency. If `AUTH_PASSWORD` is empty, all endpoints are publicly accessible.
:::
