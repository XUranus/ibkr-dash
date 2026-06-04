# IBKR Dash

A personal investment portfolio dashboard with AI agent capabilities, powered by Interactive Brokers data.

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Frontend   │───▶│   Backend    │───▶│   SQLite     │
│  React + TS  │    │   FastAPI    │    │   (storage)  │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │
                    ┌──────┴───────┐
                    │    Worker    │
                    │  (data ETL)  │
                    └──────────────┘
```

| Module | Tech Stack | Description |
|--------|-----------|-------------|
| `ibkr_dash_backend` | Python, FastAPI, SQLite | API server + AI agents |
| `ibkr_dash_worker` | Python, APScheduler | IBKR Flex CSV data import |
| `ibkr_dash_frontend` | React, TypeScript, Vite | Dashboard UI |

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd ibkr-dash

# Copy example configs
cp .env.example .env
cp ibkr_dash_backend/.env.example ibkr_dash_backend/.env 2>/dev/null || cp .env ibkr_dash_backend/.env
cp ibkr_dash_worker/.env.example ibkr_dash_worker/.env 2>/dev/null || cp .env ibkr_dash_worker/.env
```

### 2. Edit configuration

Edit `ibkr_dash_backend/.env`:
```env
# Required for AI features
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1    # or your provider
LLM_DEFAULT_MODEL=gpt-4o                   # or mimo-v2.5, deepseek-chat, etc.

# Login password (leave empty to disable auth)
AUTH_PASSWORD=your-password
```

Edit `ibkr_dash_worker/.env`:
```env
# IBKR Flex Web Service token (for automatic data pull)
FLEX_TOKEN=your-flex-token
FLEX_QUERY_ID_DAILY=your-query-id
```

### 3. Start services

**Terminal 1 — Backend:**
```bash
cd ibkr_dash_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd ibkr_dash_frontend
npm install
npm run dev
```

**Terminal 3 — Worker (optional, for data import):**
```bash
cd ibkr_dash_worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Access

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Frontend dashboard |
| http://localhost:8000/docs | Backend API docs (Swagger) |
| http://localhost:8000/api/health | Health check |

Login with the credentials you set in `AUTH_PASSWORD`.

## Importing Data

The dashboard shows IBKR account data. To get data in:

### Option A: Import a Flex CSV file

1. Export a CSV from IBKR Flex Query (Account Management > Flex Queries)
2. Place the file in `data/flex_exports/`
3. Run the import:
```bash
cd ibkr_dash_worker
python -m worker.main import ../data/flex_exports/your_file.csv
```

### Option B: Automatic pull from IBKR Flex Web Service

Configure `FLEX_TOKEN` and `FLEX_QUERY_ID_DAILY` in the worker `.env`, then:
```bash
cd ibkr_dash_worker
python -m worker.main run-scheduler
```

### Option C: Use sample data (for testing)

```bash
cd ibkr_dash_worker
python -m worker.main import worker/fixtures/daily_sample.csv
```

## AI Agents

| Agent | Endpoint | Description |
|-------|----------|-------------|
| Account Copilot | `POST /api/copilot/chat` | Chat-based portfolio assistant |
| Daily Position Review | `POST /api/daily-position-review/generate` | Daily portfolio review |
| Trade Decision | `POST /api/trade-decision/analyze` | Entry/holding analysis |
| Trade Review | `POST /api/trade-review/review` | Post-trade evaluation |
| Risk Assessment | `POST /api/risk-assessment/assess` | Portfolio risk analysis |

All agents require `LLM_API_KEY` to be configured. Without it, the data dashboard still works but AI features are disabled.

## Docker Deployment

```bash
# Build and start all services
docker compose up -d --build

# Access at http://localhost:8080
```

## Testing

```bash
# Backend tests (43 tests)
cd ibkr_dash_backend && .venv/bin/python -m pytest tests/ -v

# Frontend tests (74 tests)
cd ibkr_dash_frontend && npx vitest run
```

## Environment Variables

See `.env.example` for all available configuration options.

### Backend (`ibkr_dash_backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLITE_PATH` | `data/ibkr_dash.db` | SQLite database path |
| `LLM_API_KEY` | (empty) | OpenAI-compatible API key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM endpoint |
| `LLM_DEFAULT_MODEL` | `gpt-4o` | Model name |
| `AUTH_USERNAME` | `admin` | Login username |
| `AUTH_PASSWORD` | (empty) | Login password (empty = no auth) |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |

### Worker (`ibkr_dash_worker/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `data/flex_exports` | CSV import directory |
| `FLEX_TOKEN` | (empty) | IBKR Flex Web Service token |
| `FLEX_QUERY_ID_DAILY` | (empty) | Daily snapshot query ID |
| `SCHEDULER_HOUR` | `12` | Daily import hour |
| `SCHEDULER_MINUTE` | `30` | Daily import minute |
| `SCHEDULER_TIMEZONE` | `Asia/Shanghai` | Scheduler timezone |

## Project Structure

```
ibkr-dash/
├── ibkr_dash_backend/          # FastAPI server + AI agents
│   ├── app/
│   │   ├── agents/             # AI agent system
│   │   │   ├── account_copilot/ # Chat agent
│   │   │   ├── daily_review/   # Daily position review
│   │   │   ├── trade_decision/ # Trade decision analysis
│   │   │   ├── trade_review/   # Trade review
│   │   │   ├── risk_assessment/# Risk assessment
│   │   │   ├── structured_output/ # Output validation
│   │   │   └── eval_cases/     # Evaluation framework
│   │   ├── api/routes/         # API endpoints (20 routes)
│   │   ├── services/           # Business logic
│   │   ├── schemas/            # Pydantic models
│   │   └── core/               # Config, DB, auth
│   └── tests/                  # Backend tests
├── ibkr_dash_frontend/         # React + TypeScript
│   ├── src/
│   │   ├── views/              # Page components (19 views)
│   │   ├── components/         # Reusable components
│   │   ├── api/                # API clients
│   │   └── types/              # TypeScript types
│   └── package.json
├── ibkr_dash_worker/           # Data ETL
│   ├── worker/
│   │   ├── parsers/            # IBKR Flex CSV parser
│   │   ├── clients/            # DB and API clients
│   │   └── jobs/               # Scheduled jobs
│   └── tests/
├── docker/                     # Docker configs
├── scripts/                    # Utility scripts
└── docs/                       # Documentation
```

## License

MIT
