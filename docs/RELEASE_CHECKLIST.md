# Release Checklist

Use this checklist before each release/deploy.

## One-Command Run
Preferred:

```bash
./scripts/release_check.sh
```

Note:
- by default this runs non-e2e tests (`-m "not e2e"`)
- include e2e explicitly when environment supports browser/socket runtime:

```bash
RUN_E2E=1 ./scripts/release_check.sh
```

With runtime API health check included:

```bash
TOKEN=... BASE_URL=http://localhost:8001 ./scripts/release_check.sh
```

Strict mode (fail if TOKEN is missing):

```bash
REQUIRE_HEALTH=1 TOKEN=... BASE_URL=http://localhost:8001 ./scripts/release_check.sh
```

## 1. Test Baseline
Run full test suite:

```bash
./.venv/bin/pytest -q
```

Expected:
- all tests pass
- no unexpected warnings/regressions

## 2. Request Budget Guard
Budgets are defined in:
- `docs/REQUEST_BUDGETS.md`

Automated gate:
- `tests/api/test_request_budgets_api.py`

Run directly (optional explicit check):

```bash
./.venv/bin/pytest -q tests/api/test_request_budgets_api.py
```

Expected:
- all request-budget checks pass

## 3. Lightweight Health Check
For current scale (`~2-3` users), run weekly and before release:

```bash
TOKEN=... BASE_URL=http://localhost:8001 ./scripts/health_check.sh
```

Expected:
- `/health` is `ok`
- `dashboard/summary` and `dashboard/summary/metrics` are reachable
- threshold checks in script pass (`p95`, `cache_hit_ratio`, optional request-total cap)

## 4. Production Config Gate
Before any production deploy, verify:
- `APP_ENV=production`
- `APP_SECRET_KEY` is set and is not the default placeholder
- `TELEGRAM_BOT_TOKEN` is set correctly
- `ADMIN_TELEGRAM_IDS` contains actual admin Telegram IDs and owner/admin IDs are expected to auto-approve
- no alternative non-Telegram login entrypoints remain enabled

Expected:
- Telegram auth is the only active sign-in path in production
- admin approval flow works for a newly created `pending` user
- non-approved users cannot access workspace sections

## 5. Telegram Mini App Readiness Gate
Before exposing the app inside Telegram WebApp, verify:
- login works from Telegram Mini App container, not only from standalone browser
- key screens are usable on narrow mobile viewport (`320-430px`)
- no critical action depends on hover-only UI
- main forms remain usable with mobile keyboard open
- safe-area/viewport shifts do not hide primary CTA or break layout
- targeted mobile e2e regression suite passes:
  - `tests/e2e/test_auth_login_ui_e2e.py`
  - `tests/e2e/test_receipt_picker_store_scope_e2e.py`
  - `tests/e2e/test_debts_flow_e2e.py`
  - `tests/e2e/test_chip_picker_no_duplicates_e2e.py`
  - `tests/e2e/test_batch_create_operations_e2e.py`
  - `tests/e2e/test_bulk_import_sections_e2e.py`
  - `tests/e2e/test_analytics_mobile_e2e.py`

Expected:
- app is usable end-to-end on a real phone or equivalent mobile emulation
- auth/session restore behaves correctly after reopening the Mini App
- regression suite covers auth/access states, modal CTA reachability, batch preview reachability and analytics mobile navigation
