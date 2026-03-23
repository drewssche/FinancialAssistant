# Roadmap

## MVP-1
- Telegram auth
- Dashboard summary (day/week/month/year/`all_time`/custom)
- Operations CRUD + search/filter/sort basics
- Categories + category groups (icon/color), chip rendering
- Bulk actions for operations (select, bulk edit/delete, delete all)
- Categories grouped table (collapsible groups, row-level actions, `Удалить все` without checkbox bulk-select)
- Batch operation create flow
- Persisted user preferences for display/filter state
- Docker Compose stack (app + postgres + redis)
- List loading standard for high-volume sections: `20` rows initially + `+20` on scroll (infinite scroll; no visible numbered pagination)

## MVP-2
- Google auth provider
- Budgets/limits
- richer reports/charts
- export/import options

## Delivered in MVP-1.x (already implemented)
- Operations receipt detail:
- optional receipt line items in operation
- reusable position catalog (chips/templates)
- per-position price history
- discrepancy warning (`operation amount` vs `receipt total`) with non-blocking save
- optional per-line-item category in receipt rows
- Debt management module (`Долги`) with:
- counterparty cards
- debt create flow (`дал`/`взял`)
- repayment flow (`вернули`/`вернул`)
- outstanding progress and due-date tracking
- Analytics section baseline (`Аналитика`):
- calendar month grid with week totals
- year calendar aggregates
- trend charts for `day/week/month/year`
- highlights for top operations, category breakdown, anomalies, top positions and price increases
- Access governance baseline:
- user statuses (`pending/approved/rejected`)
- admin-only section for approve/reject/delete user
- admin identity from env (`ADMIN_TELEGRAM_IDS`)
- Production browser Telegram login gate:
- `GET /api/v1/auth/public-config`
- optional `/api/v1/auth/telegram/browser` flow when `TELEGRAM_BOT_USERNAME` is configured

## Feature Status: Debts (Implemented MVP Baseline)
1. Navigation and information architecture
- Implemented: sidebar section `Долги`
- Implemented: dashboard debt widget stays compact; full list is in `Долги`

2. Operation modal integration
- Implemented: operation modal mode switch `Обычная операция` / `Долг`
- In `Долг` mode:
- hide categories/tags inputs
- show debt-specific fields (`Кто/Кому`, `Сумма`, `Когда`, `До какого числа`, `Комментарий`)

3. Counterparty reuse and anti-duplication
- Implemented: counterparty input reuses existing cards
- Implemented: new debt with existing counterparty appends into existing card without duplicate card

4. Repayment mechanics
- Implemented:
- principal total
- repaid total
- outstanding total
- debt card is active while outstanding > 0
- when outstanding becomes 0, card is hidden from dashboard widget and marked closed in debts history

## MVP-3
- deeper Telegram Mini App optimization
- async jobs and notifications
- advanced analytics and recommendations
- optional position-level analytics (backlog candidate, depends on product demand)

## Production Transition Track (Near-Term)
1. Production hardening
- keep Telegram WebApp auth as the primary production path and verify it end-to-end (`initData`, freshness, admin approval, rejected/pending states)
- keep browser Telegram login as optional fallback only when `TELEGRAM_BOT_USERNAME` is intentionally configured
- make release checklist mandatory before deploy
- add/keep explicit regression coverage for access states and admin actions

2. Mobile-first adaptation
- adapt all core flows for narrow mobile viewports first (`320-430px` baseline)
- remove dependency on hover-only actions in critical flows
- review modal-heavy desktop interactions and replace with sheet/full-screen mobile patterns where needed
- validate tap targets, spacing, keyboard overlap, and sticky CTA behavior on mobile
- status update (2026-03-08):
- core mobile auth/navigation, operation/debt/category/item-catalog modals, batch modals and analytics calendar flows now have targeted e2e regression coverage
- remaining work is primarily real-device release validation, not baseline UI mechanics

3. Telegram Mini App integration polish
- support Telegram WebApp viewport specifics (`safe-area`, header chrome, expand behavior)
- keep Telegram-specific integration focused on container/runtime concerns, not native navigation buttons
- optimize startup/render path for mobile device constraints and in-app browser runtime
- keep backend contracts shared; Telegram-specific behavior stays in client layer

