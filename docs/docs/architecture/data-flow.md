---
sidebar_position: 4
title: Data Flow
---

# Data Flow

This document traces data as it moves through IBKR Dash -- from IBKR's servers to your screen. Every major flow is illustrated with sequence diagrams so you can understand exactly what happens at each step.

---

## Overview

There are two main data flows in IBKR Dash:

1. **Financial Data Flow** -- IBKR Flex API -> Worker -> SQLite -> Backend -> Frontend
2. **AI Agent Flow** -- User -> Frontend -> Backend -> LLM -> Response

```mermaid
graph LR
    subgraph Flow1 ["Financial Data Flow"]
        IBKR["IBKR Flex API"] --> Worker["Worker"]
        Worker --> SQLite["SQLite"]
        SQLite --> Backend["Backend API"]
        Backend --> Frontend["Frontend"]
        Frontend --> User["User"]
    end

    subgraph Flow2 ["AI Agent Flow"]
        User2["User"] --> FE["Frontend"]
        FE --> BE["Backend"]
        BE --> LLM["LLM Provider"]
        LLM --> BE
        BE --> FE
        FE --> User2
    end
```

---

## Financial Data Flow

This is the core data pipeline that brings your IBKR portfolio data into the dashboard.

### Step 1: Data Extraction from IBKR

There are two ways to get data from IBKR:

#### Option A: Manual Flex CSV Export

You manually export a CSV from IBKR's web interface:

1. Log in to IBKR Account Management
2. Navigate to Reports > Flex Queries
3. Run a Flex Query (daily snapshot)
4. Download the CSV file
5. Place it in `data/flex_exports/`

#### Option B: Automatic Flex Web Service Pull

The worker automatically pulls data using IBKR's Flex Web Service API:

```mermaid
sequenceDiagram
    participant Scheduler as Worker Scheduler
    participant FlexClient as Flex Client
    participant IBKR as IBKR Flex API
    participant Disk as File System

    Scheduler->>Scheduler: Cron trigger (12:30 daily)
    Scheduler->>FlexClient: run_daily_incremental_job()
    FlexClient->>IBKR: SendRequest (query_id, token)
    IBKR-->>FlexClient: ReferenceCode

    loop Poll until ready
        FlexClient->>IBKR: GetStatement (reference_code)
        IBKR-->>FlexClient: "Not Ready" (code 1018/1019)
        FlexClient->>FlexClient: Sleep(poll_interval)
    end

    FlexClient->>IBKR: GetStatement (reference_code)
    IBKR-->>FlexClient: FlexQueryResponse (XML)
    FlexClient->>Disk: Save statement file
```

The Flex Client (`worker/clients/flex_client.py`) handles:

- **Sending** the query request with your token and query ID
- **Polling** until the statement is ready (IBKR generates reports asynchronously)
- **Downloading** the final statement (XML or CSV format)
- **Retrying** up to 60 times with 10-second intervals

:::info
IBKR Flex queries are not instant. After submitting a query, IBKR takes 10-60 seconds to generate the report. The worker polls every 10 seconds until the report is ready.
:::

---

### Step 2: CSV Parsing

The IBKR Flex CSV format is a multi-section format with record type markers. The parser (`worker/parsers/flex_csv_parser.py`) reads each row and categorizes it:

```mermaid
flowchart TD
    Input["Raw CSV File"] --> ReadLine["Read Line"]
    ReadLine --> CheckType{"Record Type?"}

    CheckType -->|"BOF"| ExtractMeta["Extract File Metadata<br/>(AccountId, QueryName, Dates)"]
    CheckType -->|"BOA"| ExtractAccount["Extract Account Metadata<br/>(Key-Value Pairs)"]
    CheckType -->|"BOS"| StartSection["Start New Section<br/>(ACCT, POST, TRNT, etc.)"]
    CheckType -->|"HEADER"| SetHeaders["Set Column Headers<br/>for Current Section"]
    CheckType -->|"DATA"| AddRow["Add Data Row<br/>to Current Section"]
    CheckType -->|"EOS"| EndSection["End Current Section"]
    CheckType -->|"EOF"| Done["Parsing Complete"]

    ExtractMeta --> ReadLine
    ExtractAccount --> ReadLine
    StartSection --> ReadLine
    SetHeaders --> ReadLine
    AddRow --> ReadLine
    EndSection --> ReadLine

    Done --> Output["FlexStatement Object"]
```

