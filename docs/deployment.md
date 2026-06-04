# Deployment Guide

This guide covers deploying IBKR Dash using Docker or running it directly on a server.

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- An IBKR Flex Query Token (for data import)
- (Optional) An OpenAI-compatible API key (for AI features)

### Step 1: Clone and configure

```bash
cd /path/to/ibkr-dash

# Backend config
cp ibkr_dash_backend/.env.example ibkr_dash_backend/.env
# Edit ibkr_dash_backend/.env with your LLM API key and auth password

# Worker config
cp ibkr_dash_worker/.env.example ibkr_dash_worker/.env
# Edit ibkr_dash_worker/.env with your IBKR Flex token
```

### Step 2: Start Backend

```bash
cd ibkr_dash_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Step 3: Start Frontend

```bash
cd ibkr_dash_frontend
npm install
npm run dev
```

### Step 4: Import Data

```bash
cd ibkr_dash_worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Import a Flex CSV file
python -m worker.main import ../data/flex_exports/your_file.csv

# Or import sample data for testing
python -m worker.main import worker/fixtures/daily_sample.csv
```

### Step 5: Access

- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Login: `admin` / your-password

## Docker Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2+

### Steps

1. **Create environment files**:

   ```bash
   # Backend
   cp ibkr_dash_backend/.env.example ibkr_dash_backend/.env
   # Edit with your settings

   # Worker
   cp ibkr_dash_worker/.env.example ibkr_dash_worker/.env
   # Edit with your settings
   ```

2. **Build and start**:

   ```bash
   docker compose up -d --build
   ```

3. **Access**: http://localhost:8080

4. **Import data** (inside the worker container):

   ```bash
   docker compose exec worker python -m worker.main import worker/fixtures/daily_sample.csv
   ```

## Configuration Reference

### Backend (`ibkr_dash_backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment name |
| `DEBUG` | `true` | Debug mode |
| `SQLITE_PATH` | `data/ibkr_dash.db` | SQLite database path |
| `CACHE_TTL_SECONDS` | `86400` | Cache TTL (24h) |
| `LLM_API_KEY` | (empty) | OpenAI-compatible API key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM endpoint |
| `LLM_DEFAULT_MODEL` | `gpt-4o` | Model name |
| `LLM_TEMPERATURE` | `0.1` | Temperature |
| `LLM_MAX_TOKENS` | `4096` | Max tokens |
| `AUTH_USERNAME` | `admin` | Login username |
| `AUTH_PASSWORD` | (empty) | Login password (empty = no auth) |
| `CORS_ORIGINS` | `http://localhost:5173` | CORS origins |

### Worker (`ibkr_dash_worker/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLITE_PATH` | `data/ibkr_dash.db` | SQLite path (shared with backend) |
| `DATA_DIR` | `data/flex_exports` | CSV import directory |
| `SCHEDULER_ENABLED` | `true` | Enable scheduler |
| `SCHEDULER_HOUR` | `12` | Daily import hour |
| `SCHEDULER_MINUTE` | `30` | Daily import minute |
| `SCHEDULER_TIMEZONE` | `Asia/Shanghai` | Timezone |
| `FLEX_TOKEN` | (empty) | IBKR Flex Web Service token |
| `FLEX_QUERY_ID_DAILY` | (empty) | Daily query ID |
| `BACKEND_BASE_URL` | `http://localhost:8000` | Backend URL |

### Supported LLM Providers

| Provider | Base URL | Model Examples |
|----------|----------|----------------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| Xiaomi MiMo | `https://token-plan-cn.xiaomimimo.com/v1` | `mimo-v2.5`, `mimo-v2.5-pro` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat`, `deepseek-reasoner` |
| Anthropic (via proxy) | Your proxy URL | `claude-sonnet-4-20250514` |

## Data Import

### IBKR Flex Query Setup

1. Log in to IBKR Account Management
2. Go to Settings > Flex Web Service
3. Generate a Flex Web Service token
4. Create a Flex Query with the data you want (positions, trades, cash flows)
5. Note the Query ID
6. Configure `FLEX_TOKEN` and `FLEX_QUERY_ID_DAILY` in the worker `.env`

### Manual CSV Import

Export a CSV from IBKR Flex Query and import it:

```bash
cd ibkr_dash_worker
python -m worker.main import /path/to/your/flex_export.csv
```

### Automatic Import

Configure the scheduler in the worker `.env`:

```env
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=12
SCHEDULER_MINUTE=30
SCHEDULER_TIMEZONE=Asia/Shanghai
FLEX_TOKEN=your-token
FLEX_QUERY_ID_DAILY=your-query-id
```

Then run the scheduler:

```bash
python -m worker.main run-scheduler
```

## Backups

The SQLite database can be backed up by copying the file:

```bash
cp data/ibkr_dash.db data/backup_$(date +%Y%m%d).db
```

For live backups:

```bash
sqlite3 data/ibkr_dash.db ".backup 'data/backup.db'"
```

## Troubleshooting

### No data showing in dashboard

- Import data first (see Data Import section above)
- Check that the backend is running: `curl http://localhost:8000/api/health`
- Check that the SQLite database has data: `sqlite3 data/ibkr_dash.db "SELECT COUNT(*) FROM account_snapshots"`

### LLM not configured

- Set `LLM_API_KEY` in `ibkr_dash_backend/.env`
- Restart the backend
- Test: `curl -X POST http://localhost:8000/api/admin/llm/test -H "Content-Type: application/json" -d '{"message":"Hello"}'`

### Login not working

- Check `AUTH_PASSWORD` is set in `ibkr_dash_backend/.env`
- If `AUTH_PASSWORD` is empty, login is disabled (open access)
