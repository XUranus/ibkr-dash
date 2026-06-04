#!/usr/bin/env bash
# Pre-release safety checks.
# Scans the git repository for leaked secrets and runs test suites.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

FOUND=0

# ---------------------------------------------------------------------------
# Secret-leak scanner
# ---------------------------------------------------------------------------

check() {
  local pattern="$1"
  local label="$2"
  local matches
  matches="$(git grep -n --untracked "$pattern" -- \
    ':!*.svg' ':!*.png' ':!*.jpg' ':!*.lock' \
    ':!scripts/check_release_safety.sh' \
    ':!.env.example' \
    ':!SECURITY.md' \
    ':!README.md' \
    ':!CONTRIBUTING.md' \
    ':!AGENTS.md' \
    ':!CLAUDE.md' \
    2>/dev/null || true)"

  if [ -n "$matches" ]; then
    local filtered
    filtered="$(echo "$matches" | grep -iv 'change-me\|example\|placeholder\|dummy\|mock\|verify\|test\|fake\|sample\|#.*=' || true)"
    # Further filter: exclude lines that are clearly code (object access, assignments to variables, etc.)
    if [ -n "$filtered" ]; then
      filtered="$(echo "$filtered" | grep -v '\.\(api_key\|access_token\|refresh_token\)\b' | grep -v 'str(item\.get\|payload\.\|provider\.\|state\.\|self\.\|data\.\|token_data\|reg_payload\|token_payload' || true)"
    fi
    if [ -n "$filtered" ]; then
      echo ""
      echo "SUSPECT [$label]:"
      echo "$filtered"
      FOUND=1
    fi
  fi
}

check_file_pattern() {
  local glob="$1"
  local label="$2"
  if git ls-files -- "$glob" 2>/dev/null | grep -q .; then
    echo ""
    echo "SUSPECT [$label]:"
    git ls-files -- "$glob"
    FOUND=1
  fi
}

log() { printf '\n\033[1;36m>>> %s\033[0m\n' "$*"; }

log "Scanning for sensitive patterns..."

check 'FLEX_TOKEN=[^ ]' "IBKR Flex Token"
check 'FLEX_QUERY_ID_DAILY=[0-9]' "IBKR Query ID (hardcoded)"
check 'sk-[a-zA-Z0-9]\{20,\}' "OpenAI-style API Key"
check 'OPENAI_API_KEY=[^ ]' "OpenAI API Key (hardcoded)"
check 'LONGBRIDGE_OPENAPI_OAUTH_CLIENT_ID=[^ ]' "LongBridge Client ID (hardcoded)"
check 'LONGBRIDGE_ACCESS_TOKEN=[^ ]' "LongBridge Access Token (hardcoded)"
check 'AUTH_PASSWORD=[^ ]' "Auth Password (hardcoded)"
check 'REMOTE_SSH_PASSWORD=' "SSH password"
check 'DAILY_REVIEW_INTERNAL_TOKEN=[^ ]' "Internal Token (hardcoded)"
check 'gehaoyuan\.top' "Private domain"
check '/root/ibkr_show' "Private server path"
check '/root/ibkr_dash' "Private server path"

check_file_pattern '*/data/config/*.json' "tracked config JSON"

# ---------------------------------------------------------------------------
# Run test suites
# ---------------------------------------------------------------------------

log "Running backend tests..."
(cd ibkr_dash_backend && python -m pytest tests/ -v --tb=short 2>&1) || {
  echo ""
  printf '\033[1;31m>>> backend tests FAILED\033[0m\n'
  FOUND=1
}

log "Running worker tests..."
(cd ibkr_dash_worker && python -m pytest tests/ -v --tb=short 2>&1) || {
  echo ""
  printf '\033[1;31m>>> worker tests FAILED\033[0m\n'
  FOUND=1
}

log "Checking frontend build..."
(cd ibkr_dash_frontend && npm run build 2>&1) || {
  echo ""
  printf '\033[1;31m>>> frontend build FAILED\033[0m\n'
  FOUND=1
}

# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------

echo ""
if [ "$FOUND" -eq 0 ]; then
  printf '\033[1;32m>>> release safety check passed\033[0m\n'
  exit 0
else
  printf '\033[1;31m>>> release safety check FAILED -- review suspects above\033[0m\n'
  exit 1
fi
