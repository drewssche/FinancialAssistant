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
2. Run `docker compose up --build`
3. Run migrations inside app container:
   - `alembic upgrade head`
4. Open API docs: `http://localhost:8000/docs`

## Current Scope
- API scaffold and schema foundations
- Telegram-first auth endpoint scaffold
- Authenticated `GET /api/v1/users/me` profile endpoint
- Dashboard, operations, categories, preferences endpoints
- Documentation for product, architecture, UX and engineering rules

## Notes
Telegram `initData` signature and `auth_date` freshness validation are implemented in `app/core/telegram_auth.py`.
