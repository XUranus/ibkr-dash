---
sidebar_position: 7
title: 管理 API
---

# 管理 API

管理 API 提供系统监控、配置管理和集成测试的端点。使用这些端点检查系统健康状态、管理 LLM 和 IBKR 设置、配置邮件以及管理代理提示词。

---

## 系统状态

获取系统健康状态和配置的全面概览。

### 请求

```
GET /api/admin/system/status
```

### 示例

```bash
curl "http://localhost:8000/api/admin/system/status"
```

### 响应

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": {
    "healthy": true,
    "path": "data/ibkr_dash.db",
    "record_counts": {
      "account_snapshots": 365,
      "position_snapshots": 5000,
      "trade_records": 1200,
      "agent_tasks": 50
    }
  },
  "llm": {
    "configured": true,
    "model": "gpt-4o",
    "base_url": "https://api.openai.com/v1"
  },
  "longbridge": {
    "configured": false
  },
  "runtime": {
    "python_version": "3.12.0",
    "platform": "Linux-6.1.0-x86_64",
    "app_env": "development"
  }
}
```

:::tip
当数据库健康时，`status` 字段为 `"ok"`；如果数据库连接失败则为 `"degraded"`。使用此端点进行健康监控和告警。
:::

---

## LLM 管理

管理所有 AI 代理和 Copilot 使用的 LLM 提供商配置。

### 列出提供商

```
GET /api/admin/llm/providers
```

```bash
curl "http://localhost:8000/api/admin/llm/providers"
```

返回活动的 LLM 配置（API 密钥已脱敏）：

```json
[
  {
    "name": "default",
    "base_url": "https://api.openai.com/v1",
    "api_key_masked": "sk-a****xyz",
    "default_model": "gpt-4o",
    "temperature": 0.1,
    "max_tokens": 8192,
    "is_active": true
  }
]
```

### 测试 LLM 连接

```
POST /api/admin/llm/test
```

发送测试消息以验证 LLM 连接是否正常。

```bash
curl -X POST "http://localhost:8000/api/admin/llm/test" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, are you working?"}'
```

**响应（成功）：**

```json
{
  "success": true,
  "model": "gpt-4o",
  "content": "Yes",
  "latency_ms": 850
}
```

**响应（失败）：**

```json
{
  "success": false,
  "error": "auth_error: Invalid API key"
}
```

### LLM 健康检查

```
GET /api/admin/llm/health
```

```bash
curl "http://localhost:8000/api/admin/llm/health"
```

```json
{
  "configured": true,
  "base_url": "https://api.openai.com/v1",
  "default_model": "gpt-4o",
  "status": "ok",
  "message": "LLM is configured and ready"
}
```

---

## IBKR 设置

查看和更新 IBKR Flex Web Service 连接设置。

### 获取设置

```
GET /api/admin/ibkr/settings
```

```bash
curl "http://localhost:8000/api/admin/ibkr/settings"
```

```json
{
  "flex_token": "your-flex-token",
  "flex_query_id": "123456",
  "account_id": "U1234567"
}
```

### 更新设置

```
PUT /api/admin/ibkr/settings
```

```bash
curl -X PUT "http://localhost:8000/api/admin/ibkr/settings" \
  -H "Content-Type: application/json" \
  -d '{"flex_token": "new-token", "flex_query_id": "789012"}'
