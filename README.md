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

## Modules

| Module | Tech Stack | Description |
|--------|-----------|-------------|
| `ibkr_dash_backend` | Python, FastAPI, SQLite | API server + AI agents |
| `ibkr_dash_worker` | Python, APScheduler | IBKR Flex CSV data import |
| `ibkr_dash_frontend` | React, TypeScript, Vite | Dashboard UI |

## Quick Start

```bash
# Backend
cd ibkr_dash_backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Worker
cd ibkr_dash_worker
pip install -r requirements.txt
python -m worker.main run-scheduler

# Frontend
cd ibkr_dash_frontend
npm install
npm run dev
```

## Storage

- **SQLite**: Single embedded database for all data (financial snapshots, positions, trades, agent outputs)
- **No Redis/ES**: Replaced by SQLite for simplicity; in-memory TTL cache for hot data

## AI Agents

| Agent | Purpose |
|-------|---------|
| Account Copilot | Chat-based portfolio assistant |
| Daily Position Review | Daily portfolio review with market context |
| Trade Decision | Entry/holding analysis for specific symbols |
| Trade Review | Post-trade performance evaluation |
| Risk Assessment | Portfolio risk analysis and stress testing |
