# Financial Assistant

Web-first financial assistant (income/expense tracking) with architecture ready for Telegram Mini App integration.

## Stack
- FastAPI
- PostgreSQL
- Redis (optional runtime cache)
- SQLAlchemy + Alembic
- Docker Compose

## Quick Start
1. Copy `.env.example` to `.env`
2. Run `docker compose up --build -d`
3. App container applies migrations automatically on startup (`alembic upgrade head`)
4. Open API docs: `http://localhost:8001/docs`
5. Open Web UI: `http://localhost:8001/`

Optional cache profile:
- lightweight VPS mode can run without Redis; app falls back to in-process cache
- to enable Redis explicitly: `docker compose --profile cache up --build -d`

For production auth mode set `APP_ENV=production` and configure:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_BOT_POLL_TIMEOUT_SECONDS` (optional; default `25`)
- `TELEGRAM_BOT_RETRY_DELAY_SECONDS` (optional; default `2`)
- `TELEGRAM_PLAN_REMINDER_SCAN_INTERVAL_SECONDS` (optional; default `60`, effective minimum `15`)
- `ADMIN_TELEGRAM_IDS` (comma-separated Telegram IDs of admins; these IDs are auto-approved on first login)

Production startup fails fast if critical config is unsafe or incomplete:
- `APP_SECRET_KEY` must not stay `change_me`
- `TELEGRAM_BOT_TOKEN` must not stay `change_me`
- `ADMIN_TELEGRAM_IDS` must include at least one admin

## Ports
- App API: `8001 -> 8000` (container)
- Postgres and optional Redis are internal-only in current Compose setup and are not published to the host by default

## Access Approval
- New users are created with `pending` status.
- Only `approved` users can access data sections.
- `rejected` users cannot use the service until status is changed by admin.
- Users from `ADMIN_TELEGRAM_IDS` are approved automatically and see the admin section immediately after Telegram login.

## First Use (Production Mode)
1. Start services and run migrations.
2. Open app from Telegram Mini App (WebApp) so `initData` is available.
3. Login via Telegram.
4. Admin opens `Админ` section:
   - `Ожидают` -> `Approve` for allowed users
   - optional `Reject` or `Удалить` (deletes user with all DB data)
5. Approved users re-login and can use the app.

## Telegram Mini App Note
Telegram Mini App readiness is broader than responsive layout only. In addition to mobile screen adaptation, production-ready Mini App support requires:
- Telegram WebApp auth/runtime handling (`initData`, viewport behavior)
- touch-first interactions without hover dependency
- safe-area and mobile keyboard-safe layouts

## Browser Use
- The app UI can be opened in a regular browser.
- In Telegram Mini App, login uses Telegram WebApp `initData`.
- In a regular browser, login can use Telegram Login Widget when `TELEGRAM_BOT_USERNAME` is configured.
- Both browser and Mini App login paths resolve to the same backend user model and access rules.
- Browser widget login also requires the correct domain/hostname to be configured for the bot on Telegram side; this must be verified manually during production setup.

## Admin Access Notifications
- New non-admin users are created with `pending` status.
- If bot polling service is running, admins from `ADMIN_TELEGRAM_IDS` receive compact Telegram notifications for new pending users.
- Notification message includes inline `Approve` / `Reject` buttons.
- Admin must open the bot and press `Start` once, otherwise Telegram may reject outbound bot messages to that admin chat.
- In local/dev or VPS Compose setup this polling worker is started by the default `bot` service (`python scripts/run_telegram_admin_bot.py`).

## Domain and HTTPS Basics
- Yes, you can prepare the domain yourself on your VPS.
- Typical setup is:
  1. buy or use an existing domain
  2. create an `A` record pointing the domain/subdomain to your VPS public IP
  3. run a reverse proxy (`nginx`)
  4. issue a free TLS certificate with `Let's Encrypt`
- Telegram Mini App in production should be opened over `https://`, so valid HTTPS is effectively required.
- If you do not want to buy a domain yet, the practical alternative is a free hostname/subdomain service that points to your VPS. A bare VPS IP alone is not a good production path for Telegram login + HTTPS.

## VPS Baseline
For a small production rollout (`up to ~5 users`), a VPS with `1 vCPU / 2 GB RAM` is sufficient for this project when running:
- app with one Uvicorn process
- PostgreSQL with conservative memory settings
- optional Redis as lightweight cache only when you want cross-process cache persistence
- Docker Compose without dev reload/watch mode

Recommended small-VPS mode:
- `docker compose up --build -d`
- this starts `app`, `bot`, `db`
- Redis stays off unless you start profile `cache`

Full runtime with Redis:
- `docker compose --profile cache up --build -d`

## UI E2E Regression Test (Chip Picker)
Added browser regression test for category chip duplication in operation modal search:

- `tests/e2e/test_chip_picker_no_duplicates_e2e.py`

Run locally:

1. `./.venv/bin/pip install -r requirements-e2e.txt`
2. `./.venv/bin/python -m playwright install chromium`
3. `./.venv/bin/pytest -q tests/e2e/test_chip_picker_no_duplicates_e2e.py`
4. Shortcut: `./scripts/test_ui.sh`

Notes:
- Test uses mocked API responses via Playwright `route`, so it is deterministic and does not require running backend.
- In CI/local environment without Playwright/Chromium it will be skipped with a clear reason.

## Current Scope
- Telegram auth flow
- Browser Telegram login fallback with server-side availability gating (`/api/v1/auth/public-config`)
- Full CRUD for operations, categories/groups, debts and plans
- Dashboard summary (including debt and currency KPI fields) + summary metrics endpoint
- Analytics endpoints for calendar, year calendar, trend and highlights views
- Money-flow views over operations, debts and FX events
- Receipt line items in operations (`receipt_items`, discrepancy support)
- Receipt line items can optionally store their own `category_id`
- Reusable item templates catalog + price history endpoints
- Category-level `include_in_statistics` flag for analytics/breakdown control
- Currency/FX module: tracked currencies, FX trades, current/history rates, dashboard currency panel, analytics currency tab and Telegram currency notifications
- Multi-currency operations, plans and debts with base-currency conversion snapshots or live equivalents where appropriate
- Plan and debt due-date reminders through the Telegram bot runtime
- Persisted user preferences (server + local fallback)
- API and UI regression suite (API + Playwright e2e)

## Notes
Telegram `initData` signature and `auth_date` freshness validation are implemented in `app/core/telegram_auth.py`.
