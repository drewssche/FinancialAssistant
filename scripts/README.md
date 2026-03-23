# Scripts

## Request Scenarios Metrics

Use this script to measure backend request counts per user action and cache/latency metrics.

Command:

```bash
PYTHONPATH=. ./.venv/bin/python scripts/measure_request_scenarios.py
```

What it does:
- boots an isolated in-memory test app
- seeds representative operations/debts data
- runs user-like scenarios:
  - open dashboard
  - operations search
  - create operation + refresh
  - debts search
  - section switch without frontend cache (baseline)
  - section switch with frontend TTL cache policy (operations/debts/categories)
- prints a table with:
  - request totals per endpoint (`METHOD /api/v1/...`)
  - cache hit ratio
  - summary latency p50/p95

How to read output:
- request totals show backend cost of a user action
- cache hit ratio should be high for repeated dashboard summary reads
- p95 highlights tail latency regressions

Related automated guard:
- `tests/api/test_request_budgets_api.py`

## Release Check (One Command)

Run:

```bash
./scripts/release_check.sh
```

Default mode runs non-e2e suite only (`-m "not e2e"`).  
Include e2e when environment supports it:

```bash
RUN_E2E=1 ./scripts/release_check.sh
```

Include runtime API checks:

```bash
TOKEN=... BASE_URL=http://localhost:8001 ./scripts/release_check.sh
```

Strict mode:

```bash
REQUIRE_HEALTH=1 TOKEN=... BASE_URL=http://localhost:8001 ./scripts/release_check.sh
```

## Weekly Health Check (Lightweight Ops)

For small installations (`~2-3` active users), run this once a week:

```bash
TOKEN=... BASE_URL=http://localhost:8001 ./scripts/health_check.sh
```

What it checks:
- `GET /health` returns `{"status":"ok"}`
- `GET /api/v1/dashboard/summary` is available for authenticated user
- `GET /api/v1/dashboard/summary/metrics` returns valid telemetry and basic thresholds

Optional thresholds via env:
- `MAX_P95_MS` (default `250`)
- `MIN_CACHE_HIT_RATIO` (default `0.0`)
- `MAX_SUMMARY_GET_TOTAL` (default `0`, disabled)

## Telegram Admin Bot

Polling worker for admin access notifications and inline `Approve` / `Reject` actions:

```bash
PYTHONPATH=. ./.venv/bin/python scripts/run_telegram_admin_bot.py
```

Required env:
- `TELEGRAM_BOT_TOKEN`
- `ADMIN_TELEGRAM_IDS`

Optional env:
- `TELEGRAM_BOT_POLL_TIMEOUT_SECONDS` (default `25`)
- `TELEGRAM_BOT_RETRY_DELAY_SECONDS` (default `2`)
- `TELEGRAM_PLAN_REMINDER_SCAN_INTERVAL_SECONDS` (default `60`, effective minimum `15`)

Notes:
- the same worker is started by the Compose `bot` service
- admins must open the bot and press `Start` once before Telegram allows outbound notifications
- the same worker also sends due/overdue plan reminders to users who enabled `plans.reminders_enabled`
- when Redis is unavailable, the worker now sends an admin-only advisory about `local fallback` mode with a built-in `12h` cooldown and health-check guidance
