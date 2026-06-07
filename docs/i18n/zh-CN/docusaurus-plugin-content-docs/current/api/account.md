---
sidebar_position: 3
title: 账户
---

# 账户 API

账户 API 提供投资组合级别的概览数据和历史快照。使用这些端点显示主仪表盘指标并跟踪账户价值变化。

---

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/account/overview` | 当前账户概览及关键指标 |
| `GET` | `/api/account/snapshots` | 历史每日账户快照 |

两个端点在启用身份验证时都需要认证。

---

## GET /api/account/overview

返回最新的账户概览，包括总权益、现金、资产分类、盈亏数据和日环比变化。

### 请求

无参数。返回最新的可用快照。

### 响应 (200)

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

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | IBKR 账户标识符 |
| `report_date` | string | 快照日期 (YYYY-MM-DD) |
| `currency` | string | 基础货币（如 "USD"） |
| `total_equity` | float | 账户总权益 |
| `cash` | float | 可用现金余额 |
| `stock_value` | float | 股票持仓总价值 |
| `options_value` | float | 期权持仓总价值 |
| `funds_value` | float | 基金/ETF 总价值 |
| `crypto_value` | float | 加密货币持仓总价值 |
| `fifo_total_realized_pnl` | float | 累计已实现盈亏（FIFO） |
| `fifo_total_unrealized_pnl` | float | 当前未实现盈亏（FIFO） |
| `fifo_total_pnl` | float | 总盈亏（已实现 + 未实现） |
| `cnav_mtm` | float | 客户净资产值（按市值计价） |
| `cnav_twr` | float | 时间加权收益率 |
| `total_equity_delta` | object | 权益日环比变化 |
| `fifo_total_realized_pnl_delta` | object | 已实现盈亏日环比变化 |
| `fifo_total_unrealized_pnl_delta` | object | 未实现盈亏日环比变化 |
| `fifo_total_pnl_delta` | object | 总盈亏日环比变化 |

### Delta 对象

每个 delta 字段包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `amount_change` | float | 与前一日的绝对变化 |
| `percent_change` | float | 与前一日的百分比变化 |

### 资产分类

响应按资产类别将投资组合分开：

| 字段 | 资产类别 | 示例值 |
|------|----------|--------|
| `stock_value` | 个股 (STK) | `95000.00` |
| `options_value` | 期权合约 (OPT) | `8000.00` |
| `funds_value` | ETF 和共同基金 (FUND) | `5000.00` |
| `crypto_value` | 加密货币 (CRYPTO) | `2000.25` |
| `cash` | 现金和货币市场 | `15000.25` |

所有资产价值之和等于 `total_equity`。

### 错误响应 (404)

```json
{
  "detail": "No account overview data found."
}
```

当尚未导入数据时会出现此错误。

### 示例

```bash
curl -b cookies.txt http://localhost:8000/api/account/overview
```

### React 渲染示例

```typescript
// 获取并显示账户概览
const response = await fetch('/api/account/overview', { credentials: 'include' });
const overview = await response.json();

console.log(`总权益: $${overview.total_equity.toLocaleString()}`);
console.log(`日变化: ${overview.total_equity_delta.percent_change > 0 ? '+' : ''}${(overview.total_equity_delta.percent_change * 100).toFixed(2)}%`);
```

---

## GET /api/account/snapshots

返回历史每日账户快照列表。用于构建显示账户价值随时间变化的图表。

### 查询参数

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| `limit` | integer | `30` | 1-500 | 返回的快照数量 |

### 响应 (200)

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

### 响应字段（每个快照）

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | IBKR 账户标识符 |
| `report_date` | string | 快照日期 (YYYY-MM-DD) |
| `currency` | string | 基础货币 |
| `total_equity` | float | 账户总权益 |
| `cash` | float | 可用现金余额 |
| `stock_value` | float | 股票持仓价值 |
| `options_value` | float | 期权持仓价值 |
| `funds_value` | float | 基金/ETF 价值 |
| `crypto_value` | float | 加密货币持仓价值 |
| `cnav_mtm` | float | 客户净资产值（按市值计价） |
| `cnav_twr` | float | 时间加权收益率 |
| `fifo_total_realized_pnl` | float | 累计已实现盈亏 |
| `fifo_total_unrealized_pnl` | float | 未实现盈亏 |

### 示例

```bash
# 获取最近 10 个快照
curl -b cookies.txt "http://localhost:8000/api/account/snapshots?limit=10"

# 获取最近 90 天
curl -b cookies.txt "http://localhost:8000/api/account/snapshots?limit=90"
```

### 构建权益图表示例

```typescript
// 获取快照并渲染折线图
const res = await fetch('/api/account/snapshots?limit=90', { credentials: 'include' });
const { items } = await res.json();

const chartData = items.map(s => ({
  date: s.report_date,
  equity: s.total_equity,
}));

// chartData 可直接用于 ECharts、Recharts 等
// [{ date: "2025-06-01", equity: 125000.50 }, ...]
```

---

## 数据来源

账户数据由 worker 模块从 IBKR Flex CSV 报告导入。数据存储在 `account_snapshots` SQLite 表中，每个账户每天一行。`UNIQUE(account_id, report_date)` 约束确保不会出现重复快照。
