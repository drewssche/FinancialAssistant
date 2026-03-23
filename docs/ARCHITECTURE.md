# Architecture

## High-Level
- Backend: FastAPI
- DB: PostgreSQL
- Migrations: Alembic
- Migration smoke test: `tests/test_migration_consistency.py` checks Alembic heads and SQLAlchemy metadata parity on a safe in-memory schema bootstrap
- Cache/queue-ready: Redis (optional; app has local fallback for dashboard cache, and admin-only advisory can now warn when measured local-fallback pressure grows beyond the small-install baseline)
- Runtime: Docker Compose
- Observability baseline: API responses now carry `X-Request-ID`, API request-completion logs include `method`, `path`, `status_code`, `duration_ms`, and `request_id`, Telegram bot emits structured event logs for callback/reminder/polling outcomes, Telegram inline plan confirmation emits structured service-level events through `app/services/telegram_plan_bot_service.py`, admin governance mutations emit structured service-level events through `app/services/admin_user_service.py`, plan-reminder job lifecycle emits structured background-job events from `app/services/plan_reminder_service.py`, debt due-soon reminder lifecycle emits structured background-job events from `app/services/debt_reminder_service.py`, preferences updates emit structured background-job events before/after reminder resync through `app/services/preferences_service.py`, HTTP totals remain tracked separately in `app/core/metrics.py`, cache runtime now also exposes Redis/local-fallback pressure signals used by the admin-only Redis advisory path, and debt-repayment owner notifications emit structured notifier-level events through `app/services/telegram_debt_notifier.py`

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
- Telegram plan reminders can now include an inline `Подтвердить` action; the confirmation source of truth remains `app/services/plan_service.py`, while the bot shell only delivers the reminder and forwards callback handling into service-layer Telegram adapters
- Debt Telegram notifications now have a split baseline:
- when a debt is fully repaid, `app/services/debt_service.py` triggers an owner-only Telegram notification through `app/services/telegram_debt_notifier.py`
- due-date debt reminders now have a dedicated queue path through `app/services/debt_reminder_service.py`, `app/db/models/debt_reminder_job.py`, and `app/services/telegram_debt_reminder_bot_service.py`
- current debt reminder event types:
  - `due_soon`: one-shot, one day before `due_date`
  - `overdue`: at most once per user-local day, with automatic next-day reschedule after a send

## Shared API for Multi-Client
One API serves both Web and Telegram Mini App clients.
Client-specific logic stays at UI layer; domain logic stays in backend services.

