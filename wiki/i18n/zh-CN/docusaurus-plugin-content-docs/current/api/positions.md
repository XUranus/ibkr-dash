---
sidebar_position: 2
title: 持仓 API
---

# 持仓 API

持仓 API 让您查看当前投资组合持仓、获取汇总摘要，并深入查看单个标的。所有端点返回的数据来自已导入数据库的最新 IBKR Flex 报告。

---

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/positions` | 列出所有持仓（支持分页和筛选） |
| GET | `/api/positions/summary` | 获取投资组合汇总摘要 |
| GET | `/api/positions/{symbol}` | 获取单个标的的详细历史 |

所有端点在 `AUTH_PASSWORD` 非空时需要身份验证。

---

## 列出持仓

获取带可选筛选和排序的分页持仓列表。

### 请求

```
GET /api/positions
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `report_date` | string | 最新 | 按报告日期筛选（格式：`YYYY-MM-DD`） |
| `symbol` | string | - | 按股票代码筛选（如 `AAPL`） |
| `asset_class` | string | - | 按资产类别筛选（如 `STK`、`OPT`） |
| `include_summary` | bool | `false` | 在响应中包含摘要数据 |
| `sort_by` | string | `position_value` | 排序字段：`position_value`、`symbol`、`quantity`、`mark_price` |
| `sort_order` | string | `desc` | 排序方向：`asc` 或 `desc` |
| `page` | int | `1` | 页码（从 1 开始） |
| `page_size` | int | `20` | 每页条目数（1-200） |

### 筛选示例

```bash
# 获取按价值排序的前 10 个持仓
curl "http://localhost:8000/api/positions?page=1&page_size=10&sort_by=position_value&sort_order=desc"

# 按标的筛选
curl "http://localhost:8000/api/positions?symbol=AAPL"

# 按资产类别筛选（仅股票）
curl "http://localhost:8000/api/positions?asset_class=STK"

# 按数量排序的期权持仓
curl "http://localhost:8000/api/positions?asset_class=OPT&sort_by=quantity&sort_order=desc"

# 获取特定日期的持仓
curl "http://localhost:8000/api/positions?report_date=2024-01-15&page_size=50"

# 组合多个筛选条件
curl "http://localhost:8000/api/positions?asset_class=STK&sort_by=symbol&sort_order=asc&page=1&page_size=100"
```

### 响应

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

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | IBKR 账户标识符 |
| `report_date` | string | 快照日期 |
| `symbol` | string | 股票代码 |
| `description` | string | 完整公司/资产名称 |
| `asset_class` | string | 资产类别代码（`STK`、`OPT`、`FUND` 等） |
| `quantity` | float | 股数/合约数 |
| `mark_price` | float | 当前市场价格 |
| `position_value` | float | 总市值（数量 x 标记价格） |
| `percent_of_nav` | float | 占净资产值的百分比 |
| `average_cost_price` | float | 平均买入价格 |
| `cost_basis_money` | float | 总成本基础 |
| `total_realized_pnl` | float | 已实现盈亏 |
| `total_unrealized_pnl` | float | 未实现盈亏 |
| `previous_day_change_percent` | float | 日涨跌百分比 |

### 资产类别代码

| 代码 | 说明 |
|------|------|
| `STK` | 股票 / ETF |
| `OPT` | 期权 |
| `FUND` | 共同基金 |
| `CRYPTO` | 加密货币 |
| `BOND` | 债券 |
| `WAR` | 权证 |

---

## 获取持仓摘要

获取投资组合的汇总视图，包括主要持仓和资产分布。

### 请求

```
GET /api/positions/summary
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `report_date` | string | 最新 | 按报告日期筛选 |
| `symbol` | string | - | 按标的筛选 |
| `asset_class` | string | - | 按资产类别筛选 |

### 示例

```bash
curl "http://localhost:8000/api/positions/summary"
```

### 响应

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

## 获取持仓详情

获取单个标的的详细历史，包括价格 K 线和交易标记。

### 请求

```
GET /api/positions/{symbol}
```

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码（如 `AAPL`） |

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `asset_class` | string | - | 当同一标的存在于多个资产类别时用于区分 |

### 示例

```bash
curl "http://localhost:8000/api/positions/AAPL"
```

### 响应

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

### 响应字段

**bars** -- 用于图表展示的历史价格数据：

| 字段 | 类型 | 说明 |
|------|------|------|
| `report_date` | string | 快照日期 |
| `open_price` | float | 开盘价 |
| `high_price` | float | 最高价 |
| `low_price` | float | 最低价 |
| `close_price` | float | 收盘价 |
| `quantity` | float | 当日持有股数 |

**trades** -- 叠加在图表上的交易事件：

| 字段 | 类型 | 说明 |
|------|------|------|
| `trade_date` | string | 交易日期 |
| `buy_sell` | string | `BUY`（买入）或 `SELL`（卖出） |
| `quantity` | float | 交易股数 |
| `trade_price` | float | 执行价格 |
| `fifo_pnl_realized` | float | 已实现盈亏（未平仓持仓为 null） |

---

## 错误处理

| 状态码 | 响应体 | 原因 |
|--------|--------|------|
| `401` | `{"detail":"Not authenticated"}` | 会话缺失或已过期 |
| `422` | `{"detail":"Invalid date format: ..."}` | 查询参数值无效 |
| `500` | `{"detail":"Internal server error"}` | 服务器内部错误 |