## Execution Steps (Current Sprint)
1. Production auth cleanup
- keep Telegram WebApp as the primary supported auth path
- expose browser Telegram login only behind `TELEGRAM_BOT_USERNAME` feature gate
- keep `ADMIN_TELEGRAM_IDS` as immediate auto-approve/admin access list

2. VPS deployment baseline
- run app without bind-mounted source code and without `--reload`
- keep one application process for `1 vCPU`
- cap service resources for `app`, `db`, and `redis` to fit `2 GB RAM`

3. Mini App readiness implementation
- mobile-first shell and safe-area support
- no critical hover-only actions
- Telegram WebApp adapter for viewport/back button/main button

## Status Against Refactor Plan
Working note:
- `docs/ROADMAP.md` is the active source of truth for the current execution plan and status
- `docs/AUDIT_TODO.md` is now treated as historical/archive context, not as the primary live task tracker

1. Fix current behavior with regression tests
- status: `done`
- done:
- critical web/e2e coverage exists for auth, debts, plans, analytics-mobile, receipt/item-catalog, chip-picker, mobile shell, sort-preset persistence, batch flows
- frontend runtime contract is protected by `tests/api/test_frontend_bootstrap_contract.py`
- examples: `tests/e2e/test_auth_login_ui_e2e.py`, `tests/e2e/test_debts_flow_e2e.py`, `tests/e2e/test_plans_ui_e2e.py`, `tests/e2e/test_analytics_mobile_e2e.py`, `tests/e2e/test_receipt_picker_store_scope_e2e.py`
- explicit executable regression matrix now exists in `scripts/test_regression_matrix.sh` for the critical chain `auth -> dashboard -> create/edit operation -> debts -> plans`
- by default the matrix runs the API nucleus and supports `RUN_E2E=1` for the full browser-backed chain

2. Stabilize frontend entrypoint
- status: `done`
- `static/index.html` no longer owns the full script chain
- ordered boot is centralized in `static/js/app-manifest.js`
- sequential startup is centralized in `static/js/app-bootstrap.js`

3. Remove fragile dependency on script load order
- status: `done` for the current architecture track
- init/runtime registries are in place: `static/js/app-init-registry.js`, `static/js/app-runtime-registry.js`
- key modules/factories/helpers are resolved through registry instead of ad-hoc global timing
- contract coverage exists in `tests/api/test_frontend_bootstrap_contract.py`

4. Reduce `window.App` usage
- status: `done` for the current architecture track
- done:
- legacy top-level `window.App.feature*` providers were removed from active runtime paths
- many consumers now use `getRuntimeModule(...)`
- `window.App.actions` was narrowed and documented as an explicit public facade contract in `static/js/app-features.js`
- `static/js/app-features.js` has now shrunk that explicit facade in practice: the category bridge no longer gets republished through the broad public action facade and now stays runtime-only behind `category-actions`
- random hot-path globals in startup/session/modal/operations/catalog/analytics paths were moved behind local getters or runtime-module lookup
- legacy analytics highlights UI access is no longer direct: `static/js/app-features-analytics-highlights.js` now resolves `analytics-highlights-ui` through registry-first lookup instead of depending on `window.App.featureAnalyticsHighlightsUi`
- the last legacy analytics-highlights UI bridge was removed: `static/js/app-features-analytics-highlights-ui.js` no longer publishes `window.App.featureAnalyticsHighlightsUi`, and `static/js/app-features-analytics-highlights.js` now resolves the UI strictly through the runtime registry
- residual/non-blocking:
- `static/js/app-features.js` still owns the intentional broad public facade for navigation/back-stack and debt/batch orchestration
- a few local getter paths still intentionally resolve through `window.App.actions` / `window.App.core` in compatibility-heavy files, but the category bridge and `feature*` global sprawl are no longer part of the active runtime path

