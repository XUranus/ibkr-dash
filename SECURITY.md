# Security Policy

## Data Handling

- IBKR account data is stored locally in SQLite — never sent to third parties
- LLM calls send only the necessary context (positions, prices) — no credentials
- Longbridge API keys are loaded from environment variables
- All agent traces are sanitized to remove sensitive data (API keys, tokens)

## Authentication

- Basic auth is optional (set `AUTH_USERNAME` / `AUTH_PASSWORD` in `.env`)
- No external auth providers — this is a personal tool

## Reporting Vulnerabilities

This is a personal project. If you find a security issue, please open an issue.
