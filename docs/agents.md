# AI Agents

IBKR Dash includes a suite of AI-powered agents that automatically analyze your portfolio data and generate actionable insights.

## Available Agents

### Daily Position Review

Analyzes all current positions at the end of each trading day. The agent:

- Reviews each position's PnL, cost basis, and market performance
- Identifies positions with significant gains or losses
- Compares current prices to entry prices and recent trends
- Generates a summary report with key observations
- Highlights positions that may need attention

**Trigger**: Automatically after daily data import, or manually via the API.

### Trade Review

Analyzes individual trades or groups of trades. The agent:

- Evaluates trade entry and exit timing
- Compares trade outcomes to market movements
- Identifies patterns in winning vs. losing trades
- Provides feedback on trade execution quality

**Trigger**: On-demand via the API.

### Risk Assessment

Evaluates portfolio-level risk metrics. The agent:

- Analyzes concentration risk (position sizes relative to total equity)
- Reviews sector and asset class diversification
- Identifies correlation risks between positions
- Suggests rebalancing considerations

**Trigger**: On-demand via the API.

## Architecture

All agents follow a consistent pattern:

1. **Task Creation**: A task record is created in the `agent_tasks` table with status `pending`.
2. **Data Gathering**: The agent queries the SQLite database for relevant data (snapshots, positions, trades).
3. **Prompt Construction**: The data is formatted into a structured prompt for the LLM.
4. **LLM Invocation**: The prompt is sent to the configured LLM provider.
5. **Result Storage**: The LLM response is parsed and stored in the appropriate table (`daily_position_reviews`, `trade_reviews`, `risk_assessments`).
6. **Task Completion**: The task status is updated to `completed` (or `failed` on error).

## Task Status Lifecycle

```
pending -> running -> completed
                   -> failed
         -> cancelled
```

- **pending**: Task created, waiting to be picked up.
- **running**: Task is actively processing.
- **completed**: Task finished successfully with results.
- **failed**: Task encountered an error.
- **cancelled**: Task was cancelled before completion.

## Configuration

Agents use the same LLM configuration as the Account Copilot:

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o
```

Internal token for triggering agents from the worker:

```env
DAILY_REVIEW_INTERNAL_TOKEN=your-internal-token
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/agent/tasks` | GET | List agent tasks |
| `/api/agent/tasks/{id}` | GET | Get task details |
| `/api/agent/daily-position-review` | GET | List daily reviews |
| `/api/agent/daily-position-review/{id}` | GET | Get specific review |
| `/api/agent/daily-position-review/internal/latest/tasks` | POST | Trigger latest review |
| `/api/agent/trade-reviews` | GET | List trade reviews |
| `/api/agent/risk-assessments` | GET | List risk assessments |

## Prompt Management

Agent prompts are versioned and stored in the `agent_prompts` table. This allows:

- Iterating on prompt quality without code changes
- A/B testing different prompt strategies
- Rolling back to previous prompt versions
- Activating/deactivating specific prompts

## Extending Agents

To add a new agent:

1. Create a new prompt in the `agent_prompts` table.
2. Implement a service class that gathers the required data.
3. Add an API route to trigger and query the agent.
4. Store results in a dedicated table or reuse existing ones.
