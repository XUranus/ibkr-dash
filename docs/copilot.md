# Account Copilot

The Account Copilot is an AI-powered conversational assistant integrated into IBKR Dash. It allows you to ask natural-language questions about your portfolio, trades, and account performance.

## Features

- **Natural Language Queries**: Ask questions like "What is my total PnL this month?" or "Which positions have the highest unrealized loss?"
- **Context Awareness**: The copilot understands your account data, positions, trades, and cash flows.
- **Session Memory**: Conversations persist within sessions, allowing follow-up questions.
- **Structured Responses**: Returns data-backed answers with references to specific records.

## How It Works

1. You type a question in the Copilot chat panel.
2. The backend retrieves relevant account data (snapshots, positions, trades, cash flows).
3. The data is formatted into a context prompt and sent to the configured LLM.
4. The LLM generates a response grounded in your actual portfolio data.
5. The response is displayed in the chat with optional data citations.

## Configuration

The Copilot requires an LLM provider to be configured in the backend:

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
```

Any OpenAI-compatible API endpoint can be used (OpenAI, Azure OpenAI, local models via Ollama, etc.).

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/copilot/sessions` | POST | Create a new conversation session |
| `/api/copilot/sessions/{id}/messages` | POST | Send a message and get a response |
| `/api/copilot/sessions/{id}/messages` | GET | Retrieve conversation history |
| `/api/copilot/sessions` | GET | List all sessions |

## Data Privacy

- All data stays in your local SQLite database.
- Only the context needed to answer your question is sent to the LLM provider.
- No portfolio data is stored by the LLM provider.
- Sessions and messages are stored locally and can be deleted at any time.

## Limitations

- The copilot can only access data that has been imported into the system.
- Complex analytical queries may require multiple turns of conversation.
- The quality of responses depends on the configured LLM model.
- Real-time market data is not available unless separately configured.
