---
sidebar_position: 4
title: Backup & Migration
---

# Backup & Migration

IBKR Dash uses **code-data separation**: all persistent data lives on the host filesystem, bind-mounted into Docker containers. This makes backup and migration straightforward — just copy the data directory.

---

## Data Directory Structure

All persistent data lives in a single directory on the host (default: `/opt/ibkr-dash/data/`):

```
/opt/ibkr-dash/data/
├── config.json          # System configuration (LLM, IBKR, auth, etc.)
├── ibkr_dash.db         # Main SQLite database (positions, trades, snapshots)
├── flex_exports/        # Downloaded IBKR Flex XML reports
├── audit/               # LLM call audit logs
└── reports/             # Generated reports
```

### Docker Volume Mount

In `docker-compose.yml`, this directory is bind-mounted into the container:

```yaml
services:
  backend:
    volumes:
      - ${IBKR_DATA_DIR:-./data}:/app/backend/data
    environment:
      - CONFIG_PATH=/app/backend/data/config.json
```

| Host Path | Container Path | Contents |
|-----------|---------------|----------|
| `/opt/ibkr-dash/data/` | `/app/backend/data/` | All persistent data |

### What's NOT in the data directory

| Item | Location | Notes |
|------|----------|-------|
| Application code | Inside Docker image | Rebuilt on update, not persistent |
| Python dependencies | Inside Docker image | Installed during build |
| Logs | stdout/stderr | Collected by `docker logs`, managed by Docker log rotation |

---

## Backup

### Quick Backup

```bash
# Stop containers to ensure database consistency
cd /opt/ibkr-dash
docker compose stop backend

# Create a compressed backup
tar czf ~/ibkr-dash-backup-$(date +%Y%m%d).tar.gz -C /opt/ibkr-dash data/

# Restart
docker compose start backend
```

### Zero-Downtime Backup (SQLite safe copy)

SQLite supports hot backup without stopping the service:

```bash
# Use SQLite's .backup command for a consistent snapshot
docker compose exec backend python3 -c "
import sqlite3
src = sqlite3.connect('/app/backend/data/ibkr_dash.db')
dst = sqlite3.connect('/tmp/ibkr_dash_backup.db')
src.backup(dst)
src.close()
dst.close()
"

# Copy out of container
docker compose cp backend:/tmp/ibkr_dash_backup.db \
  /opt/ibkr-dash/data/ibkr_dash_backup_$(date +%Y%m%d).db

# Compress
tar czf ~/ibkr-dash-backup-$(date +%Y%m%d).tar.gz \
  -C /opt/ibkr-dash data/ibkr_dash_backup_$(date +%Y%m%d).db \
  data/config.json data/flex_exports/

# Clean up temp file in container
docker compose exec backend rm /tmp/ibkr_dash_backup.db
```

### Automated Daily Backup (cron)

Create a backup script:

```bash
sudo nano /opt/ibkr-dash/backup.sh
```

```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/ibkr-dash"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/opt/ibkr-dash"

mkdir -p "$BACKUP_DIR"

# Hot backup SQLite database
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T backend python3 -c "
import sqlite3
src = sqlite3.connect('/app/backend/data/ibkr_dash.db')
dst = sqlite3.connect('/tmp/backup.db')
src.backup(dst)
src.close()
dst.close()
"

# Copy from container
docker compose -f "$PROJECT_DIR/docker-compose.yml" \
  cp backend:/tmp/backup.db "$BACKUP_DIR/ibkr_dash_$DATE.db"

# Also backup config and flex exports
tar czf "$BACKUP_DIR/full_$DATE.tar.gz" \
  -C "$PROJECT_DIR" \
  data/config.json \
  data/flex_exports/

# Clean up
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T backend rm /tmp/backup.db

# Keep only last 30 backups
ls -t "$BACKUP_DIR"/ibkr_dash_*.db 2>/dev/null | tail -n +31 | xargs -r rm -f
ls -t "$BACKUP_DIR"/full_*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm -f

echo "Backup completed: $DATE"
```

```bash
chmod +x /opt/ibkr-dash/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /opt/ibkr-dash/backup.sh >> /var/log/ibkr-backup.log 2>&1
```

### What to Back Up

| Item | Priority | Size | Notes |
|------|----------|------|-------|
| `config.json` | **Critical** | ~3 KB | Contains all secrets and settings |
| `ibkr_dash.db` | **Critical** | ~18 MB | All portfolio data |
| `flex_exports/` | Medium | ~1 MB | Can re-download from IBKR |
| `audit/` | Low | ~100 KB | LLM call logs |
| `reports/` | Low | ~50 KB | Generated reports |

---

## Restore

### From Full Backup

