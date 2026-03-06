#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
TOKEN="${TOKEN:-}"
REQUIRE_HEALTH="${REQUIRE_HEALTH:-0}"
RUN_E2E="${RUN_E2E:-0}"

echo "[1/3] Full test baseline"
if [[ "${RUN_E2E}" == "1" ]]; then
  ./.venv/bin/pytest -q
else
  ./.venv/bin/pytest -q -m "not e2e"
  echo "Skipped e2e tests by default (set RUN_E2E=1 to include)."
fi

echo "[2/3] Request budget guard"
./.venv/bin/pytest -q tests/api/test_request_budgets_api.py

echo "[3/3] Lightweight health check"
if [[ -n "${TOKEN}" ]]; then
  BASE_URL="${BASE_URL}" TOKEN="${TOKEN}" ./scripts/health_check.sh
elif [[ "${REQUIRE_HEALTH}" == "1" ]]; then
  echo "TOKEN is required when REQUIRE_HEALTH=1"
  exit 2
else
  echo "Skipping health check (TOKEN is not set)."
  echo "Run with TOKEN=... to include API runtime checks."
fi

echo "Release check completed."