5. Centralize frontend state and DOM updates
- status: `done` for the current architecture track
- done:
- shared runtime helpers/factories/preview flows are more centralized than before
- some hot-path DOM/state mutation flows were pulled behind runtime modules and local getters
- analytics segmented state transitions and persisted reload flows now go through a centralized runtime helper in `static/js/app-analytics-ui-coordinator.js`
- picker/modal binding glue now goes through a centralized runtime helper in `static/js/app-picker-ui-coordinator.js`
- those coordinator helpers now also resolve `core`/`session` through local getters instead of direct `window.App.actions` / `window.App.core` hot-path reads
- `static/js/app-init-features-pickers.js` now also narrows its global surface through local `actions/core/picker-utils` getters, and its fallback date-field binder no longer reaches into `window.App.core` directly
- `static/js/app-init-features-analytics.js` now also narrows its fallback coordinator through local `core/session` getters, so the fallback path no longer reaches directly into `window.App.core` or `window.App.actions.savePreferences`
- startup bootstrap now resolves Telegram adapter, session boot/login calls, and category-startup actions through local getters in `static/js/app-init-startup.js`
- receipt-picker runtime glue now resolves `picker-utils` and category-modal opening through local getters in `static/js/app-features-operation-modal-receipt-pickers.js`
- session preferences now resolve `renderTodayLabel()` through a narrow category-action getter instead of directly reading `window.App.actions` in the settings/apply path
- `static/js/app-features-session-auth.js` no longer keeps a top-level snapshot of `window.App.actions`; category-modal cleanup now resolves through a narrow local getter at use time
- `static/js/app-features-session.js` now also keeps `renderTodayLabel()` behind a narrow category-action getter, while leaving `refreshAll()` on the broader public action facade intentionally
- `static/js/app-features-operation-modal.js` no longer keeps a top-level snapshot of category actions; category catalog/select calls now resolve through a narrow getter at use time, while the modal flow itself stays unchanged
- `static/js/app-features-operations.js` also no longer keeps a top-level snapshot of category actions; mutation-feature wiring now resolves category actions through a narrow getter at assembly time
- `static/js/app-init-features-catalog.js` now also resolves `actions`, `picker-utils`, and `categories-ui-coordinator` through local getters instead of reading them directly from `window.App` at module top level
- analytics highlights UI is now also available as a runtime module, and `static/js/app-features-analytics-highlights.js` now resolves UI rendering through registry-first lookup instead of depending directly on the legacy `window.App.featureAnalyticsHighlightsUi` global
- item-catalog body click/menu orchestration now goes through `static/js/app-item-catalog-ui-coordinator.js`, and item-catalog section search/sort/collapse glue now goes through `static/js/app-item-catalog-section-coordinator.js`, so `app-init-features-catalog.js` no longer owns those imperative item-catalog paths directly
- item-catalog grouped render/build logic now goes through `static/js/app-item-catalog-render-coordinator.js`, so `static/js/app-features-item-catalog.js` is no longer the main grouped-render hot spot
- category section controls now go through `static/js/app-categories-section-coordinator.js`, so kind filter transitions, search debounce/reload, collapse-expand wiring, and infinite observer lifecycle are no longer owned directly by `app-init-features-catalog.js`
- categories grouped-table render orchestration and collapsed-group state transitions now go through a centralized runtime helper in `static/js/app-categories-ui-coordinator.js`
- categories edit modal open/close orchestration now also goes through `static/js/app-categories-ui-coordinator.js`
- categories body click/menu dispatch now also goes through `static/js/app-categories-ui-coordinator.js`
- debts cards click/menu dispatch now goes through a centralized runtime helper in `static/js/app-debts-ui-coordinator.js`
- analytics breakdown hover/focus event orchestration now goes through a centralized runtime helper in `static/js/app-analytics-hover-coordinator.js`
- analytics render-time breakdown hover binding now goes through a centralized runtime helper in `static/js/app-analytics-breakdown-ui-coordinator.js`
- analytics hover-state DOM application now goes through a centralized runtime helper in `static/js/app-analytics-hover-state-coordinator.js`
- analytics breakdown visibility persistence now goes through a centralized runtime helper in `static/js/app-analytics-breakdown-visibility-coordinator.js`
- analytics breakdown snapshot assembly now goes through a centralized runtime helper in `static/js/app-analytics-breakdown-snapshot-coordinator.js`
- analytics breakdown render/presenter logic now goes through a centralized runtime helper in `static/js/app-analytics-breakdown-render-coordinator.js`, so `static/js/app-features-analytics-highlights-ui.js` is now more focused on state ownership and high-level UI coordination than on HTML/SVG rendering details
- category picker clear-state is now separated from regular category chips, so `Без категории` is no longer exposed as a fake `data-category-id` option in operation modal search results
- regression coverage was updated for the real mobile categories UX path via card action menu before opening the edit-category modal
- residual/non-blocking:
- the remaining work is now mostly final presentation/facade polish rather than mixed DOM/state glue spread across init and feature files