The CSV contains several sections:

| Section | Description | Maps To |
|---------|-------------|---------|
| `ACCT` | Account information | `account_snapshots` |
| `POST` | Position data | `position_snapshots` |
| `TRNT` | Trade transactions | `trade_records` |
| `CTRN` | Cash transactions | `cash_flows` |
| `FIFO` | FIFO P&L data | Merged into positions |
| `SECU` | Security details | Merged into positions |
| `PPPO` | Price data | `price_history` |

Example of the raw CSV structure:

```csv
BOF,DU123456,Daily_Snapshot,2024-01-01,2024-01-15
BOA,AccountId,DU123456,AccountType,Individual
BOS,ACCT
HEADER,AccountId,Currency,TotalEquity,Cash
DATA,DU123456,USD,150000.00,25000.00
EOS
BOS,POST
HEADER,Symbol,Quantity,MarkPrice,PositionValue
DATA,AAPL,100,185.50,18550.00
DATA,MSFT,50,375.00,18750.00
EOS
```

---

### Step 3: Data Transformation

The transformer (`worker/parsers/transformers.py`) converts parsed sections into SQLite-ready dictionaries:

```mermaid
flowchart LR
    subgraph Input ["FlexStatement"]
        Sections["Sections<br/>(ACCT, POST, TRNT, etc.)"]
        Meta["Metadata<br/>(Account IDs, Dates)"]
    end

    subgraph Transform ["Transform Logic"]
        AccountTF["Account Transformer"]
        PositionTF["Position Transformer"]
        TradeTF["Trade Transformer"]
        CashFlowTF["Cash Flow Transformer"]
        PriceTF["Price Transformer"]
    end

    subgraph Output ["TransformResult"]
        Accounts["account_documents[]"]
        Positions["position_documents[]"]
        Trades["trade_documents[]"]
        CashFlows["cash_flow_documents[]"]
        Prices["price_history_documents[]"]
    end

    Sections --> AccountTF
    Sections --> PositionTF
    Sections --> TradeTF
    Sections --> CashFlowTF
    Sections --> PriceTF
    Meta --> AccountTF

    AccountTF --> Accounts
    PositionTF --> Positions
    TradeTF --> Trades
    CashFlowTF --> CashFlows
    PriceTF --> Prices
```

Key transformation steps:

- **Date normalization** -- Converts IBKR date formats to ISO 8601 (`YYYY-MM-DD`)
- **Number cleaning** -- Removes commas, currency symbols, and whitespace from numeric fields
- **Field mapping** -- Maps IBKR column names to database column names
- **Deduplication** -- Uses unique constraints to prevent duplicate records

---

### Step 4: Database Write

The SQLite writer (`worker/writers/sqlite_writer.py`) performs bulk upserts:

```mermaid
sequenceDiagram
    participant Writer as SQLite Writer
    participant DB as SQLite Database

    Writer->>DB: BEGIN TRANSACTION
    Writer->>DB: INSERT OR REPLACE INTO account_snapshots
    Writer->>DB: INSERT OR REPLACE INTO position_snapshots
    Writer->>DB: INSERT OR REPLACE INTO trade_records
    Writer->>DB: INSERT OR REPLACE INTO cash_flows
    Writer->>DB: INSERT OR REPLACE INTO price_history
    Writer->>DB: COMMIT

    DB-->>Writer: Write counts per table
```

The upsert pattern (`INSERT ... ON CONFLICT DO UPDATE`) ensures that:

- Re-importing the same day's data updates existing records instead of creating duplicates
- The unique constraints (`account_id + report_date + symbol`) prevent data duplication
- Each import is idempotent (safe to run multiple times)

:::tip
The worker uses SQLite's `PRAGMA journal_mode=WAL` for concurrent access. This allows the backend to continue serving read requests while the worker is writing.
:::

---

### Step 5: API Read

