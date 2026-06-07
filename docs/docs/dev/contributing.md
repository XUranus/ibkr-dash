---
sidebar_position: 1
title: Contributing Guide
---

# Contributing Guide

Welcome to the IBKR Dash project! This guide covers code style, git workflow, pull request process, and architecture decisions to help you contribute effectively.

---

## Project Architecture

IBKR Dash is a monorepo with three modules:

```
ibkr-dash/
  ibkr_dash_backend/     # FastAPI REST API (Python)
  ibkr_dash_frontend/    # React SPA (TypeScript)
  ibkr_dash_worker/      # ETL scheduler (Python)
  data/                  # SQLite DB + Flex CSV exports
  docker/                # Dockerfiles + nginx config
  wiki/                  # Docusaurus documentation
```

### Backend (`ibkr_dash_backend/`)

- **Framework**: FastAPI with Pydantic v2 schemas
- **Database**: SQLite (no Redis, no Elasticsearch)
- **Structure**: Routes -> Services -> Database
- **AI Agents**: ReAct-style agents using LLM function calling

Key directories:

```
app/
  api/routes/     # FastAPI route handlers
  schemas/        # Pydantic request/response models
  services/       # Business logic layer
  agents/         # AI agent implementations
  core/           # Config, database, auth, logging
```

### Frontend (`ibkr_dash_frontend/`)

- **Framework**: React 18 + TypeScript (strict mode)
- **Build tool**: Vite
- **Charts**: ECharts
- **Routing**: React Router v6
- **i18n**: i18next

Key directories:

```
src/
  api/            # HTTP client functions
  components/     # Reusable UI components
  views/          # Page-level components
  hooks/          # Custom React hooks
  types/          # TypeScript type definitions
  utils/          # Utility functions
```

### Worker (`ibkr_dash_worker/`)

- **Purpose**: ETL pipeline from IBKR Flex CSV to SQLite
- **Scheduler**: APScheduler (cron-based)
- **CLI**: argparse-based commands

Key directories:

```
worker/
  clients/        # External service clients (Flex, SQLite, email)
  core/           # Config, scheduler, logging
  importers/      # Data import orchestration
  jobs/           # Scheduled job definitions
  parsers/        # CSV/XML parsing
  writers/        # Database write operations
```

---

## Code Style

### Python (Backend + Worker)

- **Type hints required** on all function signatures and return types.
- **English comments only** -- no Chinese in source code.
- **Docstrings**: Use Google-style docstrings for public functions and classes.
- **Imports**: Group imports as stdlib, third-party, local (separated by blank lines).
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants.

```python
# Good
def get_positions(
    db: Database,
    symbol: str | None = None,
    page: int = 1,
) -> PositionListResponse:
    """Return a paginated list of positions.

    Args:
        db: Database instance.
        symbol: Optional symbol filter.
        page: Page number (1-based).

    Returns:
        Paginated position list.
    """
    ...

# Bad -- missing type hints
def get_positions(db, symbol=None, page=1):
    ...
```

**Import ordering example:**

```python
# stdlib
import os
from datetime import datetime
from typing import Optional

# third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# local
from app.core.database import Database
from app.core.config import get_settings
from app.schemas.positions import PositionListResponse
```

### TypeScript (Frontend)

- **Strict mode** enabled in `tsconfig.json`.
- **English comments only**.
- **Naming**: `camelCase` for functions/variables, `PascalCase` for components/types, `UPPER_SNAKE` for constants.
- **Components**: One component per file, named exports.
- **Types**: Define in `src/types/` directory.

```typescript
// Good
interface Position {
  symbol: string;
  quantity: number;
  markPrice: number;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}

// Good -- React component with named export
export function PositionCard({ position }: { position: Position }) {
  return (
    <div className="position-card">
      <span>{position.symbol}</span>
      <span>{formatCurrency(position.markPrice)}</span>
    </div>
  );
}
```

---

## Git Workflow

### Branch Strategy

```
main            # Stable release branch
  ├── feature/* # New features
  ├── fix/*     # Bug fixes
  └── docs/*    # Documentation changes
```

### Branch Naming

Use descriptive names with prefixes:

```
feature/add-dividend-charts
fix/position-sort-order
docs/update-api-reference
```

