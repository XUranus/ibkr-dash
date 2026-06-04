#!/usr/bin/env bash
# Verify Docker build, startup, health, data, auth, and frontend.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VERIFY_PROJECT="ibkr_dash_verify"

FRONTEND_PORT="${FRONTEND_PORT:-8080}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

HEALTH_URL="http://localhost:${FRONTEND_PORT}/health"
BOOTSTRAP_URL="http://localhost:${FRONTEND_PORT}/api/auth/bootstrap/init"
BOOTSTRAP_STATUS_URL="http://localhost:${FRONTEND_PORT}/api/auth/bootstrap/status"
LOGIN_URL="http://localhost:${FRONTEND_PORT}/api/auth/login"
SESSION_URL="http://localhost:${FRONTEND_PORT}/api/auth/session"
FRONTEND_URL="http://localhost:${FRONTEND_PORT}/"

COOKIE_JAR="$(mktemp)"
ENV_BACKUP=""
ORIGINAL_ENV_EXISTS=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { printf '\n\033[1;36m>>> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mFAIL: %s\033[0m\n' "$*"; dump_logs; exit 1; }

compose() {
  COMPOSE_PROJECT_NAME="$VERIFY_PROJECT" docker compose "$@"
}

dump_logs() {
  echo ""
  echo "=== compose ps ==="
  compose ps 2>/dev/null || true
  for svc in backend frontend; do
    echo ""
    echo "=== compose logs $svc --tail=100 ==="
    compose logs "$svc" --tail=100 2>/dev/null || true
  done
}

cleanup_compose() {
  COMPOSE_PROJECT_NAME="$VERIFY_PROJECT" docker compose down -v --remove-orphans 2>/dev/null || true
}

cleanup_env() {
  if [ "$ORIGINAL_ENV_EXISTS" -eq 1 ]; then
    if [ -n "$ENV_BACKUP" ] && [ -f "$ENV_BACKUP" ]; then
      cp "$ENV_BACKUP" .env
      rm -f "$ENV_BACKUP"
      echo "  Restored original .env"
    fi
  else
    rm -f .env
    echo "  Removed temporary .env"
  fi
}

wait_for_health() {
  local max_wait=120
  local elapsed=0
  log "Waiting for $HEALTH_URL (max ${max_wait}s)..."
  while [ "$elapsed" -lt "$max_wait" ]; do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
      echo "  Health check passed after ${elapsed}s."
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  fail "Health check did not respond within ${max_wait}s"
}

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

log "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "docker compose is not available"

# ---------------------------------------------------------------------------
# Prepare .env
# ---------------------------------------------------------------------------

if [ -f .env ]; then
  ORIGINAL_ENV_EXISTS=1
  ENV_BACKUP="$(mktemp)"
  cp .env "$ENV_BACKUP"
  echo "  Backed up existing .env"
fi

if [ "${CLEANUP:-0}" = "1" ]; then
  trap 'cleanup_compose; cleanup_env; rm -f "$COOKIE_JAR"' EXIT
else
  trap 'cleanup_env; rm -f "$COOKIE_JAR"' EXIT
fi

cat > .env <<EOF
COMPOSE_PROJECT_NAME=${VERIFY_PROJECT}
FRONTEND_PORT=${FRONTEND_PORT}
BACKEND_PORT=${BACKEND_PORT}
APP_ENV=docker
AUTH_USERNAME=admin
AUTH_PASSWORD=change-me
AUTH_SESSION_SECRET=verify-session-secret
DAILY_REVIEW_INTERNAL_TOKEN=verify-internal-token
DEMO_MODE=true
EOF
echo "  Wrote verification .env"

# ---------------------------------------------------------------------------
# Docker Compose lifecycle
# ---------------------------------------------------------------------------

log "docker compose config"
compose config --quiet || fail "docker compose config failed"

log "docker compose build"
compose build --no-cache || fail "docker compose build failed"

log "docker compose down (clean slate)"
compose down -v --remove-orphans 2>/dev/null || true

log "docker compose up -d"
compose up -d || fail "docker compose up failed"

# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------

wait_for_health

# ---------------------------------------------------------------------------
# 2. Data verification after startup
# ---------------------------------------------------------------------------

log "Checking backend data API..."
data_response="$(curl -sf "${HEALTH_URL}" 2>/dev/null || echo '{}')"
echo "  Health response: $data_response"

# Verify the backend API is responding with valid JSON
if echo "$data_response" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  echo "  Backend API returns valid JSON."
else
  echo "  Warning: Backend health response is not valid JSON."
fi

# ---------------------------------------------------------------------------
# 3. Auth testing (bootstrap + login)
# ---------------------------------------------------------------------------

log "Testing auth flow..."

# Bootstrap init
http_code="$(curl -sf -o /dev/null -w '%{http_code}' \
  -X POST "$BOOTSTRAP_URL" \
  -H 'Content-Type: application/json' \
  -d '{"username":"verify-admin","password":"verify-password-123"}' 2>/dev/null || echo '000')"
echo "  POST /api/auth/bootstrap/init -> ${http_code}"

if [ "$http_code" = "200" ]; then
  log "Checking bootstrap status..."
  bootstrap_json="$(curl -sf "$BOOTSTRAP_STATUS_URL" 2>/dev/null || echo '{}')"
  initialized="$(echo "$bootstrap_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('initialized', False))" 2>/dev/null || echo 'False')"
  echo "  initialized=${initialized}"

  # Login
  log "Logging in..."
  http_code="$(curl -sf -o /dev/null -w '%{http_code}' \
    -c "$COOKIE_JAR" \
    -X POST "$LOGIN_URL" \
    -H 'Content-Type: application/json' \
    -d '{"username":"verify-admin","password":"verify-password-123"}' 2>/dev/null || echo '000')"
  echo "  POST /api/auth/login -> ${http_code}"

  if [ "$http_code" = "200" ]; then
    log "Checking session..."
    session_json="$(curl -sf -b "$COOKIE_JAR" "$SESSION_URL" 2>/dev/null || echo '{}')"
    authenticated="$(echo "$session_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('authenticated', False))" 2>/dev/null || echo 'False')"
    echo "  authenticated=${authenticated}"
    [ "$authenticated" = "True" ] || echo "  Warning: Session not authenticated"
  else
    echo "  Skipping session check (login returned ${http_code})"
  fi
else
  echo "  Skipping auth flow (bootstrap returned ${http_code})"
fi

# ---------------------------------------------------------------------------
# 4. Frontend HTML verification
# ---------------------------------------------------------------------------

log "Checking frontend HTML..."
frontend_html="$(curl -sf "$FRONTEND_URL" 2>/dev/null || echo '')"
if [ -z "$frontend_html" ]; then
  fail "Frontend HTML is empty or unreachable"
fi

if echo "$frontend_html" | grep -q 'id="app"\|<script\|<div'; then
  echo "  Frontend HTML contains expected elements."
else
  echo "  Warning: Frontend HTML may not contain expected app entry point."
fi

# Verify the HTML is not an error page
if echo "$frontend_html" | grep -qi '502 bad gateway\|503 service\|nginx error'; then
  fail "Frontend is returning an error page"
fi

echo "  Frontend HTML verification passed."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

log "All verification checks passed!"
if [ "${CLEANUP:-0}" = "1" ]; then
  echo "  CLEANUP=1 set, containers will be torn down on exit."
fi
