---
sidebar_position: 3
title: 交易 API
---

# 交易 API

交易 API 提供对 IBKR Flex 报告中交易历史的访问。您可以列出带筛选条件的单笔交易，或获取总佣金和已实现盈亏等汇总统计。

---

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trades` | 列出交易（支持分页和筛选） |
| GET | `/api/trades/summary` | 获取交易汇总统计 |

所有端点在 `AUTH_PASSWORD` 非空时需要身份验证。

---

## 列出交易

获取带可选筛选条件的分页交易记录列表。

### 请求

```
GET /api/trades
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start_date` | string | - | 筛选此日期之后的交易（`YYYY-MM-DD`） |
| `end_date` | string | - | 筛选此日期之前的交易（`YYYY-MM-DD`） |
| `symbol` | string | - | 按股票代码筛选（如 `AAPL`） |
| `asset_class` | string | - | 按资产类别筛选（`STK`、`OPT` 等） |
| `buy_sell` | string | - | 按方向筛选：`BUY` 或 `SELL` |
| `sort_by` | string | `date_time` | 排序字段：`date_time`、`symbol`、`trade_price`、`fifo_pnl_realized` |
| `sort_order` | string | `desc` | 排序方向：`asc` 或 `desc` |
| `page` | int | `1` | 页码（从 1 开始） |
| `page_size` | int | `20` | 每页条目数（1-200） |

### 筛选示例

```bash
# 获取最近的交易
curl "http://localhost:8000/api/trades?page=1&page_size=10"

# 按日期范围筛选
curl "http://localhost:8000/api/trades?start_date=2024-01-01&end_date=2024-01-31"

# 按标的和方向筛选
curl "http://localhost:8000/api/trades?symbol=AAPL&buy_sell=BUY"

# 仅期权卖出交易
curl "http://localhost:8000/api/trades?asset_class=OPT&buy_sell=SELL"

# 按已实现盈亏排序（最盈利的在前）
curl "http://localhost:8000/api/trades?sort_by=fifo_pnl_realized&sort_order=desc"

# 特定标的在日期范围内的交易
curl "http://localhost:8000/api/trades?symbol=MSFT&start_date=2024-01-01&end_date=2024-03-31&sort_by=date_time&sort_order=asc"
```

### 响应

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

### 响应模式

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | IBKR 账户标识符 |
| `trade_date` | string | 交易日期 |
| `date_time` | string | 交易完整时间戳 |
| `symbol` | string | 股票代码 |
| `description` | string | 完整资产名称 |
| `asset_class` | string | 资产类别代码 |
| `buy_sell` | string | `BUY`（买入）或 `SELL`（卖出） |
| `quantity` | float | 交易股数/合约数 |
| `trade_price` | float | 每单位执行价格 |
| `trade_money` | float | 交易总价值 |
| `proceeds` | float | 现金收益（买入时为负值） |
| `taxes` | float | 交易税费 |
| `ib_commission` | float | IBKR 佣金（始终为负值） |
| `net_cash` | float | 含费用的净现金影响 |
| `fifo_pnl_realized` | float | FIFO 已实现盈亏（买入时为 null） |
| `exchange` | string | 交易执行的交易所 |
| `order_type` | string | 订单类型（`LMT`、`MKT`、`STP` 等） |

### 订单类型

| 代码 | 说明 |
|------|------|
| `LMT` | 限价单 |
| `MKT` | 市价单 |
| `STP` | 止损单 |
| `STP LMT` | 止损限价单 |
| `TRAIL` | 移动止损 |

---

## 获取交易摘要

获取与列表端点相同筛选条件下的汇总交易统计。

### 请求

```
GET /api/trades/summary
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start_date` | string | - | 起始日期 |
| `end_date` | string | - | 结束日期 |
| `symbol` | string | - | 按标的筛选 |
| `asset_class` | string | - | 按资产类别筛选 |
| `buy_sell` | string | - | 按方向筛选 |

### 示例

```bash
# 2024 年 1 月所有交易的摘要
curl "http://localhost:8000/api/trades/summary?start_date=2024-01-01&end_date=2024-01-31"

# 特定标的的摘要
curl "http://localhost:8000/api/trades/summary?symbol=AAPL"

# 仅卖出交易的摘要
curl "http://localhost:8000/api/trades/summary?buy_sell=SELL"
```

### 响应

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

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `trade_count` | int | 交易总数 |
| `buy_count` | int | 买入交易数 |
| `sell_count` | int | 卖出交易数 |
| `total_commission` | float | 总佣金（负值） |
| `total_realized_pnl` | float | 总已实现盈亏 |
| `total_proceeds` | float | 总现金收益 |
| `symbols_count` | int | 交易的不同标的数量 |

---

## 错误处理

| 状态码 | 响应体 | 原因 |
|--------|--------|------|
| `401` | `{"detail":"Not authenticated"}` | 会话缺失或已过期 |
| `422` | `{"detail":"Invalid date format: ..."}` | 日期参数无效 |
| `500` | `{"detail":"Internal server error"}` | 服务器内部错误 |