### Commit Messages

Follow conventional commits:

```
feat: add dividend history API endpoint
fix: correct P&L calculation for options
docs: update deployment guide for Docker
refactor: extract position service from route handler
test: add unit tests for trade service
```

Prefixes: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`.

### Typical Workflow

```bash
# 1. Create a feature branch
git checkout main
git pull origin main
git checkout -b feature/my-feature

# 2. Make changes and commit
git add .
git commit -m "feat: add my new feature"

# 3. Push and create a PR
git push origin feature/my-feature

# 4. After review, merge via GitHub
```

---

## Pull Request Process

### Before Submitting

1. **Run tests** -- Make sure all tests pass.
2. **Check code style** -- No linting errors.
3. **Update docs** -- If you changed an API, update the relevant doc.
4. **Write a clear description** -- Explain what changed and why.

### PR Template

```markdown
## What changed

Brief description of the change.

## Why

The motivation behind this change.

## How to test

Steps to verify the change works.

## Checklist

- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Guidelines

- Keep PRs small and focused (one feature or fix per PR).
- Respond to review comments promptly.
- Squash commits when merging if the branch has many small commits.

---

## Architecture Decisions

These are the key design choices that shaped the project:

### 1. SQLite over Elasticsearch

IBKR Dash is a single-user application. All financial data fits comfortably in SQLite, which requires zero setup and has no external dependencies. WAL mode provides sufficient concurrency for the backend and worker sharing the same database file.

### 2. No Redis

An in-memory TTL cache (Python dict with timestamps) replaces Redis for caching. This eliminates another external dependency. The cache TTL defaults to 24 hours (`CACHE_TTL_SECONDS=86400`).

### 3. No LangGraph

AI agents use simple Python functions with `asyncio.gather()` for parallelism instead of LangGraph's graph-based orchestration. Each agent is a standalone function that takes a database and LLM service, gathers context, prompts the LLM, and returns structured output.

### 4. React over Vue

The frontend was rebuilt in React + TypeScript for better type safety and ecosystem support. Vite handles the build tooling.

### 5. FastAPI over Django

FastAPI was chosen for its automatic OpenAPI docs, Pydantic integration, and async support. The API is simple enough that Django's ORM and admin panel are unnecessary.

---

## Adding a New API Endpoint

Here is the step-by-step process:

### 1. Define the schema

Create or edit a file in `app/schemas/`:

```python
# app/schemas/my_feature.py
from pydantic import BaseModel

class MyFeatureResponse(BaseModel):
    id: str
    name: str
    value: float
```

### 2. Create the service

Add business logic in `app/services/`:

```python
# app/services/my_feature_service.py
from app.core.database import Database
from app.schemas.my_feature import MyFeatureResponse

class MyFeatureService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_feature(self, feature_id: str) -> MyFeatureResponse:
        row = self.db.execute_one(
            "SELECT * FROM my_features WHERE id = ?", (feature_id,)
        )
        if not row:
            raise ValueError(f"Feature not found: {feature_id}")
        return MyFeatureResponse(**row)
```

### 3. Create the route

Add the endpoint in `app/api/routes/`:

```python
# app/api/routes/my_feature.py
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.schemas.my_feature import MyFeatureResponse
from app.services.my_feature_service import MyFeatureService

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.get("/{feature_id}", response_model=MyFeatureResponse)
def get_feature(
    feature_id: str,
    db: Database = Depends(get_db),
    _user: str | None = Depends(get_current_user),
) -> MyFeatureResponse:
    service = MyFeatureService(db)
    return service.get_feature(feature_id)
```

### 4. Register the route

Add to `app/main.py`:

```python
from app.api.routes.my_feature import router as my_feature_router
app.include_router(my_feature_router, prefix="/api")
```

### 5. Write tests

Add tests in `tests/`:

```python
# tests/test_my_feature_service.py
from app.core.database import Database
from app.services.my_feature_service import MyFeatureService

def test_get_feature():
    db = Database(":memory:")
    db.init_schema()
    # ... insert test data and assert
```

---

## Getting Help

- Check existing issues and PRs on GitHub.
- Read the source code -- it is well-commented.
- Ask questions in the project's discussion forum.
