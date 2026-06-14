<p align="center">
  <img src="frontend/public/vite.svg" width="80" alt="IBKR Dash Logo">
</p>

<h1 align="center">IBKR Dash</h1>

<p align="center">
  <strong>Personal investment portfolio dashboard with AI agent capabilities</strong>
</p>

<p align="center">
  Powered by Interactive Brokers data · FastAPI · React · AI Agents
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/node-18+-green?logo=node.js&logoColor=white" alt="Node.js 18+">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="MIT License">
  <img src="https://img.shields.io/badge/docker-ready-blue?logo=docker&logoColor=white" alt="Docker Ready">
</p>

---

## Overview

IBKR Dash is a self-hosted investment portfolio dashboard that pulls data from Interactive Brokers via the Flex Web Service, stores it in SQLite, and presents it through a modern web UI. It includes five AI agents powered by any OpenAI-compatible LLM for portfolio analysis, trade decisions, and risk assessment.

**Key highlights:**

- 📊 **Real-time portfolio dashboard** — equity curves, position tables, performance calendars
- 🤖 **5 AI agents** — copilot, daily review, trade decisions, trade reviews, risk assessment
- 🔒 **HMAC session auth** — cookie-based sessions with optional password protection
- 🌐 **i18n support** — English and Chinese (Simplified)
- 🐳 **Docker ready** — single `docker compose up` to run everything
- ⚙️ **Admin UI** — configure LLM, IBKR, scheduler, email, and auth from the browser

---

## Features

### Portfolio Data

| Feature | Description |
|---------|-------------|
| Dashboard | Portfolio overview with equity curve, asset distribution, P&L calendar |
| Positions | Real-time and historical position data with detail drill-down |
| Trades | Trade history with per-trade P&L and summary statistics |
| Cash Flows | Deposits, withdrawals, transfers with running balance |
| Dividends | Dividend history and summary by symbol |
| Charts | Equity curve, performance calendar, sector distribution |

### AI Agents

| Agent | Endpoint | Description |
|-------|----------|-------------|
| **Account Copilot** | `POST /api/copilot/chat` | Chat-based portfolio assistant with tool use |
| **Daily Position Review** | `POST /api/daily-position-review/generate` | AI-generated daily portfolio analysis |
| **Trade Decision** | `POST /api/trade-decision/analyze` | Entry/exit/hold analysis for positions |
| **Trade Review** | `POST /api/trade-review/review` | Post-trade evaluation and lessons |
| **Risk Assessment** | `POST /api/risk-assessment/assess` | Portfolio risk analysis and alerts |

### Administration

