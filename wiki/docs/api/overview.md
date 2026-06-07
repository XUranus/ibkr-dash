---
sidebar_position: 1
title: API Overview
---

# API Overview

This section documents the IBKR Dash REST API. The API is built with FastAPI and provides endpoints for portfolio data, AI agents, authentication, and administration.

---

## Base URL

All API endpoints are prefixed with `/api`. The base URL depends on your environment:

| Environment | Base URL |
|-------------|----------|
| Local development | `http://localhost:8000/api` |
| Docker | `http://localhost:8080/api` (via Nginx reverse proxy) |
| Production | `https://your-domain.com/api` |

:::tip
During local development, the Vite dev server proxies `/api` requests to `http://localhost:8000`. You can call `/api/health` from the frontend without specifying the full backend URL.
:::

---

## Interactive API Docs

FastAPI auto-generates interactive API documentation:

| URL | Tool | Description |
|-----|------|-------------|
| `/api/docs` | Swagger UI | Try-it-out interface for every endpoint |
| `/api/redoc` | ReDoc | Clean, readable API reference |

Open `http://localhost:8000/docs` in your browser to explore all endpoints interactively.

---

## Authentication

IBKR Dash supports two authentication methods. When `AUTH_PASSWORD` is empty in your `.env` file, authentication is disabled and all endpoints are publicly accessible.

### Cookie-Based Session

1. Call `POST /api/auth/login` with your username and password.
2. The server returns an `httpOnly` cookie named `ibkr_dash_session`.
3. All subsequent requests include this cookie automatically (via `credentials: 'include'` in fetch).
4. The session expires after **7 days**.
5. Call `POST /api/auth/logout` to clear the cookie.

### HTTP Basic Auth

As an alternative to cookies, you can pass credentials via the standard `Authorization` header:

```bash
curl -u admin:your-password http://localhost:8000/api/account/overview
```

This is useful for scripts, CLI tools, and programmatic access.

---

## Response Format

All endpoints return JSON with `Content-Type: application/json`. Successful responses follow this pattern:

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

List endpoints include a `pagination` object. Detail endpoints return the resource directly.

### Empty Responses

DELETE endpoints return HTTP `204 No Content` with no body.

---

## HTTP Status Codes

The API uses standard HTTP status codes:

| Code | Meaning | When It Happens |
|------|---------|-----------------|
| `200` | OK | Successful GET, PUT, POST |
| `201` | Created | Resource created successfully |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Missing or invalid credentials |
| `404` | Not Found | Resource does not exist |
| `413` | Payload Too Large | Request body exceeds 1 MB limit |
| `422` | Unprocessable Entity | Valid request but business logic error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |

### Error Response Body

Error responses include a `detail` field:

```json
{
  "detail": "Invalid username or password"
}
```

For validation errors (422), `detail` is an array:

```json
{
  "detail": [
    {
      "loc": ["body", "symbol"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Rate Limiting

LLM-calling endpoints (copilot chat, agent analysis) are rate-limited to protect your API budget:

| Limit | Window | Scope |
|-------|--------|-------|
| 20 requests | 60 seconds | Per client IP |

Rate-limited endpoints:

- `POST /api/copilot/chat`
- `POST /api/trade-decision/analyze`
- `POST /api/trade-review/review`
- `POST /api/daily-position-review/generate`
- `POST /api/risk-assessment/assess`
- `POST /api/agent/run`

When the limit is exceeded, the API returns:

```json
{
  "detail": "Rate limit exceeded: max 20 requests per 60s. Please try again later."
}
```

Standard data endpoints (account, positions, trades, charts) are **not** rate-limited.

---

## Request Size Limit

The maximum request body size is **1 MB** (1,000,000 bytes). Requests exceeding this limit receive a `413 Payload Too Large` response.

---

## Compression

Responses larger than 1 KB are automatically compressed with GZip. This happens transparently -- no special headers are needed from the client.

---

## CORS

Cross-Origin Resource Sharing is configured via the `CORS_ORIGINS` environment variable. By default, requests from these origins are allowed:

- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000`

CORS requests include credentials (cookies) by default.

---

## Endpoint Groups

The API is organized into these groups:

| Group | Prefix | Description |
|-------|--------|-------------|
| Health | `/api/health` | Service health check |
| Auth | `/api/auth` | Login, logout, session |
| Account | `/api/account` | Portfolio overview, snapshots |
| Positions | `/api/positions` | Position list, summary, detail |
| Trades | `/api/trades` | Trade history, summary |
| Charts | `/api/charts` | Equity curve, performance calendar |
| Copilot | `/api/copilot` | AI chat assistant |
| Agents | `/api/trade-decision`, `/api/trade-review`, `/api/daily-position-review`, `/api/risk-assessment` | AI analysis agents |
| Agent Tasks | `/api/agent` | Background task management |
| Admin | `/api/admin` | System status, LLM, IBKR, email, prompts |

---

## Example: Full Workflow

Here is a typical API workflow using `curl`:

```bash
# 1. Check health
curl http://localhost:8000/api/health

# 2. Log in
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}' \
  -c cookies.txt

# 3. Get account overview (using saved cookie)
curl -b cookies.txt http://localhost:8000/api/account/overview

# 4. List positions
curl -b cookies.txt "http://localhost:8000/api/positions?page=1&page_size=10"

# 5. Log out
curl -X POST -b cookies.txt http://localhost:8000/api/auth/logout
```
