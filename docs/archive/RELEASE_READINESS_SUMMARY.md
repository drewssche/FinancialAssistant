# Release Readiness Summary

Updated: 2026-03-08

## Covered by Regression Tests

- Auth and access-state behavior:
  - Mini App login
  - browser login availability gating
  - `pending` / `rejected` handling
  - session restore behavior
- Mobile modal safety:
  - operations create/edit
  - debts repayment/history
  - categories create/edit
  - item catalog create/source
- Mobile batch flows:
  - batch operations
  - batch categories
  - batch item templates
- Mobile analytics:
  - month calendar horizontal scroll reachability
  - year-to-month navigation
  - day-to-operations drilldown
- Production auth/config hardening:
  - browser Telegram auth disabled without `TELEGRAM_BOT_USERNAME`
  - production config gate for secret/token/admin envs

## Key E2E Files

- `tests/e2e/test_auth_login_ui_e2e.py`
- `tests/e2e/test_receipt_picker_store_scope_e2e.py`
- `tests/e2e/test_debts_flow_e2e.py`
- `tests/e2e/test_chip_picker_no_duplicates_e2e.py`
- `tests/e2e/test_batch_create_operations_e2e.py`
- `tests/e2e/test_bulk_import_sections_e2e.py`
- `tests/e2e/test_analytics_mobile_e2e.py`

## Still Requires Manual Release Check

- Open the app inside a real Telegram Mini App container, not only desktop/mobile browser emulation
- Verify login, reopen, and session restore on a physical phone
- Verify keyboard behavior in the longest real forms on iPhone/Android
- Verify safe-area behavior on real devices with Telegram chrome
- Verify production env values on target host:
  - `APP_ENV=production`
  - valid `APP_SECRET_KEY`
  - valid `TELEGRAM_BOT_TOKEN`
  - non-empty `ADMIN_TELEGRAM_IDS`
- Verify approval flow with a real new Telegram user:
  - `pending`
  - `approved`
  - `rejected`

## Release Decision Rule

Release is reasonable when:

- non-e2e suite is green
- targeted mobile e2e suite is green
- production config gate passes
- manual Telegram Mini App smoke pass is successful on at least one real device

Do not release when:

- Telegram login works only in standalone browser
- any primary CTA is hidden by keyboard, footer, or safe-area
- approval flow was not rechecked against the real bot/runtime
