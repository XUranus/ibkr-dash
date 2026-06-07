---
sidebar_position: 3
title: Trades API
---

# Trades API

The Trades API provides access to your trade history from IBKR Flex reports. You can list individual trades with filters, or get aggregated statistics like total commission and realized P&L.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/trades` | List trades with pagination and filters |
| GET | `/api/trades/summary` | Get aggregated trade statistics |

All endpoints require authentication (unless `AUTH_PASSWORD` is empty).

---

## List Trades

Fetch a paginated list of trade records with optional filters.

### Request

```
GET /api/trades
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | - | Filter trades from this date (`YYYY-MM-DD`) |
| `end_date` | string | - | Filter trades up to this date (`YYYY-MM-DD`) |
| `symbol` | string | - | Filter by ticker symbol (e.g. `AAPL`) |
| `asset_class` | string | - | Filter by asset class (`STK`, `OPT`, etc.) |
| `buy_sell` | string | - | Filter by direction: `BUY` or `SELL` |
| `sort_by` | string | `date_time` | Sort field: `date_time`, `symbol`, `trade_price`, `fifo_pnl_realized` |
| `sort_order` | string | `desc` | Sort direction: `asc` or `desc` |
| `page` | int | `1` | Page number (starts at 1) |
| `page_size` | int | `20` | Items per page (1-200) |

### Examples

```bash
# Get recent trades
curl "http://localhost:8000/api/trades?page=1&page_size=10"

# Filter by date range
curl "http://localhost:8000/api/trades?start_date=2024-01-01&end_date=2024-01-31"

# Filter by symbol and direction
curl "http://localhost:8000/api/trades?symbol=AAPL&buy_sell=BUY"
```

### Response

```json
{
  "items": [
    {
      "account_id": "U1234567",
      "trade_date": "2024-01-15",
      "date_time": "2024-01-15 10:30:00",
      "symbol": "AAPL",
      "description": "APPLE INC",
      "asset_class": "STK",
      "buy_sell": "BUY",
      "quantity": 100,
      "trade_price": 185.50,
      "trade_money": 18550.00,
      "proceeds": -18550.00,
      "taxes": 0,
      "ib_commission": -1.00,
      "net_cash": -18551.00,
      "fifo_pnl_realized": null,
      "exchange": "NASDAQ",
      "order_type": "LMT"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 200,
    "total_pages": 20
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | IBKR account identifier |
| `trade_date` | string | Date of the trade |
| `date_time` | string | Full timestamp of the trade |
| `symbol` | string | Ticker symbol |
| `description` | string | Full asset name |
| `asset_class` | string | Asset class code |
| `buy_sell` | string | `BUY` or `SELL` |
| `quantity` | float | Number of shares/contracts traded |
| `trade_price` | float | Execution price per unit |
| `trade_money` | float | Total trade value |
| `proceeds` | float | Cash proceeds (negative for buys) |
| `taxes` | float | Taxes on the trade |
| `ib_commission` | float | IBKR commission (always negative) |
| `net_cash` | float | Net cash impact including fees |
| `fifo_pnl_realized` | float | FIFO realized P&L (null for buys) |
| `exchange` | string | Exchange where the trade executed |
| `order_type` | string | Order type (`LMT`, `MKT`, `STP`, etc.) |

---

## Get Trade Summary

Get aggregated trade statistics filtered by the same criteria as the list endpoint.

### Request

```
GET /api/trades/summary
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | - | Filter from date |
| `end_date` | string | - | Filter to date |
| `symbol` | string | - | Filter by symbol |
| `asset_class` | string | - | Filter by asset class |
| `buy_sell` | string | - | Filter by direction |

### Example

```bash
# Summary of all trades in January 2024
curl "http://localhost:8000/api/trades/summary?start_date=2024-01-01&end_date=2024-01-31"

# Summary for a specific symbol
curl "http://localhost:8000/api/trades/summary?symbol=AAPL"
```

### Response

```json
{
  "trade_count": 150,
  "buy_count": 80,
  "sell_count": 70,
  "total_commission": -150.00,
  "total_realized_pnl": 12500.00,
  "total_proceeds": 450000.00,
  "symbols_count": 25
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `trade_count` | int | Total number of trades |
| `buy_count` | int | Number of buy trades |
| `sell_count` | int | Number of sell trades |
| `total_commission` | float | Total commissions paid (negative) |
| `total_realized_pnl` | float | Total realized profit/loss |
| `total_proceeds` | float | Total cash proceeds |
| `symbols_count` | int | Number of distinct symbols traded |

---

## Error Handling

| Status | Body | Cause |
|--------|------|-------|
| `401` | `{"detail":"Not authenticated"}` | Missing or expired session |
| `422` | `{"detail":"Invalid date format: ..."}` | Bad date parameter |
| `500` | `{"detail":"Internal server error"}` | Unexpected error |