6. Check and strengthen backend layer boundaries
- status: `done`
- done:
- API routers mostly call services (`app/api/v1/* -> app/services/*`)
- repositories are present and used across domain services
- backend boundary guard tests exist in `tests/api/test_backend_boundary_guards.py`
- `app/api/v1/admin.py` no longer talks to `UserRepository` directly; it now goes through `app/services/admin_user_service.py`
- `app/api/deps.py` no longer talks to `UserRepository` directly; it now goes through `app/services/auth_context_service.py`
- direct `app.repositories` imports in `app/api` are now expected to be zero and guarded by test
- `scripts/run_telegram_admin_bot.py` is now covered by a boundary guard so the bot shell cannot quietly grow direct `repositories` / `db.models` / `api` / `fastapi` imports
- current runtime entrypoints with business impact are now covered by service boundaries or explicit guards

7. Move shared web/Telegram logic into services
- status: `done`
- done:
- Telegram reminder delivery orchestration now goes through `app/services/telegram_plan_reminder_bot_service.py` instead of being assembled inside `scripts/run_telegram_admin_bot.py`
- auth/admin notification and plan reminder logic already live in services
- Telegram admin approval callback flow now goes through `app/services/telegram_admin_bot_service.py` instead of mutating user state directly in `scripts/run_telegram_admin_bot.py`
- Telegram reminders now support inline `Подтвердить` callback flow for planned operations, with reminder markup in `app/services/plan_reminder_service.py` and callback confirmation in `app/services/telegram_plan_bot_service.py`
- the Telegram bot shell is now guarded against drifting back into direct repository/model/api imports
- the Telegram bot shell is also guarded against importing `PlanReminderService` directly; reminder delivery stays behind the telegram-specific adapter service
- current Telegram runtime paths with business logic now go through explicit service-layer adapters instead of embedding domain mutation logic in the shell
- debt Telegram product flow now has two layers:
- full debt repayment sends an owner-only notification through `app/services/telegram_debt_notifier.py`, triggered post-commit from `app/services/debt_service.py`
- debt due-date reminders now also go through a dedicated queue path: `app/services/debt_reminder_service.py` owns scheduling/dedupe over `debt_reminder_jobs`, `app/services/telegram_debt_reminder_bot_service.py` owns Telegram delivery assembly, and `scripts/run_telegram_admin_bot.py` stays a thin polling/delivery shell
- current debt reminder event types:
  - `due_soon`: one-shot, one day before `due_date`
  - `overdue`: at most once per local day, with next-day reschedule after send

8. Unify caching model
- status: `done`
- done:
- backend cache contract exists in `app/core/cache.py` with Redis + local fallback
- backend cache contract is now namespaced and user-scoped instead of being implicitly dashboard-summary-only
- `plans` list/history now also use the shared backend cache contract via the `plans` namespace
- operations item-template reads now also use the shared backend cache contract via the `item_templates` namespace
- debts cards read now also uses the shared backend cache contract via the `debts` namespace
- operations summary and operations list reads now also use the shared backend cache contract via the `operations` namespace
- categories catalog, groups, and paginated table reads now also use the shared backend cache contract via the `categories` namespace
- `dashboard_analytics` namespace is now used by `GET /api/v1/dashboard/analytics/highlights`, `GET /api/v1/dashboard/analytics/trend`, `GET /api/v1/dashboard/analytics/calendar`, and `GET /api/v1/dashboard/analytics/calendar/year`
- dashboard cache invalidation is wired from operation/debt mutations
- analytics highlights cache invalidation is now wired from operation/category/group mutations
- item-template cache invalidation is now wired from both template CRUD and receipt-driven operation mutations, so template list / price-history reads stay coherent with чек-based price updates
- debts cards cache invalidation is now wired from debt create/update/delete and repayment mutations
- operations summary/list cache invalidation is now wired from operation create/update/delete mutations
- categories catalog/groups/paginated-table cache invalidation is now wired from category/group create/update/delete mutations
- cache metrics and request-budget tests exist (`app/core/metrics.py`, `tests/api/test_dashboard_api.py`, `tests/api/test_request_budgets_api.py`)
- cache runtime now also tracks Redis/local-fallback mode signals (`backend_cache_local_fallback_read_total`, `backend_cache_local_fallback_write_total`, local cache entry count) so Redis advisory decisions can be based on measured fallback pressure instead of a binary “Redis missing” check
- cache contract guard tests now pin key shape, namespace TTL registry, and namespace-scoped invalidation in `tests/api/test_cache_contract.py`
- plans cache invalidation after plan mutations is pinned in `tests/api/test_plans_api.py`
- item-template cache invalidation after template/receipt mutations is pinned in `tests/api/test_operations_api.py`
- debts cards cache invalidation after debt/repayment mutations is pinned in `tests/api/test_debts_api.py`
- operations summary/list cache invalidation after operation mutations is pinned in `tests/api/test_operations_api.py`
- categories catalog/groups/paginated-table cache invalidation after category/group mutations is pinned in `tests/api/test_categories_api.py`
- frontend bounded read-through cache also exists in `app-core-actions.js`
- no further dashboard analytics read endpoint remains outside the shared backend cache contract
- current app-scope read-heavy product surface is effectively closed on a shared cache contract
- residual uncached endpoints are low-cost or non-central compared with the main dashboard / operations / plans / categories / debts / item-template flows that motivated this plan item

