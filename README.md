# Financial Assistant

Web-first financial assistant (income/expense tracking) with architecture ready for Telegram Mini App integration.

## Stack
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy + Alembic
- Docker Compose

## Quick Start
1. Copy `.env.example` to `.env`
2. Run `docker compose up --build -d`
3. Run migrations inside app container:
   - `docker compose exec app sh -lc 'cd /app && PYTHONPATH=/app alembic upgrade head'`
4. Open API docs: `http://localhost:8001/docs`
5. Open Dev UI: `http://localhost:8001/`

## Ports
- App API: `8001 -> 8000` (container)
- Postgres: `5433 -> 5432` (container)
- Redis: `6380 -> 6379` (container)

## Local Dev Login (Telegram Auth)
If you need a quick local token without opening Telegram Mini App, use:

1. `python3 scripts/dev_login.py`
2. Copy token from output
3. Call protected endpoint:
   - `curl -H "Authorization: Bearer <TOKEN>" http://localhost:8001/api/v1/users/me`

Optional args:
- `--api-url http://localhost:8001`
- `--telegram-id 100001`
- `--first-name Dev`
- `--username dev_user`
- `--bot-token <TOKEN>`

### One-click Dev Button
`http://localhost:8001/` includes a `Войти (Dev)` button using `POST /api/v1/auth/dev`.
This endpoint is allowed only when `APP_ENV != production`.

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
- API scaffold and schema foundations
- Telegram-first auth endpoint scaffold
- Authenticated `GET /api/v1/users/me` profile endpoint
- Dashboard, operations, categories, preferences endpoints
- Documentation for product, architecture, UX and engineering rules

## Notes
Telegram `initData` signature and `auth_date` freshness validation are implemented in `app/core/telegram_auth.py`.
