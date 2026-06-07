---
sidebar_position: 2
title: Positions API
---

# Positions API

The Positions API lets you view your current portfolio holdings, get aggregated summaries, and drill down into individual symbols. All endpoints return data from the most recent IBKR Flex report that has been imported into the database.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/positions` | List all positions with pagination and filters |
| GET | `/api/positions/summary` | Get aggregated portfolio summary |
| GET | `/api/positions/{symbol}` | Get detailed history for a single symbol |

All endpoints require authentication (unless `AUTH_PASSWORD` is empty).

---

## List Positions

Fetch a paginated list of positions with optional filters and sorting.

### Request

```
GET /api/positions
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `report_date` | string | latest | Filter by report date (format: `YYYY-MM-DD`) |
| `symbol` | string | - | Filter by stock symbol (e.g. `AAPL`) |
| `asset_class` | string | - | Filter by asset class (e.g. `STK`, `OPT`) |
| `include_summary` | bool | `false` | Include summary data in the response |
| `sort_by` | string | `position_value` | Sort field: `position_value`, `symbol`, `quantity`, `mark_price` |
| `sort_order` | string | `desc` | Sort direction: `asc` or `desc` |
| `page` | int | `1` | Page number (starts at 1) |
| `page_size` | int | `20` | Items per page (1-200) |

### Filter Examples

```bash
# Get the first 10 positions sorted by value
curl "http://localhost:8000/api/positions?page=1&page_size=10&sort_by=position_value&sort_order=desc"

# Filter by symbol
curl "http://localhost:8000/api/positions?symbol=AAPL"

# Filter by asset class (stocks only)
curl "http://localhost:8000/api/positions?asset_class=STK"

# Filter options positions sorted by quantity
curl "http://localhost:8000/api/positions?asset_class=OPT&sort_by=quantity&sort_order=desc"

# Get positions for a specific date
curl "http://localhost:8000/api/positions?report_date=2024-01-15&page_size=50"

# Combine multiple filters
curl "http://localhost:8000/api/positions?asset_class=STK&sort_by=symbol&sort_order=asc&page=1&page_size=100"
```

### Response

```json
{
  "items": [
    {
      "account_id": "U1234567",
      "report_date": "2024-01-15",
      "symbol": "AAPL",
      "description": "APPLE INC",
      "asset_class": "STK",
      "quantity": 100,
      "mark_price": 185.50,
      "position_value": 18550.00,
      "percent_of_nav": 12.5,
      "average_cost_price": 150.00,
      "cost_basis_money": 15000.00,
      "total_realized_pnl": 2000.00,
      "realized_pnl_percent": 13.3,
      "total_unrealized_pnl": 3550.00,
      "unrealized_pnl_percent": 23.7,
      "total_fifo_pnl": 3550.00,
      "previous_day_change_percent": 1.2
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 45,
    "total_pages": 5
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | IBKR account identifier |
| `report_date` | string | Date of the snapshot |
| `symbol` | string | Ticker symbol |
| `description` | string | Full company/asset name |
| `asset_class` | string | Asset class code (`STK`, `OPT`, `FUND`, etc.) |
| `quantity` | float | Number of shares/contracts |
| `mark_price` | float | Current market price |
| `position_value` | float | Total market value (quantity x mark_price) |
| `percent_of_nav` | float | Percentage of net asset value |
| `average_cost_price` | float | Average purchase price |
| `cost_basis_money` | float | Total cost basis |
| `total_realized_pnl` | float | Realized profit/loss |
| `total_unrealized_pnl` | float | Unrealized profit/loss |
| `previous_day_change_percent` | float | Daily change percentage |

### Asset Class Codes

| Code | Description |
|------|-------------|
| `STK` | Stocks / ETFs |
| `OPT` | Options |
| `FUND` | Mutual funds |
| `CRYPTO` | Cryptocurrency |
| `BOND` | Bonds |
| `WAR` | Warrants |

---

## Get Position Summary

Get an aggregated view of your portfolio including top holdings and asset distribution.

### Request

```
GET /api/positions/summary
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `report_date` | string | latest | Filter by report date |
| `symbol` | string | - | Filter by symbol |
| `asset_class` | string | - | Filter by asset class |

### Example

```bash
curl "http://localhost:8000/api/positions/summary"
```

### Response

```json
{
  "report_date": "2024-01-15",
  "total_positions": 45,
  "total_position_value": 250000.00,
  "total_cost_basis_money": 200000.00,
  "total_realized_pnl": 15000.00,
  "total_unrealized_pnl": 50000.00,
  "total_fifo_pnl": 50000.00,
  "top_positions": [
    {
      "symbol": "AAPL",
      "description": "APPLE INC",
      "asset_class": "STK",
      "position_value": 18550.00,
      "percent_of_nav": 7.4
    }
  ],
  "asset_distribution": [
    {
      "asset_class": "STK",
      "position_value": 200000.00,
      "positions_count": 30
    },
    {
      "asset_class": "OPT",
      "position_value": 50000.00,
      "positions_count": 15
    }
  ]
}
```

---

## Get Position Detail

Get detailed history for a single symbol, including price bars and trade markers.

### Request

```
GET /api/positions/{symbol}
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | string | The ticker symbol (e.g. `AAPL`) |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `asset_class` | string | - | Disambiguate if the same symbol exists in multiple asset classes |

### Example

```bash
curl "http://localhost:8000/api/positions/AAPL"
```

### Response

```json
{
  "symbol": "AAPL",
  "description": "APPLE INC",
  "asset_class": "STK",
  "bars": [
    {
      "report_date": "2024-01-15",
      "open_price": 180.00,
      "high_price": 186.00,
      "low_price": 179.50,
      "close_price": 185.50,
      "quantity": 100
    }
  ],
  "trades": [
    {
      "trade_date": "2024-01-10",
      "buy_sell": "BUY",
      "quantity": 50,
      "trade_price": 175.00,
      "fifo_pnl_realized": null
    }
  ]
}
```

### Response Fields

**bars** -- Historical price data for charting:

| Field | Type | Description |
|-------|------|-------------|
| `report_date` | string | Date of the snapshot |
| `open_price` | float | Opening price |
| `high_price` | float | High price |
| `low_price` | float | Low price |
| `close_price` | float | Closing price |
| `quantity` | float | Shares held on that date |

**trades** -- Trade events overlaid on the chart:

| Field | Type | Description |
|-------|------|-------------|
| `trade_date` | string | Date of the trade |
| `buy_sell` | string | `BUY` or `SELL` |
| `quantity` | float | Number of shares traded |
| `trade_price` | float | Execution price |
| `fifo_pnl_realized` | float | Realized P&L (null for open positions) |

---

## Error Handling

| Status | Body | Cause |
|--------|------|-------|
| `401` | `{"detail":"Not authenticated"}` | Missing or expired session |
| `422` | `{"detail":"Invalid date format: ..."}` | Bad query parameter value |
| `500` | `{"detail":"Internal server error"}` | Unexpected error |