9. Improve observability
- status: `done` for the current architecture track
- done:
- basic logging exists in `app/core/logging.py`
- API request correlation now exists: responses include `X-Request-ID`, and request-completion logs include `method`, `path`, `status_code`, `duration_ms`, and `request_id`
- Telegram bot now emits structured event logs for callback processing, reminder delivery, and `getUpdates` polling failures
- Telegram bot no longer emits generic startup Redis warnings; admin-only Redis advisory is now reserved for measured local-fallback pressure that exceeds the safe baseline
- plan reminder job lifecycle now emits structured background-job events from `app/services/plan_reminder_service.py` for sync/send/reschedule transitions
- preferences update path now emits structured background-job events from `app/services/preferences_service.py` and leaves a visible trace when reminder resync is triggered
- auth login/upsert flow now emits structured service-level auth events from `app/services/auth_service.py` for login success, new user creation, existing user update, admin auto-approve, and pending-user creation
- admin notification delivery now also emits structured notifier-level events from `app/services/telegram_admin_notifier.py` for send attempt / success / failure
- admin-only Redis fallback advisory now also goes through `app/services/telegram_admin_notifier.py`, and `app/services/redis_runtime_advisory_service.py` only sends it after measured local-fallback thresholds are exceeded plus a cooldown window
- admin user lifecycle now also emits structured service-level events from `app/services/admin_user_service.py` for approve/reject transitions, no-op status writes, hard-delete outcomes, and blocked self-actions
- plan mutation/orchestration flow now emits structured service-level events from `app/services/plan_service.py` for create/update/delete/confirm/skip and for downstream reminder-sync / item-template-sync requests
- Telegram plan confirmation now also emits structured service-level events from `app/services/telegram_plan_bot_service.py` for confirm attempt / success / missing-user / missing-plan / already-completed outcomes
- request and cache metrics exist in `app/core/metrics.py`
- health/measurement scripts exist (`scripts/health_check.sh`, `scripts/measure_request_scenarios.py`)
- Telegram bot has logging too (`scripts/run_telegram_admin_bot.py`)
- API request observability is pinned by `tests/api/test_observability_api.py`
- bot structured event logging is pinned by `tests/api/test_bot_observability_logging.py`
- reminder lifecycle background logging is pinned by `tests/services/test_plan_reminder_service.py`
- preferences/resync background logging is pinned by `tests/services/test_preferences_service.py`
- auth service observability is pinned by `tests/api/test_auth_observability.py`
- admin notifier observability is pinned by `tests/services/test_telegram_admin_notifier.py`
- admin user lifecycle observability is pinned by `tests/services/test_admin_user_service_observability.py`
- plan service observability is pinned by `tests/services/test_plan_service_observability.py`
- operation service observability is pinned by `tests/services/test_operation_service_observability.py`
- Telegram plan confirmation observability is pinned by `tests/services/test_telegram_plan_bot_service.py`
- residual/non-blocking:
- observability is now strong for API, auth upsert, admin governance decisions, admin notification delivery, Telegram bot shell, Telegram plan confirmation, reminder delivery, preferences-triggered reminder resync, plan orchestration, and the critical operation mutation flow
- debt Telegram repayment notification now also emits structured notifier-level events from `app/services/telegram_debt_notifier.py`
- debt `due_soon` reminder lifecycle now also emits structured background-job events from `app/services/debt_reminder_service.py`, and bot delivery is observable via the existing Telegram bot shell logs
- debt `overdue` reminder lifecycle now follows the same observable queue path and is also covered by `app/services/debt_reminder_service.py`
- the remaining gap is primarily broader cross-process correlation and future background entrypoints outside the currently instrumented flows

