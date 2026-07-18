---
sidebar_position: 10
title: MCP API (External Access)
---

# MCP API — External Data Access

The MCP API provides **read-only** access to portfolio data for external integrations: MCP servers, AI agents, automation tools, and scripts.

Authentication uses **Bearer API tokens** generated in Admin → Access API.

---

## Authentication

All MCP endpoints require a Bearer token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer ibkr_xxxxxxxxxxxx" \
  http://localhost:8080/api/mcp/positions
```

### Getting a Token

1. Open **Admin → Access API** in the dashboard
2. Click **Create Token**
3. Give it a name (e.g., "MCP Server", "AI Agent")
4. Select scopes (or use the default `read` for all access)
5. Copy the token immediately — it's only shown once

### Token Scopes

| Scope | Access |
|-------|--------|
| `read` | All data (default) |
| `read:positions` | Position data |
| `read:account` | Account overview & snapshots |
| `read:trades` | Trade history |
| `read:cashflows` | Cash flows & dividends |
| `read:charts` | Equity curve & performance calendar |
| `read:reviews` | Daily reviews & portfolio reports |

---

## Endpoints

### API Discovery

```
GET /api/mcp
```

Returns the list of available endpoints. Use this for service discovery.

### Positions

```
GET /api/mcp/positions
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_date` | string | Filter by date (YYYY-MM-DD) |
| `symbol` | string | Filter by symbol |
| `limit` | int | Max results (default: 50, max: 500) |

```json
{
  "positions": [
    {
      "report_date": "2025-07-15",
      "symbol": "AAPL",
      "description": "APPLE INC",
      "asset_class": "STK",
      "quantity": 100,
      "mark_price": 210.5,
      "position_value": 21050,
      "cost_basis_money": 18000,
      "percent_of_nav": 0.05,
      "fifo_pnl_unrealized": 3050,
      "total_unrealized_pnl": 3050,
      "previous_day_change_percent": 1.2
    }
  ],
  "count": 1
}
```

### Account Overview

```
GET /api/mcp/account/overview
```

Returns the latest account snapshot with equity, cash, P&L, and NAV breakdown.

### Account Snapshots

```
GET /api/mcp/account/snapshots
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Max snapshots (default: 30) |
| `start_date` | string | Start date filter |
| `end_date` | string | End date filter |

### Trades

```
GET /api/mcp/trades
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | string | Filter by symbol |
| `start_date` | string | Start date |
| `end_date` | string | End date |
| `limit` | int | Max results (default: 50) |

### Cash Flows

```
GET /api/mcp/cash-flows
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `flow_type` | string | Filter: DIV, INT, DEP, etc. |
| `start_date` | string | Start date |
| `end_date` | string | End date |
| `limit` | int | Max results |

### Dividends

```
GET /api/mcp/dividends
```

Shortcut for cash flows filtered to `flow_type = 'DIV'`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Start date |
| `end_date` | string | End date |
| `limit` | int | Max results |

### Equity Curve

```
GET /api/mcp/charts/equity-curve
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Start date |
| `end_date` | string | End date |

Returns daily equity values with TWR and MTM.

### Performance Calendar

```
GET /api/mcp/charts/performance-calendar
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `view` | string | `month`, `year`, or `all` |
| `anchor` | string | YYYY-MM or YYYY |

### Daily Reviews

```
GET /api/mcp/reviews
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_date` | string | Get review for specific date |
| `limit` | int | Max results (default: 10) |

Returns AI-generated daily position reviews.

### Portfolio Reviews

```
GET /api/mcp/portfolio/review
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_date` | string | Get review for specific date |
| `limit` | int | Max results (default: 10) |

Returns portfolio manager review reports.

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `401` | Missing or invalid token |
| `403` | Token lacks required scope |
| `404` | No data found |

```json
{
  "detail": "Invalid or expired API token."
}
```

---

## Examples

### curl

```bash
TOKEN="ibkr_your_token_here"
BASE="http://localhost:8080/api/mcp"

# List all endpoints
curl -H "Authorization: Bearer $TOKEN" $BASE

# Get positions
curl -H "Authorization: Bearer $TOKEN" "$BASE/positions?limit=10"

# Get AAPL positions
curl -H "Authorization: Bearer $TOKEN" "$BASE/positions?symbol=AAPL"

# Get account overview
curl -H "Authorization: Bearer $TOKEN" "$BASE/account/overview"

# Get recent trades
curl -H "Authorization: Bearer $TOKEN" "$BASE/trades?limit=20"

# Get dividends this year
curl -H "Authorization: Bearer $TOKEN" "$BASE/dividends?start_date=2025-01-01"

# Get equity curve
curl -H "Authorization: Bearer $TOKEN" "$BASE/charts/equity-curve"

# Get today's review
curl -H "Authorization: Bearer $TOKEN" "$BASE/reviews?report_date=2025-07-16"
```

### Python

```python
import requests

TOKEN = "ibkr_your_token_here"
BASE = "http://localhost:8080/api/mcp"

headers = {"Authorization": f"Bearer {TOKEN}"}

# Get positions
resp = requests.get(f"{BASE}/positions", headers=headers)
data = resp.json()
print(f"Total positions: {data['count']}")
for pos in data["positions"]:
    print(f"  {pos['symbol']}: ${pos['position_value']:,.2f}")

# Get equity curve
resp = requests.get(f"{BASE}/charts/equity-curve", headers=headers)
curve = resp.json()["equity_curve"]
print(f"Equity history: {len(curve)} data points")
```

### TypeScript / Node.js

```typescript
const TOKEN = "ibkr_your_token_here"
const BASE = "http://localhost:8080/api/mcp"

const headers = { Authorization: `Bearer ${TOKEN}` }

// Get account overview
const res = await fetch(`${BASE}/account/overview`, { headers })
const { overview } = await res.json()
console.log(`Total equity: $${overview.total_equity.toLocaleString()}`)
```

---

## MCP Server Integration

To integrate with an MCP server, configure it to use the IBKR Dash API as a data source:

```json
{
  "name": "ibkr-dash",
  "type": "http",
  "url": "http://your-server:8080/api/mcp",
  "headers": {
    "Authorization": "Bearer ibkr_your_token_here"
  }
}
```

The MCP server can then call any endpoint to retrieve portfolio data for analysis, reporting, or decision-making.
