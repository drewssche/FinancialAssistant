# Engineering Principles

## Performance and Reuse
- API-first architecture for maximum reuse between Web and Telegram Mini App
- Reuse business logic through service and repository layers
- Push filtering/pagination/sorting to server side
- Client list rendering baseline for large datasets: initial `20` rows + incremental `+20` on scroll (infinite scroll UI over server pagination)
- Cache stable reference data when useful (categories, user preferences)
- Realtime search must support request cancellation (`AbortController`) to avoid stale-response races

## Cache Strategy (Current)
- Allowed cache layers:
- frontend in-memory cache for short-lived UI datasets (`debts cards`, `categories list`, derived search views)
- local storage for auth token and fast preferences fallback
- backend cache (Redis) for expensive aggregated reads only
- Frontend TTL policy (current):
- `operations list` read-through cache: `15s`
- `debts cards` read-through cache: `20s`
- `categories groups/catalog` read-through cache: `60s`
- `categories table page` read-through cache: `45s`
- frontend cache store is bounded by max entries (FIFO eviction) to prevent unbounded memory growth
- Current backend implementation:
- backend cache contract is now namespaced and user-scoped in `app/core/cache.py`
- current namespaces:
- `dashboard_summary` -> `dashsum:v1:*`, TTL `60s`
- `dashboard_analytics` -> `dashanalytics:v1:*`, TTL `60s`
- current `dashboard_analytics` rollout: `analytics/highlights`, `analytics/trend`, `analytics/calendar`, `analytics/calendar/year`
- invalidation triggers for current backend cache namespaces:
  - `dashboard_summary`: operations, debts
  - `dashboard_analytics` (`highlights`, `trend`, `calendar`, `calendar/year`): operations
  - extra `dashboard_analytics` invalidation for `highlights`: categories, category groups
- invalidation on successful operations/debts mutations
- backend telemetry endpoint for cache/latency: `GET /api/v1/dashboard/summary/metrics`
- API middleware tracks request totals per endpoint (`METHOD /api/v1/...`) for request-volume analysis
- Lightweight ops mode (small install up to ~3 active users):
- no mandatory always-on monitoring stack
- keep CI guardrails (`request budgets` + cache invalidation tests) as primary protection
- run manual weekly health check via `GET /api/v1/dashboard/summary/metrics` and key screen response-time sanity check
- recommended command: `TOKEN=... BASE_URL=http://localhost:8001 ./scripts/health_check.sh`
- switch to full monitoring/alerts when load grows (about `20+` active users) or visible perf complaints appear
- Cache adoption rule:
- introduce cache only for endpoints/views with repeated reads or expensive aggregation; write-heavy flows stay source-of-truth first
- Invalidation must be explicit after mutating actions:
- operation/category/debt create/update/delete must refresh or invalidate dependent cached data
- Any cache key must have:
- deterministic key format (`user + endpoint/params + version`)
- bounded TTL
- documented invalidation trigger
- preferred backend format: `namespace + user scope + deterministic params`
- Do not cache destructive-action results optimistically without rollback path (`undo` or forced refetch)
- Search rule:
- default to server-side filtering for canonical lists; client-side cache filtering is acceptable only for already-loaded, bounded datasets (e.g., current debts cards view)
- Canonical search contract for list endpoints: optional query param `q` (+ existing section filters)

## Optimization ROI Priorities
- Priority order for implementation (`effort -> impact`):
- DB composite indexes for hot queries (`high impact`, `low-medium effort`)
- Redis cache for expensive dashboard aggregates (`high impact`, `medium effort`)
- Unified server-side search + request race cancellation in UI (`high impact`, `medium effort`)
- UI render batching/virtualization only after metrics confirm need (`medium impact`, `medium effort`)
- Every optimization candidate must include:
- baseline metric (`latency`, `request count`, `render time`)
- expected gain and rollback plan
- post-change measurement in the same environment
- Request-count budgets for key user actions must be covered by automated regression tests (API/UI level)
- Canonical request-budget source: `docs/REQUEST_BUDGETS.md` (JSON block consumed by `tests/api/test_request_budgets_api.py`)

## Scalability Baseline
- PostgreSQL as primary datastore
- Redis included in compose for cache/session/queue evolution
- Dockerized local stack matching production concepts

## Code Organization
- Keep files small and focused by responsibility
- Soft file size target: 300-400 lines
- Hard refactor threshold: over 500 lines
- Avoid monolithic files and duplicate business logic
- Frontend code must be split into modules (`core`, `ui`, `features`) when file grows over 500 lines
- Shared UX behaviors (confirm, toast, undo, modal open/close) must be implemented as reusable helpers, not duplicated handlers

## Localization and Formatting
- Product UI language is Russian by default
- Date display format in UI tables/cards is `DD.MM.YYYY`
- Monetary and semantic statuses must use consistent meaning-based color patterns across all screens
- UI calculations must use raw model values (API/state), not formatted text from DOM nodes (to avoid locale/currency parse bugs)

## Reliability
- DB constraints and indexes from day one
- Alembic migrations required for schema changes
- Structured logging and request tracing ids (next iterations)
- Pre-release execution checklist: `docs/RELEASE_CHECKLIST.md`