10. Check migrations and data-model consistency
- status: `done`
- done:
- Alembic environment and version history are present in `alembic/`
- tests build schemas from metadata in many API/service suites
- model imports are centralized in `app/db/models/__init__.py`
- migration consistency smoke test exists in `tests/test_migration_consistency.py`
- future Alembic branch cases remain a maintenance concern, not a current gap in the baseline consistency gate

11. Working rule for future refactor passes
- before deleting cross-module frontend contracts, first build a repo-wide consumer map
- preferred workflow: use an `explorer` subagent for the impact scan, then patch locally
- use subagents more aggressively for parallel audit/impact-scan/doc-sync work, while keeping final code edits and integration local

## Feature Draft: Analytics (Agreed, Next Delivery Track)
1. New section and IA
- New sidebar section: `Аналитика`
- `Dashboard` stays first and default-open section on app start
- Analytics is deep-dive section; dashboard keeps compact KPI highlights
- Analytics uses internal tabs to avoid one overloaded page:
- `Общий`
- `Календарь`
- `Операции`
- `Тренды`
- `Позиции` insights are merged into `Операции` tab (not separate tab)

2. Calendar-first monthly view
- main view is month grid with week starting Monday (`Пн..Вс`)
- calendar grid has explicit view switch:
- `Месяц` (day cells)
- `Год` (12 month cells with aggregated income/expense/ops/balance)
- grid navigation controls are scoped to grid only (prev/current/next for month or year)
- each day cell shows:
- income total
- expense total
- operations count
- each week row shows right-side totals:
- week income total
- week expense total
- week operations count
- calendar tab summary is rendered as grid-context KPI strip/cards (for current view month/year):
- primary KPI cards: income/expense/balance/operations
- secondary compact chip: single period result (`Профицит`/`Дефицит`/`Нулевой баланс`)
- detailed period KPI controls are shown in `Общий` tab (`week/month/year/custom`)

3. Trends and charts
- period switch supports `day/week/month/year/custom`
- trend charts include:
- income and expense bars
- balance line on top
- first extension after baseline:
- moving average
- period-over-period delta
- top expense categories

4. Insights blocks (priority after baseline tabs)
- top-5 heavy operations in selected month/period
- top categories by expense share
- anomaly checks for unusually large expense operations
- top-10 expensive receipt positions
- temporary `price increased` highlight for positions with meaningful price jump
- position-level mini trends (price and purchase frequency) in `Операции` tab

4. Dashboard integration strategy
- dashboard keeps lightweight analytics preview widget:
- mini trend sparkline for current period
- short deltas vs previous period
- primary action `Открыть аналитику`
- operations table on dashboard should be reviewed as optional:
- keep only compact recent rows (or hide via preference)
- full operations work stays in `Операции`
- dashboard widget visibility and density are preference-driven:
- show/hide analytics block
- show/hide operations block
- show/hide debts block
- operations row count (`5/8/12`)
- analytics insight density is preference-driven:
- top operations limit (`3/5/10`)
- top positions limit (`5/10/20`)

## Audit Plan (Current)
1. Stabilize shared UI mechanics
- fix one-time binding for reusable popovers (avoid duplicate listeners)
- move modal open/close flows to shared helpers with options payload

2. Reduce module size and coupling
- continue splitting `static/js/app-features.js` into focused modules (`operations`, `dashboard`, `preferences`, `item-catalog`)
- done: Item Catalog extracted to `static/js/app-features-item-catalog.js`
- done: Item Catalog modal/source-picker/history extracted to `static/js/app-features-item-catalog-modal.js`
- done: operations flow extracted to `static/js/app-features-operations.js`
- done: operation modal receipt flow extracted to `static/js/app-features-operation-modal-receipt.js`
- done: operation modal receipt interactions extracted to `static/js/app-features-operation-modal-receipt-interactions.js`
- split `static/js/app-core.js` into `state`, `dom-refs`, `format/helpers`
- keep each module under soft 300-400 lines, hard cap 500; current heavy modules above hard cap: none

