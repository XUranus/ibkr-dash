---
sidebar_position: 7
title: Admin API
---

# Admin API

The Admin API provides endpoints for system monitoring, configuration management, and testing integrations. Use these endpoints to check system health, manage LLM and IBKR settings, configure email, and manage agent prompts.

---

## System Status

Get a comprehensive overview of the system's health and configuration.

### Request

```
GET /api/admin/system/status
```

### Example

```bash
curl "http://localhost:8000/api/admin/system/status"
```

### Response

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
The `status` field is `"ok"` when the database is healthy, or `"degraded"` if the DB connection fails. Use this endpoint for health monitoring and alerting.
:::

---

## LLM Management

Manage the LLM provider configuration used by all AI agents and the copilot.

### List Providers

```
GET /api/admin/llm/providers
```

```bash
curl "http://localhost:8000/api/admin/llm/providers"
```

Returns the active LLM configuration (API key is masked):

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

### Test LLM Connection

```
POST /api/admin/llm/test
```

Send a test message to verify the LLM connection works.

```bash
curl -X POST "http://localhost:8000/api/admin/llm/test" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, are you working?"}'
```

**Response (success):**

```json
{
  "success": true,
  "model": "gpt-4o",
  "content": "Yes",
  "latency_ms": 850
}
```

**Response (failure):**

```json
{
  "success": false,
  "error": "auth_error: Invalid API key"
}
```

### LLM Health Check

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

## IBKR Settings

View and update IBKR Flex Web Service connection settings.

### Get Settings

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

### Update Settings

```
PUT /api/admin/ibkr/settings
```

```bash
curl -X PUT "http://localhost:8000/api/admin/ibkr/settings" \
  -H "Content-Type: application/json" \
  -d '{"flex_token": "new-token", "flex_query_id": "789012"}'
```

Only include fields you want to update. Omitted fields are left unchanged.

### Test Connection

```
POST /api/admin/ibkr/test
```

```bash
curl -X POST "http://localhost:8000/api/admin/ibkr/test"
```

**Response:**

```json
{
  "success": true,
  "message": "IBKR connection is active. Latest data from: 2024-01-15",
  "account_id": null
}
```

---

## Email Settings

Configure SMTP email for daily snapshot reports and notifications.

### Get Settings

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

Note: `smtp_password_set` is a boolean -- the actual password is never returned.

### Update Settings

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

| Field | Type | Description |
|-------|------|-------------|
| `smtp_host` | string | SMTP server hostname |
| `smtp_port` | int | SMTP port (usually 587 for TLS) |
| `smtp_username` | string | SMTP login username |
| `smtp_password` | string | SMTP login password |
| `from_address` | string | Sender email address |
| `to_addresses` | list[string] | Recipient email addresses |
| `enabled` | bool | Enable/disable email sending |

### Test Email

```
POST /api/admin/email/test
```

Send a test email to verify SMTP configuration.

```bash
curl -X POST "http://localhost:8000/api/admin/email/test"
```

**Response (success):**

```json
{
  "success": true,
  "message": "Test email sent successfully to recipient@example.com"
}
```

**Response (failure):**

```json
{
  "success": false,
  "message": "SMTP authentication failed. Please check your username and password."
}
```

---

## Prompt Management

Manage versioned prompts used by AI agents. Each prompt has a key, version number, and content.

### List Prompts

```
GET /api/admin/prompts
```

```bash
# All prompts
curl "http://localhost:8000/api/admin/prompts"

# Filter by key
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

### Create a New Prompt Version

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

The version number is auto-incremented. The new prompt becomes the active version for its key.

### Get Active Prompt

```
GET /api/admin/prompts/{prompt_key}/active
```

```bash
curl "http://localhost:8000/api/admin/prompts/trade_decision/active"
```

Returns the active (latest) version of a prompt.

---

## Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/system/status` | System health and stats |
| GET | `/api/admin/llm/providers` | List LLM providers |
| POST | `/api/admin/llm/test` | Test LLM connection |
| GET | `/api/admin/llm/health` | LLM health check |
| GET | `/api/admin/ibkr/settings` | Get IBKR settings |
| PUT | `/api/admin/ibkr/settings` | Update IBKR settings |
| POST | `/api/admin/ibkr/test` | Test IBKR connection |
| GET | `/api/admin/email/settings` | Get email settings |
| PUT | `/api/admin/email/settings` | Update email settings |
| POST | `/api/admin/email/test` | Send test email |
| GET | `/api/admin/prompts` | List all prompts |
| POST | `/api/admin/prompts` | Create prompt version |
| GET | `/api/admin/prompts/{key}/active` | Get active prompt |

---

## Error Handling

| Status | Body | Cause |
|--------|------|-------|
| `401` | `{"detail":"Not authenticated"}` | Missing or expired session |
| `404` | `{"detail":"No active prompt found"}` | Prompt key not found |
| `422` | `{"detail":"field required"}` | Missing required field |
| `500` | `{"detail":"Internal server error"}` | Unexpected error |
