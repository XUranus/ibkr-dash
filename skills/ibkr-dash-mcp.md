# IBKR Dash MCP Integration Skill

Connect to the IBKR Dash portfolio management system via its MCP (Model Context Protocol) API to access real-time portfolio data, positions, trades, and AI-generated analysis.

## Setup

### Prerequisites
- An API token from IBKR Dash Admin → Access API
- The base URL of your IBKR Dash instance (default: `http://localhost:8080`)

### Authentication
All requests require a Bearer token:

```
Authorization: Bearer ibkr_xxxxxxxxxxxx
```

### Base URL
```
{your-host}/api/mcp
```

## Available Data

| Data | Endpoint | Description |
|------|----------|-------------|
| Positions | `GET /api/mcp/positions` | Current holdings with P&L |
| Account | `GET /api/mcp/account/overview` | Latest equity, cash, NAV |
| Snapshots | `GET /api/mcp/account/snapshots` | Historical equity timeline |
| Trades | `GET /api/mcp/trades` | Trade history |
| Cash Flows | `GET /api/mcp/cash-flows` | Deposits, withdrawals, interest |
| Dividends | `GET /api/mcp/dividends` | Dividend history |
| Equity Curve | `GET /api/mcp/charts/equity-curve` | Daily equity time-series |
| Calendar | `GET /api/mcp/charts/performance-calendar` | P&L heatmap data |
| Reviews | `GET /api/mcp/reviews` | AI daily position reviews |
| Portfolio Review | `GET /api/mcp/portfolio/review` | Portfolio manager reports |

## Usage Patterns

### Get Current Portfolio State
```bash
# Account overview
curl -H "Authorization: Bearer $TOKEN" $BASE/account/overview

# All positions
curl -H "Authorization: Bearer $TOKEN" $BASE/positions

# Specific stock
curl -H "Authorization: Bearer $TOKEN" "$BASE/positions?symbol=AAPL"
```

### Analyze Performance
```bash
# Equity curve for charting
curl -H "Authorization: Bearer $TOKEN" "$BASE/charts/equity-curve?start_date=2025-01-01"

# Monthly P&L calendar
curl -H "Authorization: Bearer $TOKEN" "$BASE/charts/performance-calendar?view=month&anchor=2025-07"

# Recent trades
curl -H "Authorization: Bearer $TOKEN" "$BASE/trades?limit=20"
```

### Get AI Analysis
```bash
# Latest daily review
curl -H "Authorization: Bearer $TOKEN" "$BASE/reviews?limit=1"

# Review for specific date
curl -H "Authorization: Bearer $TOKEN" "$BASE/reviews?report_date=2025-07-15"

# Portfolio review report
curl -H "Authorization: Bearer $TOKEN" "$BASE/portfolio/review?limit=1"
```

## Scopes

Tokens can be scoped to limit access:

- `read` — All data (default)
- `read:positions` — Position data only
- `read:account` — Account overview & snapshots
- `read:trades` — Trade history
- `read:cashflows` — Cash flows & dividends
- `read:charts` — Equity curve & calendar
- `read:reviews` — AI reviews & reports

## Response Format

All endpoints return JSON. List endpoints include `count`:

```json
{
  "positions": [...],
  "count": 42
}
```

## Error Handling

- `401` — Invalid or expired token
- `403` — Token lacks required scope
- `404` — No data found

## Example: Portfolio Summary Script

```bash
#!/bin/bash
TOKEN="ibkr_your_token"
BASE="http://localhost:8080/api/mcp"
AUTH="Authorization: Bearer $TOKEN"

echo "=== Portfolio Summary ==="
overview=$(curl -s -H "$AUTH" "$BASE/account/overview")
echo "Equity: $(echo $overview | jq '.overview.total_equity')"
echo "Cash: $(echo $overview | jq '.overview.cash')"

echo ""
echo "=== Top Positions ==="
curl -s -H "$AUTH" "$BASE/positions?limit=5" | \
  jq -r '.positions[] | "\(.symbol): $\(.position_value) (\(.percent_of_nav * 100)%)"'

echo ""
echo "=== Recent Activity ==="
curl -s -H "$AUTH" "$BASE/trades?limit=5" | \
  jq -r '.trades[] | "\(.trade_date) \(.buy_sell) \(.quantity)x \(.symbol) @ $\(.trade_price)"'
```

## Example: Python Integration

```python
import requests

class IBKRDash:
    def __init__(self, base_url: str, token: str):
        self.base = f"{base_url}/api/mcp"
        self.headers = {"Authorization": f"Bearer {token}"}

    def _get(self, path: str, **params) -> dict:
        resp = requests.get(f"{self.base}{path}", headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def positions(self, **kwargs) -> list:
        return self._get("/positions", **kwargs)["positions"]

    def overview(self) -> dict:
        return self._get("/account/overview")["overview"]

    def trades(self, **kwargs) -> list:
        return self._get("/trades", **kwargs)["trades"]

    def equity_curve(self, **kwargs) -> list:
        return self._get("/charts/equity-curve", **kwargs)["equity_curve"]

    def reviews(self, **kwargs) -> list:
        return self._get("/reviews", **kwargs)["reviews"]

# Usage
dash = IBKRDash("http://localhost:8080", "ibkr_your_token")
overview = dash.overview()
print(f"Total equity: ${overview['total_equity']:,.2f}")

for pos in dash.positions(limit=5):
    print(f"  {pos['symbol']}: ${pos['position_value']:,.2f}")
```
