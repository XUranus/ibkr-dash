# Contributing

## Development Setup

```bash
# Backend
cd ibkr_dash_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --reload --port 8000

# Worker
cd ibkr_dash_worker
pip install -r requirements.txt
python -m worker.main init-db
python -m worker.main import data/sample.csv

# Frontend
cd ibkr_dash_frontend
npm install
npm run dev
```

## Code Style

- **Python**: Type hints required, English comments only
- **TypeScript**: Strict mode, English comments only
- **Docs**: English `.md` + Chinese `*.zh-CN.md` for each doc

## Testing

```bash
# Backend tests
cd ibkr_dash_backend && pytest

# Worker tests
cd ibkr_dash_worker && pytest

# Frontend tests
cd ibkr_dash_frontend && npm test
```

## Architecture Decisions

1. **SQLite over Elasticsearch**: Single-user app, data fits in SQLite comfortably
2. **No Redis**: In-memory TTL cache is sufficient
3. **No LangGraph**: Simple Python functions + asyncio.gather() for agent parallelism
4. **React over Vue**: Frontend rebuilt in React + TypeScript