3. Complete modal/category reuse
- use single entrypoint for category modal open from different contexts
- keep operation modal category picker and category modal synchronized through explicit events/hooks

4. Consistency and regression guard
- keep chip renderer single-source for tables and modal preview
- add focused UI/API tests for category create-from-operation flow and picker behavior

5. Unify list loading behavior to infinite scroll baseline
- apply `20` initial + `+20` incremental loading in all relevant list/table screens
- remove visible numbered pagination controls where server pagination is already used
- keep request contracts pagination-based under the hood (`page/page_size` or cursor)
- grouped-collapsible table pattern from `Каталог позиций` is adopted in `Категории`; keep both sections on one interaction contract

6. Item Catalog request/load optimization
- avoid noisy preference writes from group-toggle/sort actions via debounced persistence
- reduce search request pressure with local filtering when full catalog snapshot is available

8. Frontend runtime hardening
- done: script load order moved out of `static/index.html` into `static/js/app-manifest.js` and `static/js/app-bootstrap.js`
- done: init-stage registry added for `core/features/startup` and feature init modules
- done: runtime registry added for key feature modules (`session`, `dashboard`, `analytics`, `plans`, `operations`, `item-catalog`, `operation-modal`, etc.)
- done: hot navigation/session/analytics flows migrated to local dependency getters
- done: operations mutation, categories data, and plans refresh hooks migrated off direct `window.App.actions.*` hot-path calls
- done: plans popover handling now uses local picker-utils getter; operations/item-catalog resolve central runtime dependencies through registry
- done: dashboard resolves operation-modal/dashboard-data via getters; operations selection UI resolves bulk UI through registry getter
- done: operations display/mutation factories are registered in runtime registry and consumed from there without legacy `window.App.createOperations*` globals
- done: shared UI helpers `bulk-ui` and `category-ui` are registered in runtime registry; key consumers now resolve them from registry
- done: `picker-utils`, `dashboard-data`, and analytics submodules are registered in runtime registry; core consumers now resolve them from registry
- done: `operationModal` sub-factories for receipt/category/debt-counterparty are registered in runtime registry and resolved from the main modal module via registry-first access
- done: `operationModal` preview is registered in runtime registry; stabilized modal/session consumers have started dropping local legacy fallbacks
- done: unused legacy `createOperationModal*` global exports have been removed from the active modal factory chain where registry is already the only supported resolution path
- done: `item-catalog` modal/source factories are registered in runtime registry and no longer use legacy `window.App.createItemCatalog*` globals
- done: old shared globals `dashboardData`, `pickerUtils`, `bulkUi`, and `featureAnalyticsModules` have been removed from the active frontend runtime path
- done: `analytics` and `plans` provider globals are no longer needed by any `static/js` consumer and have been removed from the active runtime path
- done: `dashboard`, `debts`, and `operations` provider globals are no longer needed by any in-repo consumer and have been removed from the active runtime path
- done: e2e consumers were moved from `window.App.feature*` to `window.App.getRuntimeModule(...)`, allowing `session`, `item-catalog`, `session-preferences`, and `session-auth` provider globals to be removed too
- done: low-risk `window.App.actions` consumers in debts/admin/categories/analytics-settings paths now call registry-backed runtime modules directly where possible
- done: plans, analytics-highlights, operations-mutations, and debt-edit modal flows now avoid several action-bus hops where direct runtime feature dependencies already exist
- done: `app-init-features.js` and `app-section-ui.js` now resolve period refresh, section loading, analytics preview reload, and preference persistence through runtime modules instead of routing these low-risk flows through `window.App.actions`
- done: `app-init-core.js` now resolves session/settings UI flows, dashboard widget refresh triggers, plan controls, and item-catalog / operation-modal close-open flows through runtime modules instead of the broad top-level action bus
- done: `app-core-actions.js` no longer depends on `window.App.actions.logout`; `401` handling now also goes through the registry-backed `session` runtime
- done: bulk operation and item-catalog import flows now refresh via direct runtime modules instead of `window.App.actions` for ordinary post-mutation reloads
- done: the remaining `window.App.actions` surface is now explicitly documented in code as a public facade contract instead of an accidental export bag
- done: the public facade contract is now frozen in code so future cleanup passes have a stable boundary to compare against
- done: post-mapping cleanup removed two leftover accidental facade uses: `actions.telegramLogin` guard in `app-init-core.js` and `actions.updateOperationsBulkUi` in `app-features-operations.js`
- done: backend boundary guard tests were added to pin `services/repositories -> api` reverse-dependency rules and to limit direct `app.repositories` imports in `app/api` to the known boundary exceptions
- done: admin API user-management flow now goes through `app/services/admin_user_service.py` instead of talking to `UserRepository` directly from the router
- done: auth dependency resolution now goes through `app/services/auth_context_service.py` instead of querying `UserRepository` directly from `app/api/deps.py`
- done: Telegram admin approval callback flow now goes through `app/services/telegram_admin_bot_service.py` instead of mutating `UserRepository` directly inside the bot script
- in progress: remove remaining legacy fallback branches from top-level non-feature globals and decide how much of `window.App.actions` should remain public
- next: continue migration in remaining heavy files and reduce fallback reliance on legacy globals
- working rule: before deleting entries from the public facade, first build a repo-wide consumer map; using an `explorer` subagent for this narrow scan is the preferred workflow
- keep abort/sequence guards for in-flight catalog requests to prevent stale render races

