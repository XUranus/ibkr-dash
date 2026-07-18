# Agent Instructions — ibkr-dash

## VPS Deployment

- **IP**: 108.181.196.185
- **SSH Port**: 10065
- **User**: root
- **Password**: `Wxx@19981228as`
- **Docker path**: `/opt/ibkr-dash`
- **Connect**: `sshpass -p 'Wxx@19981228as' ssh -o StrictHostKeyChecking=no -p 10065 root@108.181.196.185`
- **Deploy flow**: build locally → `docker save | gzip` → scp → `docker load` → `docker compose up -d --force-recreate backend`

## Project Structure

- `backend/` — FastAPI backend (account, positions, trades, charts, agents)
- `worker/` — IBKR Flex XML parser, SQLite writer, scheduler
- `frontend/` — React frontend
- `docker/` — Dockerfiles and entrypoint
- `data/` — SQLite DB, config, flex XML exports (local dev)

## Key Files

- `backend/app/services/account_service.py` — Account overview, net_cost, P&L computation
- `backend/app/services/chart_service.py` — Equity curve, performance calendar
- `worker/worker/parsers/flex_xml_parser.py` — IBKR Flex XML parser
- `worker/worker/clients/sqlite_writer.py` — SQLite upsert with zero-value guards

## P&L Computation

- `net_cost` = total deposits - withdrawals (from cash_flows table, or TWR-based fallback)
- `total_pnl` = total_equity - net_cost
- `unrealized_pnl` = SUM(fifo_pnl_unrealized) from position_snapshots
- `realized_pnl` = total_pnl - unrealized_pnl
- `stock_value` = total_equity - cash (always recomputed, never trust DB value)
