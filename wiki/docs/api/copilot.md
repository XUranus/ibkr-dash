---
sidebar_position: 5
title: Copilot API
---

# Copilot API

The Copilot is an AI chat assistant that can answer questions about your portfolio. It uses a ReAct (Reason + Act) loop with access to portfolio data tools. You can ask questions like "What are my top holdings?" or "How did AAPL perform this month?"

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/copilot/chat` | Send a message and get a response |
| GET | `/api/copilot/sessions` | List all chat sessions |
| GET | `/api/copilot/sessions/{session_id}/messages` | Get messages in a session |
| DELETE | `/api/copilot/sessions/{session_id}` | Delete a session and its messages |

All endpoints require authentication (unless `AUTH_PASSWORD` is empty). The chat endpoint is rate-limited (20 requests per 60 seconds per IP).

---

## Send a Message

Send a message to the copilot and receive an AI-generated response. If no `session_id` is provided, a new session is created automatically.

### Request

```
POST /api/copilot/chat
```

### Request Body

```json
{
  "session_id": null,
  "message": "What are my top 5 holdings by value?"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | No | Existing session ID. Omit to create a new session. |
| `message` | string | Yes | Your question (1-10,000 characters) |

### Examples

```bash
# Start a new conversation
curl -X POST "http://localhost:8000/api/copilot/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top holdings?"}'

# Continue an existing session
curl -X POST "http://localhost:8000/api/copilot/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "message": "What about AAPL specifically?"}'
```

### Response

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "run_id": "run-xyz-789",
  "answer": "Your top 5 holdings by value are:\n1. AAPL - $18,550 (7.4% of NAV)\n2. MSFT - $15,200 (6.1% of NAV)\n...",
  "actions": [
    {"tool": "get_positions", "args": {"sort_by": "position_value", "limit": 5}}
  ],
  "tool_calls": [
    {"name": "get_positions", "status": "success"}
  ],
  "pending_approval": null,
  "errors": []
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Session ID for continuing the conversation |
| `run_id` | string | Unique ID for this specific run |
| `answer` | string | The copilot's response (Markdown formatted) |
| `actions` | list | Tools the copilot invoked during reasoning |
| `tool_calls` | list | Detailed tool call results |
| `pending_approval` | object | If set, the copilot needs user confirmation before acting |
| `errors` | list | Any errors encountered during the run |

### How It Works

The copilot uses a **ReAct loop** (up to 12 rounds):

1. You send a message.
2. The LLM reasons about your question and decides which tools to call.
3. Tools fetch data from the database (positions, trades, etc.).
4. The LLM uses tool results to generate a final answer.
5. The conversation is saved for context in future messages.

The copilot automatically truncates history to the last 20 messages to stay within LLM context limits.

---

## List Sessions

Get a list of all copilot sessions with message counts.

### Request

```
GET /api/copilot/sessions
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | `20` | Maximum number of sessions to return |

### Example

```bash
curl "http://localhost:8000/api/copilot/sessions?limit=10"
```

### Response

```json
[
  {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "What are my top holdings?...",
    "created_at": "2024-01-15T10:30:00",
    "message_count": 6
  },
  {
    "session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "title": "How is my portfolio performing...",
    "created_at": "2024-01-14T15:00:00",
    "message_count": 4
  }
]
```

---

## Get Session Messages

Retrieve all messages in a specific session.

### Request

```
GET /api/copilot/sessions/{session_id}/messages
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | The session ID |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | `100` | Maximum messages to return |

### Example

```bash
curl "http://localhost:8000/api/copilot/sessions/a1b2c3d4/messages"
```

### Response

```json
[
  {
    "id": 1,
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "role": "user",
    "content": "What are my top holdings?",
    "metadata": null,
    "created_at": "2024-01-15T10:30:00"
  },
  {
    "id": 2,
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "role": "assistant",
    "content": "Your top holdings are...",
    "metadata": {
      "run_id": "run-xyz-789",
      "actions_count": 1,
      "tool_calls_count": 1
    },
    "created_at": "2024-01-15T10:30:05"
  }
]
```

---

## Delete Session

Delete a session and all its messages.

### Request

```
DELETE /api/copilot/sessions/{session_id}
```

### Example

```bash
curl -X DELETE "http://localhost:8000/api/copilot/sessions/a1b2c3d4"
```

### Response

Returns HTTP `204 No Content` on success.

---

## Error Handling

| Status | Body | Cause |
|--------|------|-------|
| `401` | `{"detail":"Not authenticated"}` | Missing or expired session |
| `404` | `{"detail":"Session abc not found"}` | Session ID does not exist |
| `422` | `{"detail":"field required"}` | Empty message |
| `429` | `{"detail":"Rate limit exceeded..."}` | Too many requests |
| `500` | `{"detail":"Internal server error"}` | LLM or runtime error |
