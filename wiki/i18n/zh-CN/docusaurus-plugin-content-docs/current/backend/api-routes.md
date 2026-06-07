---
sidebar_position: 2
title: API 路由
description: 所有后端 REST 端点的完整列表。
---

# API 路由

所有路由以 `/api` 为前缀并返回 JSON。大多数端点需要认证（除非 `AUTH_PASSWORD` 为空）。

:::tip
探索所有端点最简单的方式是交互式 Swagger UI (`http://localhost:8000/docs`)。您可以直接从浏览器测试每个端点，无需编写任何代码。
:::

## 健康检查

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/health` | 健康检查。返回 `{ "status": "ok" }`。 |

```bash
# 示例：检查后端健康状态
curl http://localhost:8000/api/health
```

## 认证

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/auth/login` | 验证凭据，设置会话 cookie。 |
| `POST` | `/api/auth/logout` | 清除会话 cookie。 |
| `GET` | `/api/auth/session` | 检查当前会话状态。 |

### 示例：登录

**请求：**
```json
POST /api/auth/login
{
  "username": "admin",
  "password": "your-password"
}
```

**响应：**
```json
{
  "authenticated": true,
  "username": "admin"
}
```

响应设置一个包含 HMAC 签名令牌的 `ibkr_dash_session` httpOnly cookie。

```bash
# 示例：通过 curl 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}' \
  -c cookies.txt

# 示例：检查会话
curl http://localhost:8000/api/auth/session -b cookies.txt

# 示例：登出
curl -X POST http://localhost:8000/api/auth/logout -b cookies.txt
```

## 账户

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/account/overview` | 最新账户快照，含日环比变化。 |
| `GET` | `/api/account/snapshots` | 最近账户快照列表。查询：`limit` (1-500，默认 30)。 |

### 示例：账户概览

**响应：**
```json
{
  "account_id": "U1234567",
  "report_date": "2025-06-01",
  "currency": "USD",
  "total_equity": 125000.50,
  "cash": 15000.00,
  "stock_value": 100000.50,
  "fifo_total_realized_pnl": 5200.00,
  "fifo_total_unrealized_pnl": 3100.75,
  "total_equity_delta": {
    "amount_change": 1200.50,
    "percent_change": 0.97
  }
}
```

```bash
# 示例：获取账户概览
curl -u admin:password http://localhost:8000/api/account/overview

# 示例：获取最近 50 个快照
curl -u admin:password "http://localhost:8000/api/account/snapshots?limit=50"
```

## 持仓

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/positions` | 带过滤、排序、分页的持仓列表。 |
| `GET` | `/api/positions/summary` | 聚合持仓摘要（前 5、资产分布）。 |
| `GET` | `/api/positions/{symbol}` | 单个代码的持仓详情，含 OHLC K 线和交易标记。 |

**列表查询参数：**
- `report_date` -- 按日期过滤（默认最新）
- `symbol` -- 按代码过滤
- `asset_class` -- 按资产类别过滤
- `sort_by` -- 排序字段（默认：`position_value`）
- `sort_order` -- `asc` 或 `desc`（默认：`desc`）
- `page` / `page_size` -- 分页（默认：1/20，最大 page_size：200）
- `include_summary` -- 包含聚合摘要（默认：`false`）

```bash
# 示例：列出最新日期的所有持仓
curl -u admin:password http://localhost:8000/api/positions

# 示例：按代码过滤，按盈亏排序
curl -u admin:password "http://localhost:8000/api/positions?symbol=AAPL&sort_by=total_unrealized_pnl"

# 示例：获取 AAPL 的持仓详情
curl -u admin:password http://localhost:8000/api/positions/AAPL

# 示例：分页持仓（第 2 页，每页 10 个）
curl -u admin:password "http://localhost:8000/api/positions?page=2&page_size=10"
```

## 交易

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/trades` | 带过滤、排序、分页的交易列表。 |
| `GET` | `/api/trades/summary` | 聚合交易摘要。 |

**查询参数：**
- `start_date` / `end_date` -- 日期范围过滤
- `symbol` -- 按代码过滤
- `asset_class` -- 按资产类别过滤
- `buy_sell` -- 按方向过滤（`BUY` / `SELL`）
- `sort_by` / `sort_order` -- 排序
- `page` / `page_size` -- 分页

```bash
# 示例：列出所有交易
curl -u admin:password http://localhost:8000/api/trades

# 示例：按日期范围和代码过滤交易
curl -u admin:password "http://localhost:8000/api/trades?start_date=2025-01-01&end_date=2025-06-01&symbol=MSFT"

