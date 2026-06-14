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
| `backend` | Python, FastAPI, SQLite | API server + AI agents |
| `worker` | Python, APScheduler | IBKR Flex CSV data import |
| `frontend` | React, TypeScript, Vite | Dashboard UI |

## Quick Start

### 1. Clone

```bash
git clone <repo-url>
cd ibkr-dash
```

### 2. Start services

**Terminal 1 — Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Terminal 3 — Worker (optional, for data import):**
```bash
cd worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Open **http://localhost:5173/admin/settings** and set:
- **LLM API Key** — required for AI features
- **Auth Password** — leave empty for open access
- **Flex Token** — for automatic IBKR data pulls

### 4. Access

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Frontend dashboard |
| http://localhost:5173/admin/settings | Configuration |
| http://localhost:8000/docs | Backend API docs (Swagger) |
| http://localhost:8000/api/health | Health check |

## Importing Data

### Option A: Import a Flex CSV file

1. Export a CSV from IBKR Flex Query (Account Management > Flex Queries)
2. Place the file in `data/flex_exports/`
3. Run the import:
```bash
cd worker
python -m worker.main import ../data/flex_exports/your_file.csv
```

### Option B: Automatic pull from IBKR Flex Web Service

Configure the Flex token in Admin Settings, then:
```bash
cd worker
python -m worker.main run-scheduler
```

### Option C: Use sample data (for testing)

```bash
cd worker
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

All agents require an LLM API key to be configured in Admin Settings. Without it, the data dashboard still works but AI features are disabled.

## Docker Deployment

```bash
# Build and start all services
docker compose up -d --build

# Access at http://localhost:8080
# Configure at http://localhost:8080/admin/settings
```

If port 8080 is in use, override with `FRONTEND_PORT=8081 docker compose up -d`.

See [Docker Deployment docs](docs/docs/deployment/docker.md) for details.

## Configuration

All configuration is stored in `data/config.json` and managed via the **Admin Settings** UI. See [Configuration docs](docs/docs/backend/config.md) for the full reference.

## Testing

```bash
# Backend tests (43 tests)
cd backend && .venv/bin/python -m pytest tests/ -v

# Frontend tests (74 tests)
cd frontend && npx vitest run
```

## Project Structure

```
ibkr-dash/
├── backend/          # FastAPI server + AI agents
│   ├── app/
│   │   ├── agents/             # AI agent system
│   │   │   ├── account_copilot/ # Chat agent
│   │   │   ├── daily_review/   # Daily position review
│   │   │   ├── trade_decision/ # Trade decision analysis
│   │   │   ├── trade_review/   # Trade review
│   │   │   ├── risk_assessment/# Risk assessment
│   │   │   └── structured_output/ # Output validation
│   │   ├── api/routes/         # API endpoints (20 routes)
│   │   ├── services/           # Business logic
│   │   ├── schemas/            # Pydantic models
│   │   └── core/               # Config, DB, auth
│   └── tests/                  # Backend tests
├── frontend/         # React + TypeScript
│   ├── src/
│   │   ├── views/              # Page components (19 views)
│   │   ├── components/         # Reusable components
│   │   ├── api/                # API clients
│   │   └── types/              # TypeScript types
│   └── package.json
├── worker/           # Data ETL
│   ├── worker/
│   │   ├── parsers/            # IBKR Flex CSV parser
│   │   ├── clients/            # DB and API clients
│   │   └── jobs/               # Scheduled jobs
│   └── tests/
├── data/                       # SQLite DB + config.json + Flex exports
├── docker/                     # Dockerfiles + nginx.conf
├── config.example.json         # Config template (data/config.json is gitignored)
├── scripts/                    # Utility scripts
├── .dockerignore               # Docker build context exclusions
└── docs/                       # Documentation (Docusaurus)
```

## License

MIT
