# Security Policy

## Data Handling

- IBKR account data is stored locally in SQLite — never sent to third parties
- LLM calls send only the necessary context (positions, prices) — no credentials
- Longbridge API keys are stored in `data/config.json` (gitignored)
- All agent traces are sanitized to remove sensitive data (API keys, tokens)

## Authentication

- Basic auth is optional (leave `auth.password` empty in Admin Settings to disable)
- No external auth providers — this is a personal tool

## Reporting Vulnerabilities

This is a personal project. If you find a security issue, please open an issue.
