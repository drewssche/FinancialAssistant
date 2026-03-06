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
