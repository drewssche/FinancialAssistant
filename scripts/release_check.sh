#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
TOKEN="${TOKEN:-}"
REQUIRE_HEALTH="${REQUIRE_HEALTH:-0}"
RUN_E2E="${RUN_E2E:-0}"

run_pytest() {
  local label="$1"
  shift
  echo
  echo "==> ${label}"
  ./.venv/bin/pytest -q "$@"
}

echo "[1/3] Full test baseline"
if [[ "${RUN_E2E}" == "1" ]]; then
  run_pytest "Unit/API tests" -m "not e2e"
  run_pytest "E2E: auth" tests/e2e/test_auth_login_ui_e2e.py -m e2e
  run_pytest "E2E: operations money flow" tests/e2e/test_operations_money_flow_e2e.py -m e2e
  run_pytest "E2E: analytics" \
    tests/e2e/test_analytics_mobile_e2e.py \
    tests/e2e/test_analytics_trend_cashflow_e2e.py \
    -m e2e
  run_pytest "E2E: bulk and batch forms" \
    tests/e2e/test_bulk_import_sections_e2e.py \
    tests/e2e/test_batch_create_operations_e2e.py \
    -m e2e
  run_pytest "E2E: mobile shell" tests/e2e/test_mobile_shell_cards_e2e.py -m e2e
  run_pytest "E2E: debts" tests/e2e/test_debts_flow_e2e.py -m e2e
  run_pytest "E2E: plans" tests/e2e/test_plans_ui_e2e.py -m e2e
  run_pytest "E2E: currency" \
    tests/e2e/test_currency_trade_modal_e2e.py \
    tests/e2e/test_currency_trade_modal_live_calc_e2e.py \
    tests/e2e/test_currency_trades_pagination_e2e.py \
    -m e2e
  run_pytest "E2E: receipt and category pickers" \
    tests/e2e/test_receipt_picker_store_scope_e2e.py \
    tests/e2e/test_chip_picker_no_duplicates_e2e.py \
    tests/e2e/test_create_operation_receipt_amount_autofill_e2e.py \
    -m e2e
  run_pytest "E2E: preferences and sort presets (isolated sync Playwright)" \
    tests/e2e/test_sort_preset_persistence_e2e.py \
    -m e2e
else
  run_pytest "Unit/API tests" -m "not e2e"
  echo "Skipped e2e tests by default (set RUN_E2E=1 to include)."
fi

echo "[2/3] Request budget guard"
run_pytest "Request budget guard" tests/api/test_request_budgets_api.py

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
