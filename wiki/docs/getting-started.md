---
sidebar_position: 2
title: Getting Started
---

# Getting Started

This guide walks you through setting up IBKR Dash from scratch. By the end, you will have a running dashboard with sample data and all three services (backend, frontend, worker) operational.

---

## Prerequisites

Before you begin, make sure you have the following installed on your machine:

| Tool | Minimum Version | How to Check | Install Link |
|------|----------------|--------------|--------------|
| **Python** | 3.11+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | `node --version` | [nodejs.org](https://nodejs.org/) |
| **npm** | 9+ | `npm --version` | Comes with Node.js |
| **Git** | 2.30+ | `git --version` | [git-scm.com](https://git-scm.com/) |

:::tip
We recommend using a Python version manager like `pyenv` or `conda` to manage Python installations. For Node.js, `nvm` is a popular choice.
:::

:::warning
Python 3.11 or higher is required. The codebase uses modern Python features like `type | None` union syntax and `dataclasses` with `frozen=True` that are not available in older versions.
:::

---

## Step 1: Clone the Repository

Open your terminal and clone the project:

```bash
git clone https://github.com/your-username/ibkr-dash.git
cd ibkr-dash
```

After cloning, your directory structure should look like this:

```
ibkr-dash/
├── ibkr_dash_backend/       # FastAPI server + AI agents
├── ibkr_dash_frontend/      # React dashboard
├── ibkr_dash_worker/        # Data ETL worker
├── data/                    # SQLite database + Flex exports
├── docker/                  # Docker configurations
├── scripts/                 # Utility scripts
├── .env.example             # Example environment config
└── docker-compose.yml       # Docker Compose config
```

---

## Step 2: Configure Environment Variables

IBKR Dash uses `.env` files for configuration. You need to create them from the provided example.

### 2.1 Copy the example config

```bash
cp .env.example .env
```

### 2.2 Edit the root `.env`

Open `.env` in your text editor and fill in the values:

```env
# --- LLM (required for AI features) ---
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o

# --- Auth (leave empty to disable login) ---
AUTH_USERNAME=admin
AUTH_PASSWORD=your-secure-password

# --- SQLite ---
SQLITE_PATH=data/ibkr_dash.db
```

:::info
If you do not have an OpenAI API key, you can still use the data dashboard features. AI agents will be disabled but all other functionality works. You can also use any OpenAI-compatible provider (DeepSeek, MiMo, etc.) by changing `LLM_BASE_URL` and `LLM_DEFAULT_MODEL`.
:::

### 2.3 Copy config to each module

Each module (backend and worker) reads its own `.env` file. Copy the root config:

```bash
cp .env ibkr_dash_backend/.env
cp .env ibkr_dash_worker/.env
```

### 2.4 (Optional) Configure IBKR Flex Web Service

If you want automatic data pulls from IBKR (instead of manual CSV imports), add these to `ibkr_dash_worker/.env`:

```env
# Get your token from: IBKR Account Management > Settings > Flex Web Service
FLEX_TOKEN=your-flex-token
FLEX_QUERY_ID_DAILY=your-query-id
```

---

## Step 3: Start the Backend

The backend is a FastAPI server that provides the REST API and AI agent orchestration.

Open a **new terminal window** and run:

```bash
# Navigate to the backend directory
cd ibkr_dash_backend

# Create a Python virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

Verify the backend is running:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status": "ok", "version": "0.1.0"}
```

:::tip
The `--reload` flag enables auto-reload when you edit code. This is useful during development. For production, remove this flag.
:::

---

## Step 4: Start the Frontend

The frontend is a React + TypeScript application built with Vite.

Open a **second terminal window** and run:

```bash
# Navigate to the frontend directory
cd ibkr_dash_frontend

# Install npm dependencies
npm install

# Start the development server
npm run dev
```

You should see output like:

```
  VITE v5.x.x  ready in 300 ms

  ➜  Local:   http://localhost:5173/
```

Open your browser and navigate to **http://localhost:5173**. You should see the IBKR Dash login page (or the dashboard if auth is disabled).

---

## Step 5: Start the Worker (Optional)

The worker handles data import from IBKR Flex CSV files. You only need it if you want to import data.

Open a **third terminal window** and run:

```bash
# Navigate to the worker directory
cd ibkr_dash_worker

# Create a Python virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

The worker does not run as a persistent server. Instead, you use it via CLI commands (see Step 6).

---

## Step 6: Import Data

IBKR Dash needs portfolio data to display. There are three ways to get data in.

### Option A: Use Sample Data (Recommended for First Run)

The project includes sample data for testing:

```bash
cd ibkr_dash_worker
python -m worker.main import worker/fixtures/daily_sample.csv
```

:::tip
This is the fastest way to see the dashboard in action. The sample data includes realistic account snapshots, positions, trades, and cash flows.
:::

### Option B: Import a Flex CSV File

If you have exported a CSV from IBKR Flex Queries:

1. Log in to [IBKR Account Management](https://www.interactivebrokers.com/AccountManagement/AmAccountManagement)
2. Navigate to **Reports > Flex Queries**
3. Create or run a Flex Query that includes positions, trades, and cash flows
4. Export the result as CSV
5. Place the file in the `data/flex_exports/` directory
6. Run the import:

```bash
cd ibkr_dash_worker
python -m worker.main import ../data/flex_exports/your_file.csv
```

### Option C: Automatic Pull from IBKR Flex Web Service

If you configured `FLEX_TOKEN` and `FLEX_QUERY_ID_DAILY` in Step 2.4, you can run the scheduler to automatically pull data:

```bash
cd ibkr_dash_worker
python -m worker.main run-scheduler
```

This will pull data from IBKR at the scheduled time (default: 12:30 PM in the configured timezone). You can also trigger an immediate scan:

```bash
python -m worker.main scan
```

---

## Step 7: Log In

If you set `AUTH_PASSWORD` in your `.env` file, you will need to log in:

1. Open **http://localhost:5173** in your browser
2. Enter the username and password you configured
3. Click **Login**

If you left `AUTH_PASSWORD` empty, the dashboard is accessible without login.

:::warning
For security, always set a password if you expose the dashboard beyond localhost.
:::

---

## What's Next?

Once everything is running, explore the dashboard:

- **Dashboard** (`/`) -- Overview of your portfolio with key metrics
- **Positions** (`/positions`) -- Detailed table of all holdings
- **Trades** (`/trades`) -- Trade history with P&L
- **Cash Flows** (`/cash-flows`) -- Deposits, withdrawals, dividends
- **Copilot** (`/copilot`) -- Chat with your AI portfolio assistant
- **Daily Review** (`/daily-position-review`) -- AI-generated position reviews

---

## Docker Deployment (Alternative)

If you prefer Docker over running services manually:

```bash
# Build and start all services
docker compose up -d --build

# Access at http://localhost:8080
```

The Docker Compose setup runs all three services (backend, frontend, worker) in containers with a shared SQLite volume.

```bash
# View logs
docker compose logs -f backend
docker compose logs -f worker

# Stop all services
docker compose down
```

---

## Running Tests

To verify your setup is correct, run the test suites:

### Backend Tests

```bash
cd ibkr_dash_backend
.venv/bin/python -m pytest tests/ -v
```

Expected output:

```
tests/test_health.py::test_health_endpoint PASSED
tests/test_database.py::test_init_schema PASSED
tests/test_position_service.py::test_get_positions PASSED
...
43 passed
```

### Frontend Tests

```bash
cd ibkr_dash_frontend
npx vitest run
```

Expected output:

```
 ✓ src/api/__tests__/http.test.ts (5 tests)
 ✓ src/components/__tests__/StatCard.test.tsx (3 tests)
 ✓ src/views/__tests__/DashboardView.test.tsx (8 tests)
 ...
 Test Files  10 passed (10)
      Tests  74 passed (74)
```

---

## Environment Variables Reference

Here is a complete reference of all environment variables.

### Backend (`ibkr_dash_backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Application environment |
| `DEBUG` | `false` | Enable debug mode |
| `SQLITE_PATH` | `data/ibkr_dash.db` | Path to SQLite database |
| `CACHE_TTL_SECONDS` | `86400` | In-memory cache TTL (seconds) |
| `LLM_API_KEY` | (empty) | OpenAI-compatible API key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM API endpoint |
| `LLM_DEFAULT_MODEL` | `gpt-4o` | Default model name |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature |
| `LLM_MAX_TOKENS` | `8192` | Max tokens per LLM response |
| `AUTH_USERNAME` | `admin` | Login username |
| `AUTH_PASSWORD` | (empty) | Login password (empty = no auth) |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |

### Worker (`ibkr_dash_worker/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Application environment |
| `DEBUG` | `false` | Enable debug mode |
| `SQLITE_PATH` | `data/ibkr_dash.db` | Path to SQLite database (shared with backend) |
| `DATA_DIR` | `data/flex_exports` | Directory for Flex CSV files |
| `SCHEDULER_ENABLED` | `true` | Enable the background scheduler |
| `SCHEDULER_HOUR` | `12` | Hour to run daily import |
| `SCHEDULER_MINUTE` | `30` | Minute to run daily import |
| `SCHEDULER_TIMEZONE` | `Asia/Shanghai` | Timezone for scheduler |
| `FLEX_TOKEN` | (empty) | IBKR Flex Web Service token |
| `FLEX_QUERY_ID_DAILY` | (empty) | Daily snapshot query ID |
| `FLEX_POLL_INTERVAL_SECONDS` | `10` | Polling interval for Flex API |
| `FLEX_MAX_POLL_RETRIES` | `60` | Max retries for Flex API |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

You are running the command from the wrong directory. Make sure you are inside `ibkr_dash_backend/` when starting the backend:

```bash
cd ibkr_dash_backend
uvicorn app.main:app --reload --port 8000
```

### "Address already in use: port 8000"

Another process is using port 8000. Either stop that process or use a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

If you change the backend port, update `CORS_ORIGINS` in your `.env` and the frontend API base URL.

### "pip: command not found"

Use `pip3` instead of `pip`, or make sure your virtual environment is activated:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend shows "Network Error" or blank page

1. Make sure the backend is running on port 8000
2. Check that `CORS_ORIGINS` in `ibkr_dash_backend/.env` includes `http://localhost:5173`
3. Open browser developer tools (F12) and check the Console tab for errors

### "No data showing" after import

1. Verify the import command completed without errors
2. Check that the SQLite database file exists:

```bash
ls -la data/ibkr_dash.db
```

3. Query the database directly to confirm data:

```bash
sqlite3 data/ibkr_dash.db "SELECT COUNT(*) FROM position_snapshots;"
```

### "LLM provider authentication failed"

Your `LLM_API_KEY` is invalid or expired. Double-check the key in your `.env` file. If using a non-OpenAI provider, also verify `LLM_BASE_URL` is correct.

### Worker import fails with "File does not exist"

Check the file path. The worker runs from `ibkr_dash_worker/`, so use relative paths from there:

```bash
# Correct
python -m worker.main import ../data/flex_exports/my_file.csv

# Or use absolute path
python -m worker.main import /home/user/ibkr-dash/data/flex_exports/my_file.csv
```

### SQLite "database is locked"

This usually means two processes are writing to the database at the same time. SQLite uses WAL mode to minimize this, but if it occurs:

1. Stop the worker if it is running an import
2. Wait a few seconds
3. Try again

:::info
IBKR Dash uses SQLite with WAL (Write-Ahead Logging) mode enabled. This allows concurrent reads while a write is in progress, but only one writer at a time.
:::

### Docker: "Cannot connect to the Docker daemon"

Make sure Docker is installed and running:

```bash
docker --version
docker compose version
```

On Linux, you may need to add your user to the `docker` group:

```bash
sudo usermod -aG docker $USER
# Log out and log back in for the change to take effect
```

---

## Quick Reference

Here is a summary of all the commands you need:

```bash
# --- Setup ---
git clone https://github.com/your-username/ibkr-dash.git
cd ibkr-dash
cp .env.example .env
cp .env ibkr_dash_backend/.env
cp .env ibkr_dash_worker/.env
# Edit .env files with your settings

# --- Backend ---
cd ibkr_dash_backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# --- Frontend ---
cd ibkr_dash_frontend
npm install && npm run dev

# --- Worker (import sample data) ---
cd ibkr_dash_worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m worker.main import worker/fixtures/daily_sample.csv

# --- Access ---
# Dashboard:  http://localhost:5173
# API Docs:   http://localhost:8000/docs
# Health:     http://localhost:8000/api/health
```