# 示例：获取交易摘要
curl -u admin:password http://localhost:8000/api/trades/summary
```

## 现金流

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/cash-flows` | 现金流列表（存款、取款、股息）。 |

**查询参数：** `start_date`, `end_date`, `currency`, `flow_direction`, `sort_by`, `sort_order`, `page`, `page_size`。

```bash
# 示例：列出所有现金流
curl -u admin:password http://localhost:8000/api/cash-flows

# 示例：按货币和日期范围过滤
curl -u admin:password "http://localhost:8000/api/cash-flows?currency=USD&start_date=2025-01-01"
```

## 股息

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/dividends` | 股息支付列表。 |

**查询参数：** `start_date`, `end_date`, `currency`, `symbol`, `sort_by`, `sort_order`, `page`, `page_size`。

```bash
# 示例：列出所有股息
curl -u admin:password http://localhost:8000/api/dividends

# 示例：按代码过滤股息
curl -u admin:password "http://localhost:8000/api/dividends?symbol=AAPL"
```

## 图表

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/charts/equity-curve` | 权益曲线时间序列，含净成本、盈亏、每日 MTM/TWR。 |
| `GET` | `/api/charts/performance-calendar` | 表现日历（月/年/所有年视图）。 |

**权益曲线查询参数：** `start_date`, `end_date`。

**表现日历查询参数：** `view` (`month` / `year` / `all-years`)，`anchor`（例如月视图为 `2025-06`）。

```bash
# 示例：获取 2025 年的权益曲线
curl -u admin:password "http://localhost:8000/api/charts/equity-curve?start_date=2025-01-01&end_date=2025-12-31"

# 示例：获取 2025 年 6 月的表现日历
curl -u admin:password "http://localhost:8000/api/charts/performance-calendar?view=month&anchor=2025-06"
```

## 代码

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/symbols/suggest` | 代码自动补全建议。 |

**查询参数：** `q`（必需，最少 1 字符），`limit` (1-50，默认 10)。

```bash
# 示例：搜索以 "AAP" 开头的代码
curl -u admin:password "http://localhost:8000/api/symbols/suggest?q=AAP&limit=5"
```

## Copilot（AI 聊天）

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/copilot/chat` | 向账户 Copilot 发送消息。 |
| `GET` | `/api/copilot/sessions` | 列出 Copilot 会话。 |
| `GET` | `/api/copilot/sessions/{id}/messages` | 列出会话中的消息。 |
| `DELETE` | `/api/copilot/sessions/{id}` | 删除会话及其消息。 |

### 示例：Copilot 聊天

**请求：**
```json
POST /api/copilot/chat
{
  "session_id": null,
  "message": "What is my largest position?"
}
```

**响应：**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "abc-123",
  "answer": "Your largest position is AAPL with a value of $45,000...",
  "actions": [],
  "tool_calls": [{"tool": "query_positions", "args": {"sort_by": "position_value"}}],
  "pending_approval": null,
  "errors": []
}
```

```bash
# 示例：向 Copilot 提问
curl -X POST http://localhost:8000/api/copilot/chat \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"session_id": null, "message": "What is my largest position?"}'

# 示例：继续现有会话
curl -X POST http://localhost:8000/api/copilot/chat \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"session_id": "550e8400-e29b-41d4-a716-446655440000", "message": "What about MSFT?"}'
```

## 代理任务（后台）

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/agent/run` | 在后台运行代理。返回任务 ID。 |
| `GET` | `/api/agent/tasks` | 列出任务。查询：`agent_name`, `status`, `limit`。 |
| `GET` | `/api/agent/tasks/{id}` | 按 ID 获取任务状态。 |
| `POST` | `/api/agent/tasks/{id}/cancel` | 取消运行中的任务。 |

**支持的代理：** `daily_review`, `trade_decision`, `trade_review`, `risk_assessment`。

```bash
# 示例：在后台运行每日审查
curl -X POST http://localhost:8000/api/agent/run \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "daily_review", "params": {"report_date": "2025-06-01"}}'

# 示例：检查任务状态
curl -u admin:password http://localhost:8000/api/agent/tasks/abc-123

# 示例：列出所有已完成任务
curl -u admin:password "http://localhost:8000/api/agent/tasks?status=completed&limit=10"
```

## 每日持仓审查代理

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/daily-position-review/generate` | 生成每日审查（同步）。 |
| `GET` | `/api/daily-position-review/dates` | 列出有审查的日期。 |
| `GET` | `/api/daily-position-review/reviews/{date}` | 获取特定日期的审查。 |
| `GET` | `/api/daily-position-review/health` | 代理健康检查。 |

```bash
# 示例：生成每日审查
curl -X POST http://localhost:8000/api/daily-position-review/generate \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"report_date": "2025-06-01"}'