When the frontend requests data, the backend reads from SQLite:

```mermaid
sequenceDiagram
    participant Frontend
    participant Router as FastAPI Router
    participant Service as Position Service
    participant DB as SQLite

    Frontend->>Router: GET /api/positions
    Router->>Service: get_positions(account_id, date)
    Service->>DB: SELECT * FROM position_snapshots<br/>WHERE account_id=? AND report_date=?
    DB-->>Service: Raw rows
    Service->>Service: Convert to Pydantic models
    Service-->>Router: List[PositionSnapshot]
    Router-->>Frontend: JSON Response
```

---

### Step 6: Frontend Display

The frontend renders data using React components and ECharts:

```mermaid
flowchart TD
    API["API Response (JSON)"] --> Hook["useAccountOverview() Hook"]
    Hook --> State["React State"]
    State --> Components

    subgraph Components ["UI Components"]
        StatCard["StatCard<br/>(Total Equity, P&L)"]
        PositionTable["PositionTable<br/>(All Holdings)"]
        EquityCurve["EquityCurveSimple<br/>(Line Chart)"]
        PieChart["PieDistributionCard<br/>(Allocation)"]
        Calendar["PerformanceCalendar<br/>(Daily P&L)"]
    end

    Components --> DOM["Browser DOM"]
```

---

## AI Agent Data Flow

The AI agents are the most complex data flow in IBKR Dash. There are two distinct patterns:

### Pattern 1: Structured Output Agents

Used by: Daily Position Review, Trade Decision, Trade Review, Risk Assessment

These agents follow a fixed pipeline: gather data -> call LLM -> parse structured JSON -> store result.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as Backend API
    participant Service as Agent Service
    participant Tools as IBKR Tools
    participant Runtime as ReAct Runtime
    participant LLM as LLM Provider
    participant DB as SQLite

    User->>Frontend: Click "Generate Review"
    Frontend->>API: POST /api/daily-position-review/generate
    API->>Service: Create agent task
    API-->>Frontend: Task ID (202 Accepted)

    Service->>Tools: Gather portfolio data
    Tools->>DB: Read positions, trades, cash flows
    DB-->>Tools: Financial data
    Tools-->>Service: Tool results

    Service->>Runtime: Run ReAct loop
    loop ReAct Rounds (max 6)
        Runtime->>LLM: Chat with tools + context
        LLM-->>Runtime: Tool calls or final answer
        alt Tool calls requested
            Runtime->>Tools: Execute tool(s) in parallel
            Tools-->>Runtime: Tool observations
        else Final answer
            Runtime-->>Service: Structured JSON output
        end
    end

    Service->>Service: Parse + Validate JSON
    Service->>DB: Store review result
    Service->>DB: Update agent task status

    Frontend->>API: GET /api/agent-tasks/{id}
    API->>DB: Read task result
    DB-->>API: Result JSON
    API-->>Frontend: Task with result
    Frontend-->>User: Display review
```

---

### Pattern 2: Copilot (Conversational Agent)

Used by: Account Copilot

The copilot is a conversational agent with memory, skills, and tool dispatch:

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as Backend API
    participant Copilot as Copilot Runtime
    participant Planner as LLM Planner
    participant Tools as IBKR Tools
    participant Skills as Skill Registry
    participant DB as SQLite

    User->>Frontend: "What's my AAPL position worth?"
    Frontend->>API: POST /api/copilot/chat<br/>{session_id, message}
    API->>Copilot: Run copilot(state)

    loop ReAct Rounds (max 8)
        Copilot->>Planner: Plan next action
        Note over Planner: Uses structured output<br/>to decide: tool_call,<br/>skill_request, or final_answer
        Planner-->>Copilot: PlannerAction

        alt action_type = "tool_call"
            Copilot->>Tools: Execute tool(name, args)
            Tools->>DB: Query portfolio data
            DB-->>Tools: Data
            Tools-->>Copilot: Observation
        else action_type = "request_skill_approval"
            Copilot-->>Frontend: "Should I run X?"
            Frontend-->>User: Approval prompt
            User->>Frontend: Approve
            Frontend->>API: Approve skill
            Copilot->>Skills: Execute skill
        else action_type = "final_answer"
            Copilot-->>API: Final answer text
        end
    end

    API->>DB: Store messages + memory
    API-->>Frontend: Copilot response
    Frontend-->>User: Display answer
```

