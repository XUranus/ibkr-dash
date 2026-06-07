---
sidebar_position: 4
title: Charts API
---

# Charts API

The Charts API provides data for visualizing your portfolio performance over time. It includes an equity curve (portfolio value over time) and a performance calendar (P&L by month/quarter/year).

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/charts/equity-curve` | Portfolio equity curve time series |
| GET | `/api/charts/performance-calendar` | P&L calendar by period |

All endpoints require authentication (unless `AUTH_PASSWORD` is empty).

---

## Equity Curve

Returns your portfolio's total equity value over time. This data is derived from daily account snapshots and is suitable for line charts.

### Request

```
GET /api/charts/equity-curve
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | earliest | Start date (`YYYY-MM-DD`) |
| `end_date` | string | latest | End date (`YYYY-MM-DD`) |

### Examples

```bash
# Full equity curve
curl "http://localhost:8000/api/charts/equity-curve"

# Last 30 days
curl "http://localhost:8000/api/charts/equity-curve?start_date=2024-01-01&end_date=2024-01-31"

# Year to date
curl "http://localhost:8000/api/charts/equity-curve?start_date=2024-01-01"
```

### Response

```json
{
  "items": [
    {
      "report_date": "2024-01-15",
      "total_equity": 250000.00,
      "total_pnl": 50000.00,
      "net_cost": 200000.00,
      "realized_pnl": 15000.00,
      "daily_mtm": 2500.00,
      "daily_twr": 1.01
    },
    {
      "report_date": "2024-01-16",
      "total_equity": 252500.00,
      "total_pnl": 52500.00,
      "net_cost": 200000.00,
      "realized_pnl": 15000.00,
      "daily_mtm": 2500.00,
      "daily_twr": 1.00
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `report_date` | string | Date of the snapshot |
| `total_equity` | float | Total portfolio value |
| `total_pnl` | float | Total profit/loss |
| `net_cost` | float | Net cost basis |
| `realized_pnl` | float | Cumulative realized P&L |
| `daily_mtm` | float | Daily mark-to-market change |
| `daily_twr` | float | Daily time-weighted return (percentage) |

### Chart Data Format

The equity curve response is structured for direct use in charting libraries:

```typescript
// ECharts line chart example
const res = await fetch('/api/charts/equity-curve');
const { items } = await res.json();

const option = {
  xAxis: {
    type: 'category',
    data: items.map(i => i.report_date),  // ["2024-01-15", "2024-01-16", ...]
  },
  yAxis: {
    type: 'value',
    name: 'Equity ($)',
  },
  series: [{
    type: 'line',
    data: items.map(i => i.total_equity),  // [250000, 252500, ...]
    smooth: true,
  }],
};
```

:::tip
The equity curve is ideal for rendering a line chart on the dashboard. Use `total_equity` for the Y-axis and `report_date` for the X-axis.
:::

---

## Performance Calendar

Returns P&L data organized by time period (month, quarter, or year). This is useful for building a heatmap-style calendar view.

### Request

```
GET /api/charts/performance-calendar
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `view` | string | `month` | Period granularity: `month`, `quarter`, or `year` |
| `anchor` | string | latest | Center the view on this period key (e.g. `2024-01` for month view) |

### Anchor Format by View

| View | Anchor Format | Example |
|------|---------------|---------|
| `month` | `YYYY-MM` | `2024-01` |
| `quarter` | `YYYY-QN` | `2024-Q1` |
| `year` | `YYYY` | `2024` |

### Examples

```bash
# Monthly performance calendar
curl "http://localhost:8000/api/charts/performance-calendar?view=month"

# Quarterly view centered on Q1 2024
curl "http://localhost:8000/api/charts/performance-calendar?view=quarter&anchor=2024-Q1"

# Yearly view
curl "http://localhost:8000/api/charts/performance-calendar?view=year"
```

### Response

```json
{
  "view": "month",
  "anchor": "2024-01",
  "latest_anchor": "2024-03",
  "earliest_anchor": "2023-01",
  "previous_anchor": "2023-12",
  "next_anchor": "2024-02",
  "items": [
    {
      "period_key": "2024-01",
      "label": "Jan 2024",
      "period_start": "2024-01-01",
      "period_end": "2024-01-31",
      "pnl": 5000.00,
      "twr": 2.05,
      "has_data": true
    },
    {
      "period_key": "2024-02",
      "label": "Feb 2024",
      "period_start": "2024-02-01",
      "period_end": "2024-02-29",
      "pnl": -1200.00,
      "twr": -0.47,
      "has_data": true
    }
  ],
  "summary": {
    "positive_periods": 8,
    "negative_periods": 4,
    "total_pnl": 25000.00,
    "periods_with_data": 12
  }
}
```

### Response Fields

**Navigation fields:**

| Field | Type | Description |
|-------|------|-------------|
| `view` | string | Current period granularity |
| `anchor` | string | Current center period |
| `latest_anchor` | string | Most recent period with data |
| `earliest_anchor` | string | Oldest period with data |
| `previous_anchor` | string | Previous page anchor (for pagination) |
| `next_anchor` | string | Next page anchor (for pagination) |

**items[] fields:**

| Field | Type | Description |
|-------|------|-------------|
| `period_key` | string | Unique key for the period |
| `label` | string | Human-readable label |
| `period_start` | string | Start date of the period |
| `period_end` | string | End date of the period |
| `pnl` | float | P&L for the period |
| `twr` | float | Time-weighted return for the period |
| `has_data` | bool | Whether data exists for this period |

**summary fields:**

| Field | Type | Description |
|-------|------|-------------|
| `positive_periods` | int | Count of profitable periods |
| `negative_periods` | int | Count of loss periods |
| `total_pnl` | float | Total P&L across all periods |
| `periods_with_data` | int | Number of periods with data |

### Calendar Heatmap Example

```typescript
// Build a heatmap data array from the calendar response
const res = await fetch('/api/charts/performance-calendar?view=month');
const { items } = await res.json();

const heatmapData = items.map(item => ({
  date: item.period_key,       // "2024-01"
  value: item.pnl,             // 5000.00 or -1200.00
  label: item.label,           // "Jan 2024"
}));

// Color mapping: green for positive, red for negative
const getColor = (pnl: number) => pnl >= 0 ? '#22c55e' : '#ef4444';
```

:::tip
Use the `previous_anchor` and `next_anchor` fields to implement pagination in the calendar view. Pass the anchor value back to the API to navigate between pages.
:::

---

## Error Handling

| Status | Body | Cause |
|--------|------|-------|
| `401` | `{"detail":"Not authenticated"}` | Missing or expired session |
| `422` | `{"detail":"Invalid view: ..."}` | View must be `month`, `quarter`, or `year` |
| `500` | `{"detail":"Internal server error"}` | Unexpected error |