```

只包含要更新的字段。省略的字段保持不变。

### 测试连接

```
POST /api/admin/ibkr/test
```

```bash
curl -X POST "http://localhost:8000/api/admin/ibkr/test"
```

**响应：**

```json
{
  "success": true,
  "message": "IBKR connection is active. Latest data from: 2024-01-15",
  "account_id": null
}
```

---

## 邮件设置

配置用于每日快照报告和通知的 SMTP 邮件。

### 获取设置

```
GET /api/admin/email/settings
```

```bash
curl "http://localhost:8000/api/admin/email/settings"
```

```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_username": "user@gmail.com",
  "smtp_password_set": true,
  "from_address": "user@gmail.com",
  "to_addresses": ["recipient@example.com"],
  "enabled": true
}
```

注意：`smtp_password_set` 是布尔值 -- 实际密码永远不会返回。

### 更新设置

```
PUT /api/admin/email/settings
```

```bash
curl -X PUT "http://localhost:8000/api/admin/email/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "user@gmail.com",
    "smtp_password": "app-specific-password",
    "from_address": "user@gmail.com",
    "to_addresses": ["recipient@example.com"],
    "enabled": true
  }'
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `smtp_host` | string | SMTP 服务器主机名 |
| `smtp_port` | int | SMTP 端口（TLS 通常为 587） |
| `smtp_username` | string | SMTP 登录用户名 |
| `smtp_password` | string | SMTP 登录密码 |
| `from_address` | string | 发件人邮箱地址 |
| `to_addresses` | list[string] | 收件人邮箱地址列表 |
| `enabled` | bool | 启用/禁用邮件发送 |

### 测试邮件

```
POST /api/admin/email/test
```

发送测试邮件以验证 SMTP 配置。

```bash
curl -X POST "http://localhost:8000/api/admin/email/test"
```

**响应（成功）：**

```json
{
  "success": true,
  "message": "Test email sent successfully to recipient@example.com"
}
```

**响应（失败）：**

```json
{
  "success": false,
  "message": "SMTP authentication failed. Please check your username and password."
}
```

---

## 提示词管理

管理 AI 代理使用的版本化提示词。每个提示词有一个键、版本号和内容。

### 列出提示词

```
GET /api/admin/prompts
```

```bash
# 所有提示词
curl "http://localhost:8000/api/admin/prompts"

# 按键筛选
curl "http://localhost:8000/api/admin/prompts?prompt_key=trade_decision"
```

```json
[
  {
    "id": 1,
    "prompt_key": "trade_decision",
    "version": 3,
    "content": "You are a trade decision analyst...",
    "status": "active",
    "created_at": "2024-01-15T10:00:00"
  }
]
```

### 创建新提示词版本

```
POST /api/admin/prompts
```

```bash
curl -X POST "http://localhost:8000/api/admin/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_key": "trade_decision",
    "content": "You are a trade decision analyst. Analyze the given data...",
    "status": "active"
  }'
```

版本号自动递增。新提示词成为其键的活动版本。

### 获取活动提示词

```
GET /api/admin/prompts/{prompt_key}/active
```

```bash
curl "http://localhost:8000/api/admin/prompts/trade_decision/active"
```

返回提示词的活动（最新）版本。

---

## 端点汇总

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/system/status` | 系统健康状态和统计 |
| GET | `/api/admin/llm/providers` | 列出 LLM 提供商 |
| POST | `/api/admin/llm/test` | 测试 LLM 连接 |
| GET | `/api/admin/llm/health` | LLM 健康检查 |
| GET | `/api/admin/ibkr/settings` | 获取 IBKR 设置 |
| PUT | `/api/admin/ibkr/settings` | 更新 IBKR 设置 |
| POST | `/api/admin/ibkr/test` | 测试 IBKR 连接 |
| GET | `/api/admin/email/settings` | 获取邮件设置 |
| PUT | `/api/admin/email/settings` | 更新邮件设置 |
| POST | `/api/admin/email/test` | 发送测试邮件 |
| GET | `/api/admin/prompts` | 列出所有提示词 |
| POST | `/api/admin/prompts` | 创建提示词版本 |
| GET | `/api/admin/prompts/{key}/active` | 获取活动提示词 |

---

## 错误处理

| 状态码 | 响应体 | 原因 |
|--------|--------|------|
| `401` | `{"detail":"Not authenticated"}` | 会话缺失或已过期 |
| `404` | `{"detail":"No active prompt found"}` | 提示词键未找到 |
| `422` | `{"detail":"field required"}` | 缺少必需字段 |
| `500` | `{"detail":"Internal server error"}` | 服务器内部错误 |