---

## Structured Output Pipeline

All AI agents use a structured output pipeline to ensure reliable JSON output from the LLM. This is critical because LLMs can produce malformed JSON.

```mermaid
flowchart TD
    LLM["LLM Response<br/>(Raw Text)"] --> Parse["Step 1: Extract JSON<br/>extract_json_object()"]
    Parse -->|Success| Validate["Step 2: Validate<br/>Pydantic model_validate()"]
    Parse -->|Failure| Repair

    Validate -->|Success| Result["StructuredOutputResult<br/>(ok=True)"]
    Validate -->|Failure| Repair["Step 3: Repair<br/>Send to LLM with error"]

    Repair --> RepairLLM["LLM Repair Call<br/>(temperature=0)"]
    RepairLLM --> Parse2["Parse + Validate Again"]
    Parse2 -->|Success| Result
    Parse2 -->|Failure| Fallback["Step 4: Fallback<br/>Use default values"]

    Fallback --> Result

    Result --> Store["Store in SQLite"]
```

The pipeline has four stages:

1. **Parse** -- Extract a JSON object from the raw LLM text (handles markdown code blocks, extra text, etc.)
2. **Validate** -- Validate the JSON against a Pydantic model schema
3. **Repair** -- If validation fails, send the raw output back to the LLM with the error message and ask it to fix the format
4. **Fallback** -- If repair fails, use a default/fallback value

:::info
The structured output pipeline is defined in `app/agents/structured_output/`. Each agent defines a `StructuredOutputContract` that specifies the expected schema, repair behavior, and fallback logic.
:::

---

## Copilot Tool System

The Account Copilot has access to a registry of read-only tools that query the database:

```mermaid
graph TD
    subgraph Tools ["Copilot Tools"]
        T1["get_account_overview"]
        T2["get_positions"]
        T3["get_trades"]
        T4["get_cash_flows"]
        T5["get_dividends"]
        T6["get_price_history"]
        T7["get_daily_pnl"]
        T8["search_symbol"]
    end

    subgraph Skills ["Copilot Skills"]
        S1["daily_position_review"]
        S2["trade_decision"]
        S3["trade_review"]
        S4["risk_assessment"]
    end

    Copilot["Copilot Runtime"] --> Tools
    Copilot --> Skills
    Tools --> DB["SQLite Database"]
    Skills --> AgentRuntime["Agent Runtime"]
    AgentRuntime --> LLM["LLM Provider"]
    AgentRuntime --> DB
```

**Tools** are read-only database queries. The copilot can call them freely to gather data.

**Skills** are more complex operations that trigger full agent runs. They require user approval before execution and may call the LLM multiple times.

---

## Agent Task Lifecycle

Every agent execution creates a task record that tracks its progress:

```mermaid
stateDiagram-v2
    [*] --> pending: Task created
    pending --> running: Agent starts
    running --> completed: Agent finishes
    running --> failed: Error occurs
    running --> cancelled: User cancels

    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

The task record stores:

- **Progress** -- JSON updates during execution
- **Result** -- The final output (review, decision, etc.)
- **Error** -- Error message if failed
- **Timing** -- Created, started, and finished timestamps
- **Run Trace** -- Full execution trace for debugging

```mermaid
sequenceDiagram
    participant Frontend
    participant API
    participant DB as SQLite

    Note over Frontend,API: Step 1: Create task
    Frontend->>API: POST /api/daily-position-review/generate
    API->>DB: INSERT INTO agent_tasks (status=pending)
    API-->>Frontend: {task_id: "abc123"}

    Note over Frontend,API: Step 2: Poll for result
    loop Every 2 seconds
        Frontend->>API: GET /api/agent-tasks/abc123
        API->>DB: SELECT * FROM agent_tasks WHERE id='abc123'
        DB-->>API: {status: "running", progress: {...}}
        API-->>Frontend: Task still running
    end

    Note over Frontend,API: Step 3: Get final result
    Frontend->>API: GET /api/agent-tasks/abc123
    API->>DB: SELECT * FROM agent_tasks WHERE id='abc123'
    DB-->>API: {status: "completed", result: {...}}
    API-->>Frontend: Final result
    Frontend-->>User: Display review