| Feature | Description |
|---------|-------------|
| Settings | Centralized config UI for all services |
| Scheduler | Cron-based IBKR data import with manual trigger |
| Prompt Management | Edit AI agent prompts without code changes |
| LLM Management | Switch providers, test connections |
| Agent Monitoring | View agent traces, runs, and errors |
| Email | SMTP config for daily review delivery |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│                  React 18 + TypeScript + Vite                │
│              ECharts · React Router · i18next                │
└────────────────────────┬────────────────────────────────────┘
                         │ /api/* (Nginx proxy)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                        │
│          uvicorn · Pydantic v2 · httpx · SQLite              │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Copilot  │ │  Daily   │ │  Trade   │ │   Risk   │        │
│  │  Agent   │ │  Review  │ │ Decision │ │Assessment│        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Structured Output Pipeline                │       │
│  │    parse → validate → repair → fallback           │       │
│  └──────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────┐       │
│  │              ReAct Runtime                        │       │
│  │       plan → tool_call → observe → answer         │       │
│  └──────────────────────────────────────────────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQLite (WAL mode)                          │
│            data/ibkr_dash.db (shared with Worker)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Worker (Python)                           │
│            APScheduler · IBKR Flex Web Service               │
│           Fetch → Parse (CSV/XML) → Transform → Write        │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| Git | 2.30+ | [git-scm.com](https://git-scm.com/) |

### Local Development

```bash
# 1. Clone
git clone https://github.com/xuranus/ibkr-dash.git
cd ibkr-dash

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install && npm run dev

# 4. Worker (new terminal, optional)
cd worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Docker

```bash
docker compose up -d --build
# → http://localhost:8080
```

If port 8080 is in use: `FRONTEND_PORT=8081 docker compose up -d`.

---

## Configuration

All configuration is stored in `data/config.json` and managed via **Admin Settings** at `http://localhost:5173/admin/settings`. No `.env` files.

<details>
<summary><strong>Full configuration reference (click to expand)</strong></summary>

### IBKR Flex

| Key | Default | Description |
|-----|---------|-------------|
| `ibkr.flex_token` | `""` | Flex Web Service token |
| `ibkr.flex_query_ids` | `"1532356,1532359"` | Comma-separated query IDs |
| `ibkr.flex_base_url` | `https://www.interactivebrokers.com/...` | Flex API URL |
| `ibkr.flex_poll_interval_seconds` | `10` | Poll interval |
| `ibkr.flex_max_poll_retries` | `60` | Max retries |

### LLM

| Key | Default | Description |
|-----|---------|-------------|
| `llm.api_key` | `""` | OpenAI-compatible API key |
| `llm.base_url` | `https://api.openai.com/v1` | API endpoint |
| `llm.default_model` | `gpt-4o` | Model name |
| `llm.temperature` | `0.1` | Sampling temperature |
| `llm.max_tokens` | `8192` | Max response tokens |

### Scheduler

| Key | Default | Description |
|-----|---------|-------------|
| `scheduler.enabled` | `true` | Enable cron scheduler |
| `scheduler.hour` | `12` | Hour to run |
| `scheduler.minute` | `30` | Minute to run |
| `scheduler.timezone` | `Asia/Shanghai` | Timezone |

### Auth

| Key | Default | Description |
|-----|---------|-------------|
| `auth.username` | `admin` | Login username |
| `auth.password` | `""` | Password (empty = no auth) |
| `auth.cookie_secure` | `false` | Require HTTPS for cookies |

### Email

| Key | Default | Description |
|-----|---------|-------------|
| `email.smtp_host` | `""` | SMTP server |
| `email.smtp_port` | `587` | SMTP port |
| `email.smtp_username` | `""` | SMTP username |
| `email.smtp_password` | `""` | SMTP password |
| `email.from_address` | `""` | Sender address |
| `email.to_addresses` | `[]` | Recipient addresses |
| `email.enabled` | `false` | Enable email |

### Advanced

| Key | Default | Description |
|-----|---------|-------------|
| `advanced.app_env` | `"development"` | Environment name |
| `advanced.debug` | `false` | Debug mode |
| `advanced.sqlite_path` | `"data/ibkr_dash.db"` | Database path |
| `advanced.log_level` | `"INFO"` | Logging level |
| `advanced.cors_origins` | `"http://localhost:5173"` | CORS origins |
| `advanced.data_dir` | `"data/flex_exports"` | Flex export dir |
| `advanced.cache_ttl_seconds` | `86400` | Cache TTL (24h) |

</details>

See [`config.example.json`](config.example.json) for the full template.

---

## Usage

### Import Data

```bash
# From a Flex CSV export
cd worker
python -m worker.main import ../data/flex_exports/your_file.csv

# Use sample data
python -m worker.main import worker/fixtures/daily_sample.csv

# Automatic pull (requires Flex token in Admin Settings)
python -m worker.main run-scheduler
```

### Chat with Copilot

```bash
curl -X POST http://localhost:8000/api/copilot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my current portfolio allocation?"}'
```

### Trigger AI Analysis

```bash
# Daily position review
curl -X POST http://localhost:8000/api/daily-position-review/generate \
  -H "Content-Type: application/json" \
  -d '{"account_id": "U1234567"}'

# Trade decision
curl -X POST http://localhost:8000/api/trade-decision/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "action": "buy"}'

# Risk assessment
curl -X POST http://localhost:8000/api/risk-assessment/assess \
  -H "Content-Type: application/json" \
  -d '{"account_id": "U1234567"}'
```

---

## API Reference

All endpoints are prefixed with `/api`. Full interactive docs at `http://localhost:8000/docs`.

### Portfolio Data

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/account/overview` | Account overview |
| `GET` | `/api/account/snapshots` | Account snapshots |
| `GET` | `/api/positions` | Position list with pagination |
| `GET` | `/api/positions/{symbol}` | Position detail |
| `GET` | `/api/positions/{symbol}/realtime` | Real-time position data |
| `GET` | `/api/trades` | Trade history |
| `GET` | `/api/trades/summary` | Trade summary stats |
| `GET` | `/api/cash-flows` | Cash flow list |
| `GET` | `/api/cash-flows/summary` | Cash flow summary |
| `GET` | `/api/dividends` | Dividend history |
| `GET` | `/api/dividends/summary` | Dividend summary |
| `GET` | `/api/charts/equity-curve` | Equity curve data |
| `GET` | `/api/charts/performance-calendar` | Daily P&L calendar |

### AI Agents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/copilot/chat` | Chat with copilot |
| `GET` | `/api/copilot/sessions` | List chat sessions |
| `POST` | `/api/daily-position-review/generate` | Generate daily review |
| `GET` | `/api/daily-position-review/latest` | Get latest review |
| `POST` | `/api/trade-decision/analyze` | Analyze trade decision |
| `POST` | `/api/trade-review/review` | Review a trade |
| `POST` | `/api/risk-assessment/assess` | Assess portfolio risk |
| `GET` | `/api/agent-tasks` | List agent tasks |
| `GET` | `/api/agent-tasks/{id}` | Get task detail |

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Log in |
| `POST` | `/api/auth/logout` | Log out |
| `GET` | `/api/auth/session` | Check session status |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/settings` | List all settings |
| `PUT` | `/api/admin/settings` | Update settings |
| `POST` | `/api/admin/settings/reset` | Reset to defaults |
| `GET` | `/api/admin/system/status` | System status |
| `GET` | `/api/admin/llm/health` | LLM connection health |
| `POST` | `/api/admin/llm/test` | Test LLM connection |
| `GET` | `/api/admin/ibkr/settings` | IBKR settings |
| `POST` | `/api/admin/scheduler/trigger-import` | Trigger data import |
| `POST` | `/api/admin/scheduler/trigger-ai-report` | Trigger AI report |
| `GET` | `/api/admin/prompts` | List AI prompts |
| `POST` | `/api/admin/prompts` | Create/update prompt |
| `GET` | `/api/admin/agent-monitoring/overview` | Agent monitoring |

---

## Development

### Project Structure

```
ibkr-dash/
├── backend/                    # FastAPI server + AI agents
│   ├── app/
│   │   ├── agents/             # AI agent system (5 agents)
│   │   │   ├── account_copilot/
│   │   │   ├── daily_review/
│   │   │   ├── trade_decision/
│   │   │   ├── trade_review/
│   │   │   ├── risk_assessment/
│   │   │   └── structured_output/
│   │   ├── api/routes/         # 25 route modules
│   │   ├── services/           # Business logic
│   │   ├── schemas/            # Pydantic models
│   │   └── core/               # Config, DB, auth, cache
│   └── tests/                  # 16 test files
├── frontend/                   # React + TypeScript
│   ├── src/
│   │   ├── views/              # 19 page components
│   │   ├── components/         # 20 reusable components
│   │   ├── api/                # API clients
│   │   ├── hooks/              # React hooks
│   │   ├── i18n/               # EN + ZH-CN translations
│   │   ├── types/              # TypeScript types
│   │   └── utils/              # Utility functions
│   └── package.json
├── worker/                     # Data ETL
│   ├── worker/
│   │   ├── parsers/            # IBKR Flex CSV/XML parsers
│   │   ├── clients/            # DB and API clients
│   │   ├── jobs/               # Scheduled jobs
│   │   └── core/               # Config, logger, scheduler
│   └── tests/                  # 5 test files
├── data/                       # Runtime data (gitignored)
│   ├── ibkr_dash.db            # SQLite database
│   ├── config.json             # App configuration
│   └── flex_exports/           # IBKR Flex CSV/XML files
├── docker/                     # Dockerfiles + nginx.conf
├── docs/                       # Docusaurus documentation
├── scripts/                    # Utility scripts
├── config.example.json         # Config template
├── docker-compose.yml          # Docker orchestration
└── .dockerignore               # Build context exclusions
```

### Running Tests

```bash
# Backend (16 test files)
cd backend && python -m pytest tests/ -v

# Frontend (10 test files)
cd frontend && npx vitest run

# Worker
cd worker && python -m pytest tests/ -v
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | FastAPI + Pydantic v2 | REST API with validation |
| Database | SQLite (WAL mode) | Zero-config embedded DB |
| HTTP Client | httpx | LLM API calls |
| Worker | APScheduler | Cron-like job scheduling |
| Frontend | React 18 + TypeScript | UI framework |
| Build Tool | Vite 5 | Dev server + bundler |
| Charts | ECharts 5.5 | Interactive visualizations |
| i18n | react-i18next | EN + ZH-CN |
| Auth | HMAC-SHA256 | Session tokens |
| AI | OpenAI-compatible API | Any LLM provider |

---

## FAQ

<details>
<summary><strong>Can I use a non-OpenAI LLM provider?</strong></summary>

Yes. Any OpenAI-compatible API works. Set `llm.base_url` and `llm.api_key` in Admin Settings. Supported providers include DeepSeek, Xiaomi MiMo, Ollama, LiteLLM, and more.
</details>

<details>
<summary><strong>How do I disable authentication?</strong></summary>

Leave `auth.password` empty in Admin Settings. The dashboard will be accessible without login.
</details>

<details>
<summary><strong>Where is my data stored?</strong></summary>

All data is stored locally in `data/ibkr_dash.db` (SQLite). Configuration is in `data/config.json`. Neither file is committed to version control.
</details>

<details>
<summary><strong>How do I change the scheduler time?</strong></summary>

Go to Admin Settings → Scheduler and update `hour`, `minute`, and `timezone`. Changes take effect immediately — no restart needed.
</details>

<details>
<summary><strong>Can I run this without Docker?</strong></summary>

Yes. Follow the [Local Development](#local-development) instructions. Each module (backend, frontend, worker) runs independently.
</details>

<details>
<summary><strong>How do I back up my data?</strong></summary>

Copy `data/ibkr_dash.db` and `data/config.json`. For Docker:
```bash
docker compose exec backend cp /app/data/ibkr_dash.db /tmp/backup.db
docker compose cp backend:/tmp/backup.db ./backup.db
```
</details>

---

## Documentation

Full documentation is available in the [`docs/`](docs/) directory (powered by Docusaurus):

- [Getting Started](docs/docs/getting-started.md)
- [Configuration](docs/docs/backend/config.md)
- [Docker Deployment](docs/docs/deployment/docker.md)
- [Production Deployment](docs/docs/deployment/production.md)
- [API Reference](docs/docs/api/overview.md)
- [Architecture](docs/docs/architecture/overview.md)

---

## License

[MIT](LICENSE)