```bash
cd /opt/ibkr-dash

# Stop containers
docker compose down

# Restore data directory
tar xzf ~/ibkr-dash-backup-20250718.tar.gz -C /opt/ibkr-dash/

# Restart
docker compose up -d
```

### Database Only

```bash
cd /opt/ibkr-dash

# Stop backend to release database lock
docker compose stop backend worker

# Replace database file
cp ~/backup/ibkr_dash_20250718.db /opt/ibkr-dash/data/ibkr_dash.db

# Restart
docker compose start backend worker
```

### Config Only

```bash
# Replace config file
cp ~/backup/config.json /opt/ibkr-dash/data/config.json

# Restart to pick up new config
docker compose restart backend
```

---

## Migration to a New Server

### Step 1: Backup on Old Server

```bash
# On old server
cd /opt/ibkr-dash
docker compose stop backend
tar czf ~/ibkr-dash-migration.tar.gz -C /opt/ibkr-dash data/
```

### Step 2: Set Up New Server

```bash
# On new server — install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Log out and back in

# Clone repository
sudo mkdir -p /opt/ibkr-dash
sudo chown $USER:$USER /opt/ibkr-dash
cd /opt/ibkr-dash
git clone https://github.com/XUranus/ibkr-dash.git .
```

### Step 3: Transfer Data

```bash
# From old server to new server
scp ~/ibkr-dash-migration.tar.gz user@new-server:~/

# On new server
cd /opt/ibkr-dash
tar xzf ~/ibkr-dash-migration.tar.gz -C /opt/ibkr-dash/
```

### Step 4: Build and Start

```bash
cd /opt/ibkr-dash

# Build containers
docker compose up --build -d

# Verify
docker compose ps
curl http://localhost:8080/api/health
```

### Step 5: Update Config (if needed)

If the new server has different settings (e.g., different domain, ports):

```bash
# Edit config
nano /opt/ibkr-dash/data/config.json

# Key fields to update:
# - auth.password (if changing)
# - advanced.cors_origins (new domain)
# - notifyhub settings (if applicable)
```

---

## Moving Data to a Different Path

If you want to store data in a different location (e.g., `/mnt/data/ibkr-dash`):

### Option 1: Change `IBKR_DATA_DIR`

```bash
# Create target directory
mkdir -p /mnt/data/ibkr-dash/data

# Move data
mv /opt/ibkr-dash/data/* /mnt/data/ibkr-dash/data/

# Create .env file
echo "IBKR_DATA_DIR=/mnt/data/ibkr-dash/data" > /opt/ibkr-dash/.env

# Restart
cd /opt/ibkr-dash
docker compose up -d
```

### Option 2: Symlink

```bash
# Move data
mv /opt/ibkr-dash/data /mnt/data/ibkr-dash-data

# Create symlink
ln -s /mnt/data/ibkr-dash-data /opt/ibkr-dash/data

# Restart (no config change needed)
cd /opt/ibkr-dash
docker compose up -d
```

---

## Disaster Recovery

### Disk Full

```bash
# Check disk usage
df -h /opt/ibkr-dash

# Check data directory size
du -sh /opt/ibkr-dash/data/*

# Clean old flex exports (can re-download)
rm /opt/ibkr-dash/data/flex_exports/*.xml

# VACUUM database to reclaim space
docker compose exec backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/backend/data/ibkr_dash.db')
conn.execute('VACUUM')
conn.close()
"
```

### Corrupted Database

```bash
# Stop containers
docker compose stop backend worker

# Check integrity
sqlite3 /opt/ibkr-dash/data/ibkr_dash.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp /opt/backups/ibkr-dash/ibkr_dash_latest.db /opt/ibkr-dash/data/ibkr_dash.db

# Restart
docker compose start backend worker
```

### Config Lost

If `config.json` is lost, the system recreates it with defaults on next startup. You'll need to reconfigure via Admin Settings. To prevent this, always include `config.json` in backups.

---

## Quick Reference

```bash
# Backup everything
tar czf backup.tar.gz -C /opt/ibkr-dash data/

# Backup database only (hot copy)
docker compose exec backend python3 -c "
import sqlite3
s=sqlite3.connect('/app/backend/data/ibkr_dash.db')
d=sqlite3.connect('/tmp/b.db')
s.backup(d);s.close();d.close()
" && docker compose cp backend:/tmp/b.db ./backup.db

# Restore database
docker compose stop backend worker
cp backup.db /opt/ibkr-dash/data/ibkr_dash.db
docker compose start backend worker

# Check database size
ls -lh /opt/ibkr-dash/data/ibkr_dash.db

# View data directory
ls -la /opt/ibkr-dash/data/
```