```

---

## Copilot Memory Flow

The copilot maintains memory across conversations:

```mermaid
flowchart TD
    UserMsg["User Message"] --> Planner["Planner LLM Call"]

    subgraph Memory ["Memory System"]
        Rolling["Rolling Summary<br/>(condensed history)"]
        Pinned["Pinned Facts<br/>(key insights)"]
        Session["Session Messages<br/>(full conversation)"]
    end

    Memory --> Planner
    Planner --> Action{"Action Type?"}

    Action -->|"tool_call"| Tool["Execute Tool"]
    Tool --> Observation["Observation"]
    Observation --> Planner

    Action -->|"final_answer"| Answer["Final Answer"]
    Answer --> UpdateMemory["Update Memory"]
    UpdateMemory --> Rolling
    UpdateMemory --> Pinned
```

Memory types:

- **Rolling Summary** -- A condensed version of the conversation history, updated after each exchange
- **Pinned Facts** -- Key facts extracted from the conversation (e.g., "User is interested in tech stocks")
- **Session Messages** -- Full message history for the current session

---

## Data Freshness

Understanding when data is updated helps you interpret the dashboard:

```mermaid
gantt
    title Daily Data Timeline
    dateFormat HH:mm
    axisFormat %H:%M

    section Worker
    Flex Query Submission   :done, 12:30, 1m
    Poll for Statement      :done, 12:31, 5m
    Parse + Transform       :done, 12:36, 1m
    Write to SQLite         :done, 12:37, 1m

    section Backend
    Serve API Requests      :active, 00:00, 24h

    section Frontend
    Fetch on Page Load      :crit, 12:38, 1m
```

- **Financial data** is updated once per day (when the worker runs)
- **API responses** are real-time reads from SQLite (no caching by default, though `CACHE_TTL_SECONDS` can be configured)
- **AI agent outputs** are generated on-demand and stored permanently

:::warning
The dashboard shows the most recent snapshot date. If the worker has not run today, you will see yesterday's data. Check the report date in the dashboard header to confirm data freshness.
:::

---

## Error Handling

Each layer has its own error handling strategy:

```mermaid
flowchart TD
    subgraph Worker ["Worker Errors"]
        W1["Flex API timeout"] --> W1R["Retry up to 60 times"]
        W2["Invalid CSV format"] --> W2R["Log error, skip file"]
        W3["SQLite write failure"] --> W3R["Rollback transaction"]
    end

    subgraph Backend ["Backend Errors"]
        B1["LLM timeout"] --> B1R["Raise LLMClientError"]
        B2["Invalid JSON from LLM"] --> B2R["Structured output repair"]
        B3["Tool execution failure"] --> B3R["Return error observation"]
        B4["Max rounds exceeded"] --> B4R["Force final synthesis"]
    end

    subgraph Frontend ["Frontend Errors"]
        F1["API request failure"] --> F1R["ErrorBoundary catches"]
        F2["Invalid response"] --> F2R["ErrorBlock component"]
        F3["Network error"] --> F3R["Retry + error message"]
    end
```

---

## Summary

| Flow | Direction | Protocol | Frequency |
|------|-----------|----------|-----------|
| IBKR -> Worker | Pull | Flex Web Service API | Daily (scheduled) |
| Worker -> SQLite | Write | Direct SQL (upsert) | On import |
| SQLite -> Backend | Read | Direct SQL query | On API request |
| Backend -> Frontend | Serve | HTTP REST (JSON) | On page load |
| Frontend -> User | Display | Browser DOM | Real-time |
| User -> Copilot | Chat | HTTP REST (JSON) | On-demand |
| Copilot -> LLM | Query | HTTP (chat/completions) | Per agent round |
| LLM -> Copilot | Response | HTTP (JSON) | Per agent round |
| Copilot -> SQLite | Store | Direct SQL | After completion |
