# Deployment Guide

This guide covers deploying IBKR Dash using Docker or running it directly on a server.

## Quick Start with Docker

The recommended way to deploy IBKR Dash is using Docker Compose.

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2+
- An IBKR Flex Query Token (for data import)
- (Optional) An OpenAI-compatible API key (for AI features)

### Steps

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-org/ibkr-dash.git
   cd ibkr-dash
   ```

2. **Create your environment file**:

   ```bash
   cp ibkr_dash_worker/.env.example .env
   ```

   Edit `.env` and fill in your values:

   ```env
   # Required for data import
   FLEX_TOKEN=your-ibkr-flex-token
   FLEX_QUERY_ID_DAILY=your-query-id

   # Required for AI features (optional)
   LLM_API_KEY=your-openai-api-key

   # Authentication
   AUTH_PASSWORD=your-secure-password

   # Internal token for worker-backend communication
   DAILY_REVIEW_INTERNAL_TOKEN=a-random-secret-string
   ```

3. **Build and start**:

   ```bash
   docker compose up -d --build
   ```

4. **Verify**:

   ```bash
   curl http://localhost:8080/health
   ```

5. **Access the dashboard**: Open `http://localhost:8080` in your browser.

### Docker Architecture

```
                    +------------------+
                    |   nginx (frontend)|
                    |   Port 8080      |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   backend        |
                    |   Port 8000      |
                    |   (FastAPI)      |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   SQLite         |
                    |   (data volume)  |
                    +------------------+
```

- **frontend**: React SPA served by nginx, proxies `/api/` to the backend.
- **backend**: FastAPI application with SQLite storage.
- **worker-init**: One-shot container that runs the initial data import.

### Data Volumes

The SQLite database is stored in a Docker volume. To persist data across container rebuilds:

```yaml
volumes:
  ibkr-data:
    driver: local
```

### Reverse Proxy Configuration

If deploying behind a reverse proxy (nginx, Caddy, etc.), ensure:

- WebSocket support for real-time features (if applicable)
- Sufficient `client_max_body_size` (100MB recommended for large imports)
- Proper `X-Forwarded-For` and `X-Forwarded-Proto` headers
- Health check endpoint at `/health`

## Manual Deployment

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend build)
- SQLite 3.35+

### Backend

```bash
cd ibkr_dash_backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Worker

```bash
cd ibkr_dash_worker
pip install -r requirements.txt
# Run a one-time import
python -m worker.cli import-latest
# Run the scheduler
python -m worker.cli scheduler
```

### Frontend

```bash
cd ibkr_dash_frontend
npm install
npm run build
# Serve the dist/ directory with any static file server
```

## Environment Variables

### Backend

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Environment name |
| `SQLITE_PATH` | `data/ibkr_dash.db` | Path to SQLite database |
| `AUTH_USERNAME` | `admin` | Login username |
| `AUTH_PASSWORD` | (empty) | Login password |
| `AUTH_SESSION_SECRET` | (random) | Session signing key |
| `LLM_API_KEY` | (empty) | OpenAI-compatible API key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM endpoint |
| `LLM_DEFAULT_MODEL` | `gpt-4o` | Default model |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |

### Worker

| Variable | Default | Description |
|---|---|---|
| `FLEX_TOKEN` | (empty) | IBKR Flex Web Service token |
| `FLEX_QUERY_ID_DAILY` | (empty) | Daily snapshot query ID |
| `FLEX_BASE_URL` | IBKR Flex URL | Flex API base URL |
| `SCHEDULER_ENABLED` | `true` | Enable automatic scheduling |
| `SCHEDULER_HOUR` | `12` | Hour to run daily import |
| `SCHEDULER_MINUTE` | `30` | Minute to run daily import |
| `SCHEDULER_TIMEZONE` | `Asia/Shanghai` | Scheduler timezone |
| `BACKEND_BASE_URL` | `http://localhost:8000` | Backend API URL |

## Backups

The SQLite database can be backed up by copying the database file:

```bash
# Stop the backend first to ensure consistency
cp data/ibkr_dash.db data/ibkr_dash_backup_$(date +%Y%m%d).db
```

For live backups, use SQLite's backup API:

```bash
sqlite3 data/ibkr_dash.db ".backup 'data/backup.db'"
```

## Monitoring

Health check endpoint: `GET /api/health`

Returns JSON with service status:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

## Troubleshooting

### Worker cannot connect to IBKR

- Verify `FLEX_TOKEN` is set correctly
- Check that `FLEX_QUERY_ID_DAILY` matches your IBKR Flex Query configuration
- Ensure the server can reach `interactivebrokers.com`

### Frontend shows no data

- Check that the worker has run at least one import
- Verify the backend is running and accessible
- Check browser console for API errors

### AI features not working

- Verify `LLM_API_KEY` is set
- Check `LLM_BASE_URL` is reachable
- Review backend logs for LLM provider errors