## Frontend Runtime Composition
- Frontend remains plain server-served HTML/CSS/JS without a bundler framework.
- `static/index.html` is reduced to a minimal bootstrap surface and does not enumerate the full runtime script chain anymore.
- Frontend boot is now split into:
- `static/js/app-manifest.js` as the ordered script inventory
- `static/js/app-bootstrap.js` as the sequential loader and bootstrap error surface
- `static/js/app-init-registry.js` for init-stage module registration (`core`, `features`, `startup`, feature init binders)
- `static/js/app-runtime-registry.js` for runtime module registration (`session`, `dashboard`, `analytics`, `plans`, `operations`, `item-catalog`, `operation-modal`, etc.)
- the same runtime registry is now also used for selected frontend factories, including operations and item-catalog factories
- shared frontend UI helpers are now also resolved through the same runtime registry layer (`bulk-ui`, `category-ui`)
- shared runtime helpers/data modules are now also resolved there (`picker-utils`, `dashboard-data`, analytics submodules)
- analytics init state transitions now also pass through a dedicated runtime helper boundary: `static/js/app-analytics-ui-coordinator.js` owns repeated analytics/dashboard segmented-state transitions and preference-persisted reload flows
- picker/modal input binding glue now also passes through a dedicated runtime helper boundary: `static/js/app-picker-ui-coordinator.js` owns repeated date-field normalization, date-trigger opening, search-picker wiring, and receipt-list event delegation
- those coordinator modules now also resolve `core`/`session` through narrow local getters instead of reaching into `window.App.actions` / `window.App.core` throughout their hot paths
- `static/js/app-init-features-pickers.js` now also narrows its global surface through local `actions/core/picker-utils` getters, and its fallback date-field binder no longer reaches into `window.App.core` directly
- `static/js/app-init-features-analytics.js` now also narrows its fallback coordinator through local `core/session` getters, so the fallback path no longer reaches directly into `window.App.core` or `window.App.actions.savePreferences`
- startup bootstrap now also resolves Telegram adapter, session boot/login calls, and category-startup actions through narrow local getters in `static/js/app-init-startup.js`
- receipt-picker runtime glue now also resolves `picker-utils` and category-modal opening through local getters in `static/js/app-features-operation-modal-receipt-pickers.js`
- session preferences now resolve `renderTodayLabel()` through a narrow category-action getter instead of directly reading `window.App.actions` in the settings/apply path
- `static/js/app-features-session-auth.js` no longer keeps a top-level snapshot of `window.App.actions`; category-modal cleanup now resolves through a narrow local getter at use time
- `static/js/app-features-session.js` now also keeps `renderTodayLabel()` behind a narrow category-action getter, while leaving `refreshAll()` on the broader public action facade intentionally
- `static/js/app-features-operation-modal.js` no longer keeps a top-level snapshot of category actions; category catalog/select calls now resolve through a narrow getter at use time, while the modal flow itself stays unchanged
- `static/js/app-features-operations.js` also no longer keeps a top-level snapshot of category actions; mutation-feature wiring now resolves category actions through a narrow getter at assembly time
- `static/js/app-init-features-catalog.js` now also resolves `actions`, `picker-utils`, and `categories-ui-coordinator` through local getters instead of reading them directly from `window.App` at module top level
- analytics highlights UI is now also available as a runtime module: `static/js/app-features-analytics-highlights-ui.js` registers `analytics-highlights-ui`, and `static/js/app-features-analytics-highlights.js` now resolves UI rendering through registry-first lookup instead of depending directly on the legacy `window.App.featureAnalyticsHighlightsUi` global
- item-catalog body click/menu orchestration now also has its own runtime boundary: `static/js/app-item-catalog-ui-coordinator.js` owns item-catalog card-menu toggle and row-level click dispatch, while `static/js/app-item-catalog-section-coordinator.js` owns item-catalog search/sort/collapse section glue and `app-init-features-catalog.js` keeps only cross-section binding
- item-catalog grouped render orchestration now also has its own runtime boundary: `static/js/app-item-catalog-render-coordinator.js` owns grouped render/build logic, so `static/js/app-features-item-catalog.js` is now primarily a data/cache/modal assembly layer instead of a grouped-render hot spot
- category section controls now also have their own runtime boundary: `static/js/app-categories-section-coordinator.js` owns category-kind filter transition, search debounce/reload, collapse-expand wiring, and infinite-scroll observer lifecycle, while `app-init-features-catalog.js` keeps cross-section binding
- at this point, the remaining `window.App` usage is mostly concentrated in intentional facade/orchestrator layers rather than scattered hot-path feature files; the category bridge itself has moved to runtime-only registration, and the remaining broad surface is mostly the explicit facade in `static/js/app-features.js`
- `static/js/app-categories.js` now makes its legacy bridge explicit through runtime registration: category actions are assembled in `publicCategoryActions` and registered as a runtime module instead of being republished through the broad public action facade
- category-specific consumers in `static/js/app-bulk-bindings-categories.js`, `static/js/app-bulk-bindings-operations.js`, and `static/js/app-section-ui.js` now read through the runtime-registered `category-actions` bridge instead of the broad `window.App.actions` bag
- `static/js/app-features-session-auth.js` now also reads category modal closers through the runtime-registered `category-actions` bridge, which allowed `static/js/app-features.js` to drop those category modal helpers from the broad compatibility facade
- category edit-modal open flows now follow the same rule: `static/js/app-features.js` no longer republishes them broadly, and they stay behind the runtime-registered category bridge plus category UI coordinators
- category loading, group creation, and category bulk-delete flows now follow that same rule too: `static/js/app-features.js` no longer republishes them through the broad facade, and they stay behind the runtime-registered `category-actions` bridge
- the receipt-picker create-category path now follows the same bridge: `static/js/app-features-operation-modal-receipt-pickers.js` reads `openCreateCategoryModal` from the runtime-registered `category-actions` module instead of the removed broad facade export
- `static/js/app-categories-data.js` now also uses narrow runtime getters for category side-effects (`category-ui`, `operation-modal`, `dashboard`, `operations`) instead of routing those refresh/picker hooks through a broad action getter
- `static/js/app-features-operation-modal.js` now also resolves its category bridge through the runtime-registered `category-actions` module instead of a broad `window.App.actions` getter
- `static/js/app-init-features-catalog.js` now also consumes category-specific section/table behavior through that runtime-registered category bridge, so category section glue no longer depends on the broad `window.App.actions` bag for its primary path
- `static/js/app-init-core.js` now also consumes category-specific modal/render/icon behavior through that runtime-registered category bridge, so core modal wiring no longer depends on the broad `window.App.actions` bag for those paths
- `static/js/app-init-features.js` now also consumes category/group submit flows through that runtime-registered category bridge, so feature-form glue no longer depends on the broad `window.App.actions` bag for those paths
- `static/js/app-init-features-pickers.js` now also consumes category group-search/group-picker handlers through that runtime-registered category bridge, while `static/js/app-init-startup.js` now keeps category-specific startup wiring separate from generic facade actions
- after those cuts, the remaining frontend hardening work is mostly residual compatibility/facade polish in `static/js/app-features.js` and a small tail of fallback/getter-heavy files such as `app-features-analytics.js`, `app-section-ui.js`, and some coordinator/core getter paths that still read `window.App.actions` or `window.App.core` intentionally for compatibility
- `static/js/app-features.js` is no longer only the place where the explicit facade is documented; it has also started shrinking in code, with category helper/picker/render subclusters now staying behind the runtime-registered category bridge instead of being republished broadly through `window.App.actions`
- `static/js/app-features.js` now exposes only the remaining explicit public facade categories that are still intentionally broad; the category bridge itself is now runtime-only and no longer part of that broad compatibility contract
- categories table orchestration now also passes through a dedicated runtime helper boundary: `static/js/app-categories-ui-coordinator.js` owns grouped table render orchestration, collapsed-group state transitions, edit modal open/close coordination, and categories-body click/menu dispatch, while `app-categories-table-ui.js` keeps row/group rendering
- debts cards/menu orchestration now also passes through a dedicated runtime helper boundary: `static/js/app-debts-ui-coordinator.js` owns debt-card menu toggle and debts-cards click dispatch, while `app-init-features-debts.js` keeps section-level search, filters, observers, and form bindings
- analytics hover/focus lifecycle for category breakdown chart/list now also passes through a dedicated runtime helper boundary: `static/js/app-analytics-hover-coordinator.js` owns init-side hover/focus event orchestration, while `app-features-analytics-highlights-ui.js` still owns derived hover state application, DOM class updates, and render-time SVG/list binding
- analytics render-time breakdown hover binding now also passes through a dedicated runtime helper boundary: `static/js/app-analytics-breakdown-ui-coordinator.js` owns SVG-slice and rendered-list hover/focus binding, while `app-features-analytics-highlights-ui.js` still owns derived hover-state application and breakdown rendering
- analytics hover-state DOM application now also passes through a dedicated runtime helper boundary: `static/js/app-analytics-hover-state-coordinator.js` owns shared chart/list hover-state UI application for analytics and dashboard breakdowns, while `app-features-analytics-highlights-ui.js` still owns snapshot construction and visibility persistence
- analytics breakdown visibility persistence now also passes through a dedicated runtime helper boundary: `static/js/app-analytics-breakdown-visibility-coordinator.js` owns hidden-key read/write and visibility-toggle persistence, while `app-features-analytics-highlights-ui.js` is now more focused on snapshot construction and breakdown rendering
- analytics breakdown snapshot assembly now also passes through a dedicated runtime helper boundary: `static/js/app-analytics-breakdown-snapshot-coordinator.js` owns category/dashboard breakdown snapshot construction, while `app-features-analytics-highlights-ui.js` is now more focused on rendering, DOM binding, and hover application
- analytics breakdown render/presenter logic now also passes through a dedicated runtime helper boundary: `static/js/app-analytics-breakdown-render-coordinator.js` owns donut-markup and breakdown list/chart rendering for analytics and dashboard surfaces
- `static/js/app-features-analytics-highlights-ui.js` is no longer a broad mixed hot spot and no longer publishes the legacy `window.App.featureAnalyticsHighlightsUi` compatibility export; the main remaining frontend hardening hub is now the explicit public action facade in `static/js/app-features.js`, rather than mixed analytics/category UI modules
- Telegram bot runtime boundary is now guarded in tests: `scripts/run_telegram_admin_bot.py` is expected to stay a thin shell over `app.core.*`, `app.db.session`, and `app.services.*`, without direct `repositories` / `db.models` / `api` imports
- auth service now also emits structured service-level auth events for login success, new/existing Telegram-user upsert, admin auto-approve, and pending-user creation, which gives observability on the critical user-entry flow without pushing that logic into API handlers
- admin-notification delivery now also emits structured notifier-level events from `app/services/telegram_admin_notifier.py` for send attempt / success / failure, which makes the pending-user approval fan-out observable separately from the auth upsert path
- admin user lifecycle now also emits structured service-level events from `app/services/admin_user_service.py` for status transitions, no-op status writes, hard-delete outcomes, and blocked self-actions, so access-governance decisions are observable independently from auth upsert and notifier delivery
- plan service now also emits structured service-level events for create/update/delete/confirm/skip flows and for downstream reminder-sync / item-template-sync requests, which makes plan orchestration observable without pushing that concern into API routes
- operation service now also emits structured service-level events for create/update/delete flows, which makes the critical operation mutation path observable without pushing that concern into API routes
- Telegram inline plan confirmation now also emits structured service-level events from `app/services/telegram_plan_bot_service.py` for confirm attempt / success / missing-user / missing-plan / already-completed outcomes, so callback-path failures are observable independently from the bot shell transport logs
- backend cache contract now also covers `plans` list/history reads through the shared user-scoped cache namespace in `app/core/cache.py`, with invalidation from create/update/delete/confirm/skip mutations in `app/services/plan_service.py`
- backend cache contract now also covers operations item-template reads through the shared user-scoped cache namespace in `app/core/cache.py`: `list_item_templates()` and `list_item_template_prices()` now read through the `item_templates` namespace, while both template CRUD and receipt-driven operation mutations invalidate that namespace to keep template list / price-history views coherent
- backend cache contract now also covers debt-card reads through the shared user-scoped cache namespace in `app/core/cache.py`: `DebtService.list_cards()` now reads through the `debts` namespace, while debt create/update/delete and repayment mutations invalidate that namespace to keep cards coherent
- backend cache contract now also covers operations summary/list reads through the shared user-scoped cache namespace in `app/core/cache.py`: `OperationService.summarize_operations()` and `OperationService.list_operations()` now read through the `operations` namespace, while operation create/update/delete mutations invalidate that namespace
- backend cache contract now also covers category catalog/group/table reads through the shared user-scoped cache namespace in `app/core/cache.py`: `CategoryService.list_categories()`, `list_groups()`, and `list_categories_paginated()` now read through the `categories` namespace, while category/group create/update/delete mutations invalidate that namespace
- operation modal category search now treats `Без категории` as a dedicated clear action instead of a pseudo-category chip, which keeps search results and chip-count semantics aligned with the actual category dataset
- `operationModal` internals are being migrated the same way: receipt/category/debt-counterparty factories are now registry-addressable
- `operationModal` preview is also registry-addressable now, so the modal family is converging on one runtime resolution path and no longer needs several legacy factory globals for its main flow
- Migration rule:
- new cross-module code should prefer registry lookups or local dependency getters over direct global calls
- legacy `window.App.*` exports are being removed once a provider/consumer path is fully covered by manifest order, registry registration, and regression checks
- Current frontend hardening status:
- hot navigation/session/analytics flows already use local action getters
- repeated analytics UI state transitions (period/view/granularity/breakdown selections) are now funneled through `analytics-ui-coordinator` instead of being repeated as separate state-sync handlers
- operations mutation, categories data, and plans refresh flows also use local action getters instead of direct `window.App.actions.*` hot-path calls
- dashboard, plans, debts modals, item catalog, and operations now resolve key runtime collaborators through registry access instead of hardwiring old globals
- operations and item-catalog factories now resolve through runtime registry as the primary path, and their old `window.App.create*` exports have been removed where no live consumer remains
- category/bulk shared UI helpers, picker utils, dashboard cached-read helpers, and analytics submodules are now consumed through runtime registry in stabilized paths
- the old `featureAnalyticsModules` shared global and several legacy helper/data globals (`dashboardData`, `pickerUtils`, `bulkUi`) have already been removed from the active frontend runtime path
- all main feature providers are now registry-addressable without top-level `window.App.feature*` exports inside `static/js`; the frontend runtime now relies on the registry path rather than legacy feature globals
- low-risk `window.App.actions` consumers are also being reduced: where a call can target `dashboard`, `session`, `analytics`, `operations`, or `item-catalog` directly through runtime registry, the bus indirection is being removed
- `app-init-features.js` and `app-section-ui.js` now call runtime modules directly for period refresh, section loading, and preference persistence; the top-level `actions` facade is now narrower and increasingly focused on navigation/category glue instead of routine data loading
- `app-init-core.js` now also resolves session/settings, dashboard preview reloads, plans controls, modal open/close flows, and item-catalog modal flows through registry-backed runtime modules; `actions` remains mainly for navigation, category glue, debt-specific modal glue, and batch/category orchestration that has not been extracted yet
- `app-core-actions.js` now handles `401` logout through the `session` runtime module too; the remaining `actions` surface is effectively centered on navigation (`switchSection`, back-stack helpers) and legacy category/batch/debt orchestration that still spans multiple subsystems
- `app-bulk-bindings-operations.js` and `app-bulk-bindings-item-catalog.js` now refresh through direct runtime modules (`dashboard`, `operations`, `item-catalog`) after imports and mass updates; ordinary post-mutation reloads are no longer routed through the broad action bus there
- `static/js/app-features.js` now documents the leftover `window.App.actions` surface as a public facade contract instead of an implicit export bag; at this point that contract is mainly navigation/back-stack orchestration plus debt/batch orchestration
- the public facade contract is now also frozen in code to discourage accidental expansion or silent mutation during future cleanup passes
- Working rule for future cleanup: before removing keys from the public facade, first build a repo-wide consumer map; using an `explorer` subagent for this scan is recommended because it is fast and reduces the chance of deleting a still-live action by local inspection only
- Two leftover edge cases were also removed after that mapping pass: `app-init-core.js` no longer uses `actions.telegramLogin` even as a guard, and `app-features-operations.js` no longer uses `actions.updateOperationsBulkUi`; both now use their direct runtime owners
- backend layer boundaries now have a lightweight import guard test: services/repositories must not depend on `app.api`, repositories/services must not pull in `fastapi` or `starlette`, and direct `app.repositories` imports in `app/api` are now expected to be zero
- `app/api/v1/admin.py` was moved off direct repository access: user-listing, status changes, and hard delete now go through `app/services/admin_user_service.py`, which owns the `UserRepository` interaction and admin-specific guardrails
- `app/api/deps.py` was also moved off direct repository access: bearer token decoding and current-user resolution now go through `app/services/auth_context_service.py`, leaving `deps.py` responsible only for HTTP dependency adaptation and approval/admin gating
- `scripts/run_telegram_admin_bot.py` now routes admin approval callback mutation through `app/services/telegram_admin_bot_service.py`; the bot script stays focused on Telegram transport, polling, message delivery, and structured event logging instead of mutating user state directly in the callback loop
- plan reminder inline confirmation follows the same pattern: reminder message markup is built in `app/services/plan_reminder_service.py`, and Telegram callback confirmation goes through `app/services/telegram_plan_bot_service.py` instead of duplicating plan-confirm business rules in the bot shell
- reminder delivery orchestration is now also outside the bot shell: due reminder collection, payload refresh, ready-to-send message assembly, and post-send success marking go through `app/services/telegram_plan_reminder_bot_service.py`
- the bot shell is now also guarded against importing `PlanReminderService` directly, so reminder lifecycle/domain logic stays behind service-layer adapters instead of drifting back into the shell

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
- keep backend cache under a namespaced user-scoped contract in `app/core/cache.py`
- current active backend cache namespace is `dashboard_summary`
- `dashboard_analytics` is now active for `analytics/highlights`, `analytics/trend`, `analytics/calendar`, and `analytics/calendar/year`
- `plans` is now active for plan list/history reads
- `item_templates` is now active for operation item-template list / price-history reads
- `debts` is now active for debt cards reads
- `operations` is now active for operations summary/list reads
- `categories` is now active for category catalog/groups/paginated-table reads
- keep dashboard summary cache in Redis for repeated aggregate reads when Redis profile is enabled
- otherwise fall back to in-process cache for single-process/small-VPS mode
- when the app stays in local-fallback mode and measured pressure exceeds the small-install baseline (`entries`, `fallback reads`, `fallback writes`, optional `dashboard summary p95`), `app/services/redis_runtime_advisory_service.py` can send an admin-only Telegram advisory through `app/services/telegram_admin_notifier.py`
- keep cache keys parameterized by `user + period/range + version`