7. Section-aware refresh strategy
- after operation/debt/category mutations, refresh active-section datasets first
- avoid unconditional dashboard/operations/debts simultaneous reload when section is not visible

## Optimization Focus (Next)
1. Frontend module size normalization
- split high-volume files still above hard threshold:
- `static/js/app-init-features.js`
- `static/js/app-features-analytics.js`
- `static/js/app-features-operation-modal.js`
- `static/js/app-features-operation-modal-receipt-interactions.js`
- `static/js/app-features-operations.js`

2. Auth/access hardening
- remove or fully isolate dev-auth fallback path for production deployments
- add explicit regression tests for pending/rejected UX states in web app

3. Admin list performance
- avoid potential relationship N+1 in admin users listing (eager load telegram identity)
- add pagination for admin users list when user count grows

4. Scaling UX technical debt
- migrate away from `body zoom` to token-based scaling model
- lock visual regression checks for scale extremes (`85/115`)

5. Production readiness
- add a deploy-oriented checklist for env/config correctness (`APP_ENV`, `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_IDS`)
- verify structured logging/request tracing baseline before first real users
- document rollback path for schema migrations and release failures

6. Telegram Mini App readiness
- audit all main sections against mobile-first layout rules
- replace hover-only row actions with always-reachable mobile actions
- validate auth/session restore inside Telegram WebApp container, not only in desktop browser

## Feature Draft: Plans

Agreed direction:
- dedicated section `Планы` after `Операции` in sidebar
- dashboard block `Операции за период` is replaced by `Ближайшие планы`
- plans are separate entities and do not affect factual operations/statistics until explicit confirmation
- no `requires confirmation` toggle: confirmation is mandatory by definition
- plan form should reuse existing operation-form contract as much as possible, excluding debt mode
- first-class scenarios:
- one-off planned purchase / shopping preparation
- recurring monthly bill / payment / income
- dashboard KPI layer for potential spend/income and due confirmations

MVP implementation sequence:
1. Section shell + dashboard replacement + client-side state/render contract
2. Plan create/edit form reusing operation form fields (`expense/income`, amount, category, comment, receipt items)
3. Confirmation flow: `Подтвердить` creates a normal operation immediately
4. Recurrence contract and due/upcoming plan instances
5. Telegram reminder delivery for due recurring plans

Current status:
- implemented:
- dedicated `Планы` section and dashboard replacement block `Ближайшие планы`
- backend entity/API for plans
- create/edit via existing create-operation modal in `plan` mode
- one-off and recurring plans with confirm/skip/delete actions
- confirm creates a normal operation immediately
- due/overdue/upcoming KPI/filter layer in plans UI
- Telegram reminder baseline via existing polling bot worker
- recurring history/event log via `plan_operation_events` and `/api/v1/plans/history`
- extended recurrence baseline: weekly multi-weekday schedules + monthly `last day of month`
- daily recurrence now also supports `weekdays only`
- plans history UI includes event-type filters for `confirmed / skipped / reminded`
- not implemented yet:
- custom recurrence rules beyond `daily/weekly/monthly/yearly`

See detailed execution queue: `docs/AUDIT_TODO.md`