# 示例：获取特定日期的审查
curl -u admin:password http://localhost:8000/api/daily-position-review/reviews/2025-06-01
```

## 交易决策代理

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/trade-decision/analyze` | 分析交易决策（同步）。 |
| `GET` | `/api/trade-decision/decisions` | 列出最近的决策。查询：`symbol`, `decision_type`。 |
| `GET` | `/api/trade-decision/decisions/{id}` | 按 ID 获取决策。 |
| `GET` | `/api/trade-decision/health` | 代理健康检查。 |

```bash
# 示例：分析 AAPL 的交易决策
curl -X POST http://localhost:8000/api/trade-decision/analyze \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "decision_type": "new_entry"}'
```

## 交易回顾代理

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/trade-review/review` | 触发交易回顾（同步）。 |
| `GET` | `/api/trade-review/reviews` | 列出最近的回顾。查询：`symbol`, `review_type`。 |
| `GET` | `/api/trade-review/reviews/{id}` | 按 ID 获取回顾。 |
| `GET` | `/api/trade-review/health` | 代理健康检查。 |

```bash
# 示例：回顾 MSFT 的交易
curl -X POST http://localhost:8000/api/trade-review/review \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"symbol": "MSFT", "review_type": "post_trade"}'
```

## 风险评估代理

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/risk-assessment/assess` | 触发风险评估（同步）。 |
| `GET` | `/api/risk-assessment/assessments` | 列出最近的评估。 |
| `GET` | `/api/risk-assessment/assessments/{id}` | 按 ID 获取评估。 |
| `GET` | `/api/risk-assessment/health` | 代理健康检查。 |

```bash
# 示例：运行风险评估
curl -X POST http://localhost:8000/api/risk-assessment/assess \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 管理

### 系统状态

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/admin/system/status` | 系统健康、数据库状态、记录计数、运行时信息。 |

```bash
# 示例：检查系统状态
curl -u admin:password http://localhost:8000/api/admin/system/status
```

### 提示词管理

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/admin/prompts` | 列出所有提示词版本。查询：`prompt_key`。 |
| `POST` | `/api/admin/prompts` | 创建新的提示词版本。 |
| `GET` | `/api/admin/prompts/{key}/active` | 获取提示词的活跃版本。 |

```bash
# 示例：列出所有提示词
curl -u admin:password http://localhost:8000/api/admin/prompts

# 示例：获取每日审查的活跃提示词
curl -u admin:password http://localhost:8000/api/admin/prompts/daily_review/active
```

### LLM 管理

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/admin/llm/providers` | 列出已配置的 LLM 提供商。 |
| `POST` | `/api/admin/llm/providers` | 注册新的 LLM 提供商（当前后端中为空操作）。 |
| `POST` | `/api/admin/llm/test` | 用简单提示测试 LLM 连接。 |
| `GET` | `/api/admin/llm/health` | 检查 LLM 配置健康状态。 |

```bash
# 示例：测试 LLM 连接
curl -X POST http://localhost:8000/api/admin/llm/test \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello"}'
```

### IBKR 设置

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/admin/ibkr/settings` | 获取 IBKR 连接设置。 |
| `PUT` | `/api/admin/ibkr/settings` | 更新 IBKR 设置。 |
| `POST` | `/api/admin/ibkr/test` | 测试 IBKR 连接。 |

### 邮件设置

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/admin/email/settings` | 获取邮件配置。 |
| `PUT` | `/api/admin/email/settings` | 更新邮件配置。 |
| `POST` | `/api/admin/email/test` | 发送测试邮件。 |

## 路由如何使用 DI

每个受保护路由都包含 `_user: str | None = Depends(get_current_user)`。此依赖：

1. 检查是否配置了 `auth_password`。如果没有，允许匿名访问。
2. 查找 `ibkr_dash_session` cookie 并验证 HMAC 签名。
3. 回退到 HTTP Basic 认证凭据。
4. 如果未找到有效凭据，抛出 `401 Unauthorized`。

调用 LLM 的端点还包含 `_rate: None = Depends(check_llm_rate_limit)`，它对每个客户端 IP 强制执行每 60 秒 20 个请求的滑动窗口速率限制。

:::info
管理端点没有单独保护。它们共享相同的 `get_current_user` 依赖。如果 `AUTH_PASSWORD` 为空，所有端点都公开可访问。
:::

:::warning
使用 curl 进行认证时，您可以使用 HTTP Basic 认证 (`-u admin:password`) 或包含会话 cookie (`-b cookies.txt`)。Basic 认证更简单用于测试，但对生产使用不太安全。
:::
