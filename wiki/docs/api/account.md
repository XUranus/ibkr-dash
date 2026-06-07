---
sidebar_position: 3
title: Account
---

# Account API

The Account API provides portfolio-level overview data and historical snapshots. Use these endpoints to display the main dashboard metrics and track account value over time.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/account/overview` | Current account overview with key metrics |
| `GET` | `/api/account/snapshots` | Historical daily account snapshots |

Both endpoints require authentication (when enabled).

---

## GET /api/account/overview

Returns the most recent account overview with total equity, cash, asset breakdowns, P&L figures, and day-over-day deltas.

### Request

No parameters. Returns the latest available snapshot.

### Response (200)

```json
{
  "account_id": "U1234567",
  "report_date": "2025-06-01",
  "currency": "USD",
  "total_equity": 125000.50,
  "cash": 15000.25,
  "stock_value": 95000.00,
  "options_value": 8000.00,
  "funds_value": 5000.00,
  "crypto_value": 2000.25,
  "fifo_total_realized_pnl": 12500.00,
  "fifo_total_unrealized_pnl": 3200.50,
  "fifo_total_pnl": 15700.50,
  "cnav_mtm": 125000.50,
  "cnav_twr": 0.125,
  "total_equity_delta": {
    "amount_change": 1500.00,
    "percent_change": 0.012
  },
  "fifo_total_realized_pnl_delta": {
    "amount_change": 200.00,
    "percent_change": 0.016
  },
  "fifo_total_unrealized_pnl_delta": {
    "amount_change": -500.00,
    "percent_change": -0.135
  },
  "fifo_total_pnl_delta": {
    "amount_change": -300.00,
    "percent_change": -0.019
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | IBKR account identifier |
| `report_date` | string | Date of the snapshot (YYYY-MM-DD) |
| `currency` | string | Base currency (e.g., "USD") |
| `total_equity` | float | Total account equity |
| `cash` | float | Available cash balance |
| `stock_value` | float | Total stock positions value |
| `options_value` | float | Total options positions value |
| `funds_value` | float | Total funds/ETFs value |
| `crypto_value` | float | Total crypto positions value |
| `fifo_total_realized_pnl` | float | Cumulative realized P&L (FIFO) |
| `fifo_total_unrealized_pnl` | float | Current unrealized P&L (FIFO) |
| `fifo_total_pnl` | float | Total P&L (realized + unrealized) |
| `cnav_mtm` | float | Client NAV (mark-to-market) |
| `cnav_twr` | float | Time-weighted return |
| `total_equity_delta` | object | Day-over-day equity change |
| `fifo_total_realized_pnl_delta` | object | Day-over-day realized P&L change |
| `fifo_total_unrealized_pnl_delta` | object | Day-over-day unrealized P&L change |
| `fifo_total_pnl_delta` | object | Day-over-day total P&L change |

### Delta Object

Each delta field contains:

| Field | Type | Description |
|-------|------|-------------|
| `amount_change` | float | Absolute change from previous day |
| `percent_change` | float | Percentage change from previous day |

### Asset Breakdown

The response separates your portfolio by asset class:

| Field | Asset Class | Example Value |
|-------|-------------|---------------|
| `stock_value` | Individual stocks (STK) | `95000.00` |
| `options_value` | Options contracts (OPT) | `8000.00` |
| `funds_value` | ETFs and mutual funds (FUND) | `5000.00` |
| `crypto_value` | Cryptocurrency (CRYPTO) | `2000.25` |
| `cash` | Cash and money market | `15000.25` |

The sum of all asset values equals `total_equity`.

### Error Response (404)

```json
{
  "detail": "No account overview data found."
}
```

This happens when no data has been imported yet.

### Example

```bash
curl -b cookies.txt http://localhost:8000/api/account/overview
```

### Example: Rendering in React

```typescript
// Fetch and display account overview
const response = await fetch('/api/account/overview', { credentials: 'include' });
const overview = await response.json();

console.log(`Total Equity: $${overview.total_equity.toLocaleString()}`);
console.log(`Day Change: ${overview.total_equity_delta.percent_change > 0 ? '+' : ''}${(overview.total_equity_delta.percent_change * 100).toFixed(2)}%`);
```

---

## GET /api/account/snapshots

Returns a list of historical daily account snapshots. Use this to build charts showing account value over time.

### Query Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `limit` | integer | `30` | 1-500 | Number of snapshots to return |

### Response (200)

```json
{
  "items": [
    {
      "account_id": "U1234567",
      "report_date": "2025-06-01",
      "currency": "USD",
      "total_equity": 125000.50,
      "cash": 15000.25,
      "stock_value": 95000.00,
      "options_value": 8000.00,
      "funds_value": 5000.00,
      "crypto_value": 2000.25,
      "cnav_mtm": 125000.50,
      "cnav_twr": 0.125,
      "fifo_total_realized_pnl": 12500.00,
      "fifo_total_unrealized_pnl": 3200.50
    },
    {
      "account_id": "U1234567",
      "report_date": "2025-05-31",
      "currency": "USD",
      "total_equity": 123500.50,
      "cash": 14500.25,
      "stock_value": 94000.00,
      "options_value": 7500.00,
      "funds_value": 5000.00,
      "crypto_value": 2500.25,
      "cnav_mtm": 123500.50,
      "cnav_twr": 0.110,
      "fifo_total_realized_pnl": 12300.00,
      "fifo_total_unrealized_pnl": 3700.50
    }
  ]
}
```

### Response Fields (per snapshot)

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | IBKR account identifier |
| `report_date` | string | Date of the snapshot (YYYY-MM-DD) |
| `currency` | string | Base currency |
| `total_equity` | float | Total account equity |
| `cash` | float | Available cash balance |
| `stock_value` | float | Stock positions value |
| `options_value` | float | Options positions value |
| `funds_value` | float | Funds/ETFs value |
| `crypto_value` | float | Crypto positions value |
| `cnav_mtm` | float | Client NAV (mark-to-market) |
| `cnav_twr` | float | Time-weighted return |
| `fifo_total_realized_pnl` | float | Cumulative realized P&L |
| `fifo_total_unrealized_pnl` | float | Unrealized P&L |

### Example

```bash
# Get last 10 snapshots
curl -b cookies.txt "http://localhost:8000/api/account/snapshots?limit=10"

# Get last 90 days
curl -b cookies.txt "http://localhost:8000/api/account/snapshots?limit=90"
```

### Example: Building an Equity Chart

```typescript
// Fetch snapshots and render a line chart
const res = await fetch('/api/account/snapshots?limit=90', { credentials: 'include' });
const { items } = await res.json();

const chartData = items.map(s => ({
  date: s.report_date,
  equity: s.total_equity,
}));

// chartData is ready for ECharts, Recharts, etc.
// [{ date: "2025-06-01", equity: 125000.50 }, ...]
```

---

## Data Source

Account data is imported by the worker module from IBKR Flex CSV reports. The data is stored in the `account_snapshots` SQLite table with one row per account per day. The `UNIQUE(account_id, report_date)` constraint ensures no duplicate snapshots.
