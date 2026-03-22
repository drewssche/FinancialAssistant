#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/pytest" ]]; then
  echo "Virtualenv pytest not found at .venv/bin/pytest"
  exit 1
fi

RUN_API="${RUN_API:-1}"
RUN_E2E="${RUN_E2E:-0}"

run_pytest() {
  local label="$1"
  shift
  echo
  echo "==> $label"
  ./.venv/bin/pytest -q "$@"
}

echo "Running critical regression matrix..."

if [[ "$RUN_API" == "1" ]]; then
  run_pytest \
    "API: dashboard, operations, debts, plans, request budgets" \
    tests/api/test_request_budgets_api.py::test_request_budget_open_dashboard \
    tests/api/test_request_budgets_api.py::test_request_budget_create_operation_refresh_flow \
    tests/api/test_request_budgets_api.py::test_request_budget_debts_search \
    tests/api/test_operations_api.py::test_operations_crud_and_filters \
    tests/api/test_dashboard_api.py::test_dashboard_summary_cache_is_invalidated_after_operation_update_and_delete \
    tests/api/test_dashboard_api.py::test_dashboard_summary_cache_is_invalidated_after_debt_mutations \
    tests/api/test_debts_api.py::test_debts_create_and_list_cards \
    tests/api/test_debts_api.py::test_debts_repayment_and_close_card \
    tests/api/test_debts_api.py::test_debts_update_and_delete \
    tests/api/test_plans_api.py::test_plans_crud_confirm_and_history
fi

if [[ "$RUN_E2E" == "1" ]]; then
  run_pytest \
    "E2E: auth, operation create/edit, debts, plans" \
    tests/e2e/test_auth_login_ui_e2e.py::test_login_screen_prefers_mini_app_copy_and_hides_manual_button_without_initdata \
    tests/e2e/test_auth_login_ui_e2e.py::test_login_keeps_pending_and_rejected_users_out_of_workspace \
    tests/e2e/test_create_operation_receipt_amount_autofill_e2e.py::test_create_operation_allows_receipt_only_amount \
    tests/e2e/test_receipt_picker_store_scope_e2e.py::test_receipt_picker_store_scoped_and_optimistic_create \
    tests/e2e/test_debts_flow_e2e.py::test_create_debt_from_operation_modal \
    tests/e2e/test_debts_flow_e2e.py::test_repayment_moves_debt_to_closed \
    tests/e2e/test_debts_flow_e2e.py::test_edit_and_delete_debt \
    tests/e2e/test_plans_ui_e2e.py::test_plans_ui_creates_weekly_multiweekday_plan \
    tests/e2e/test_plans_ui_e2e.py::test_plans_ui_creates_month_end_plan_and_confirms_to_history \
    -m e2e
else
  echo
  echo "==> E2E: skipped (set RUN_E2E=1 when browser/socket runtime is available)"
fi

echo
echo "Critical regression matrix passed."
