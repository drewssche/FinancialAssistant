# Architecture

## High-Level
- Backend: FastAPI
- DB: PostgreSQL
- Migrations: Alembic
- Cache/queue-ready: Redis (optional; app has local fallback for dashboard cache)
- Runtime: Docker Compose

## Layering
- `api`: transport and validation
- `services`: business workflows
- `repositories`: DB access patterns
- `db/models`: persistence schema
- `schemas`: API contracts

## Auth Model
- Provider-first identities (`auth_identities`)
- Single internal user profile (`users`)
- Telegram provider in MVP-1
- Google provider planned with same identity model
- Access control statuses for users:
- `pending` (no product access yet)
- `approved` (full access)
- `rejected` (access denied)
- Admin users are resolved from env (`ADMIN_TELEGRAM_IDS`) via Telegram identity mapping
- Admin-only API surface: `/api/v1/admin/*`
- In production mode, primary auth flow is Telegram WebApp `initData` verification
- Optional browser Telegram auth is exposed via `/api/v1/auth/telegram/browser` only when `TELEGRAM_BOT_USERNAME` is configured; availability is advertised by `/api/v1/auth/public-config`

## Shared API for Multi-Client
One API serves both Web and Telegram Mini App clients.
Client-specific logic stays at UI layer; domain logic stays in backend services.

## Admin Access Workflow (Implemented Baseline)
- New users are created with `pending` status by default.
- Admin can:
- approve (`pending -> approved`)
- reject (`pending/approved -> rejected`)
- hard-delete user with all related records
- Hard-delete is centralized in `user_cleanup_service` and reused by:
- `DELETE /api/v1/users/me`
- `DELETE /api/v1/admin/users/{user_id}`

## Operations Receipt Extension (MVP)
- Add receipt-detail entities linked to operation:
- `operation_receipt_items` (snapshot line items inside operation)
- `operation_item_templates` (reusable chip catalog per user)
- `operation_item_prices` (immutable price history per template)
- Service-level rules:
- operation amount is source-of-truth for totals, but receipt total/discrepancy are computed and exposed
- save is allowed with discrepancy (warning use-case)
- template price history appends on each use; old prices are preserved
- template resolution for receipt items is batch-oriented (prefetch by `(name_ci, source_ci)` + bulk price inserts) to avoid N+1 query growth on long receipts
- receipt line items may carry their own optional `category_id`

## Debt Module (Implemented MVP Baseline)
- Dedicated domain objects (separate from category semantics):
- debt counterparty card (`debt_counterparties`)
- debt entries (`debts`) with principal, dates, direction (`lend`/`borrow`)
- repayment entries (`debt_repayments`) linked to debt entry
- Aggregation rules in service layer:
- card outstanding = sum(principal) - sum(repayments)
- card status (`active`/`closed`) is computed from outstanding
- API-first reuse:
- web and Telegram Mini App use same debt endpoints
- dashboard receives compact active-debt summary endpoint (not full debt history payload)

## Analytics Module (Implemented Baseline)
- Read-focused analytics endpoints are implemented over existing operations/debts data.
- Endpoint groups:
- calendar aggregates (monthly matrix with week totals, Monday-first grid contract)
- calendar year aggregates (12 month cards with per-month income/expense/ops/balance)
- trend aggregates (day/week/month/year buckets for income/expense/balance)
- highlights aggregates with category breakdown (`category` or `group` level)
- highlights aggregates for analytics tabs:
- month KPI summary (income/expense/balance/ops/avg day expense/max day)
- top heavy operations
- top expensive positions from receipt items
- position price-change markers
- Implemented API surface:
- `GET /api/v1/dashboard/analytics/calendar`
- `GET /api/v1/dashboard/analytics/calendar/year`
- `GET /api/v1/dashboard/analytics/trend`
- `GET /api/v1/dashboard/analytics/highlights`
- Query dimensions currently used by code:
- `period`, `date_from`, `date_to`, `month`, `year`, `granularity`, `category_kind`, `category_breakdown_level`
- API serves both `Dashboard` compact preview and full `Аналитика` section.
- Performance strategy:
- rely on existing indexed operation date/kind filters
- keep dashboard summary cache in Redis for repeated aggregate reads when Redis profile is enabled
- otherwise fall back to in-process cache for single-process/small-VPS mode
- keep cache keys parameterized by `user + period/range + version`
