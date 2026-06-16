# Roadmap

## Product Scope
- MVP-1 is implemented: Telegram auth, dashboard summary, operations CRUD, categories/groups, batch operation creation, receipt items, item catalog, debts, plans, currency/FX, admin access states, persisted UI preferences, and Docker Compose runtime.
- MVP-2 backlog: Google auth provider, budgets/limits, richer reports/charts, export/import.
- MVP-3 backlog: deeper Telegram Mini App optimization, async jobs and notifications, advanced analytics/recommendations, optional position-level analytics.

## Production Track
- Keep Telegram WebApp auth as the primary production path; browser Telegram login remains an optional fallback only when `TELEGRAM_BOT_USERNAME` is configured.
- Maintain release checks for `initData` freshness, admin approval, rejected/pending states, and admin actions.
- Continue mobile-first validation for 320-430px viewports, tap targets, keyboard overlap, sticky actions, modal/sheet behavior, and hover-free critical flows.
- Keep Telegram-specific behavior in the client runtime; backend contracts stay shared between Web UI and Telegram.

## Current Sprint
### Period Controls, All-Time Performance, And Geometry Audit 2026-06-16
- [x] Stage 1: audit period handling across dashboard, operations, analytics structure/highlights, analytics trends, calendar, debts and plans where applicable.
  - Done 2026-06-16: verified `all_time` highlights on backend, found frontend label drift in trends, found old dashboard analytics tabs, and confirmed operations money-flow had a backend pagination bottleneck for large all-time operation datasets.
- [x] Stage 2: unify period controls.
  - Done 2026-06-16: dashboard analytics now uses the same arrow period-control pattern as analytics/operations; hidden segmented tabs remain as compatibility state holders. Dashboard/analytics all-time arrows no-op instead of shifting meaningless ranges.
- [x] Stage 3: optimize `all_time` loading.
  - Done 2026-06-16 frontend hardening: operations summary requests now abort stale in-flight requests and ignore stale responses during fast period/filter switching.
  - Done 2026-06-16 backend fast path: `/api/v1/operations/money-flow` now uses SQL-level pagination for operation-only views (`source=operation`) and operation drilldowns (`category_id`, `item_template_id`), loading receipt rows only for the returned page.
  - Done 2026-06-16 mixed all-time fast path: default `source=all` list now fetches only the needed SQL window of operations before merging debt/FX rows; `money-flow/summary` uses SQL aggregation for operations instead of materializing every operation.
  - Residual future work: text search `q` in mixed `source=all` intentionally keeps the old full-materialization path for correctness across operation/debt/FX fields. If debts/FX grow to operation-scale volumes, add source-level SQL pagination/aggregation for those domains too.
- [x] Stage 4: fix desktop/mobile geometry.
  - Done 2026-06-16: analytics and dashboard category-structure grids now use equal fixed desktop panel heights for chart and right-side list; mobile overrides restore natural stacked height.
- [x] Stage 5: interaction regression pass.
  - Done 2026-06-16 targeted pass: analytics structure `all_time`, analytics period arrows, operations period popover, and desktop structure geometry are covered by e2e.
  - Done 2026-06-16 broader pass: contextual `+` actions for category groups and item sources now have browser regressions; analytics category drilldown verifies operations filters/API query; targeted kebab, sticky CTA and mobile shell geometry checks pass. Remaining future work is periodic full-matrix visual QA on real data/devices, not a blocker for this sprint.
- [x] Stage 6: test and visual validation.
  - Done 2026-06-16: frontend/API contracts, dashboard all-time highlights regression, analytics all-time/period e2e, operations period e2e, and desktop geometry e2e pass for the changed paths. Mixed e2e suites with different sync Playwright fixtures can still hit the known asyncio-loop setup conflict; affected tests pass when run in isolated pytest processes.

### Reliability And UX Audit 2026-06-15
- [x] Dashboard reliability.
  - Done 2026-06-16: summary loading now has an independent lifecycle from optional currency/plans/debts panels. Repeated dashboard refreshes coalesce in-flight optional work instead of aborting it, and standalone dashboard-plan refreshes reuse the same in-flight work.
- [x] Frontend actions and popovers.
  - Done 2026-06-16: create-group modal ownership moved to category runtime, batch category tests use stable nav selectors, picker init no longer reads the global action facade, and money-flow receipt chips open through the operations runtime. Covered by frontend contracts, bulk import e2e, and receipt-chip money-flow e2e.
- [x] Activity journal readability.
  - Done 2026-06-16: raw `old/new` values remain in the API, while display values now format enums, dates, money/rates, booleans, and resolve category/group/counterparty references on read. Operation receipt updates add compact added/removed/changed item metadata; deleted historical references fall back to `#id (удалена)`.
- [x] Analytics Year view by quarters.
  - Done 2026-06-16: the Year calendar now renders four quarter rows from the existing 12-month API payload. Each quarter shows totals for inflow, outflow, events, operating surplus/deficit, and cash flow; month cards remain clickable.
- [x] Categories and Item Catalog contextual creation.
  - Done 2026-06-16: category groups and item sources now expose contextual `+` actions on hover/focus and matching kebab-menu actions for touch devices. Category creation opens with the group preselected; item-template creation opens with the source prefilled.
- [x] Audit closeout.
  - Done 2026-06-16: roadmap collapsed to the current source of truth, targeted frontend/API/e2e checks passed. One broad mixed e2e command still hits the existing sync Playwright inside asyncio-loop fixture limitation; the same failing scenarios pass when run in isolated pytest processes.

## Recently Closed Work
- Operations is money-flow first: legacy operation-list mode and mass-selection UI are removed from the active UX.
- Operations filters support category and item-template navigation from analytics, category usage, item usage, and receipt flows.
- Category and item cards include usage modals with KPIs and related operations.
- Debts use `Движения` for financial movement history and keep audit `Журнал` separate.
- Debt movements, debt additions, repayments, and forgiveness stay reflected in money-flow and dashboard/debt caches.
- Dashboard analytics endpoints share the backend cache namespace and invalidation path.
- Runtime registry is the preferred frontend dependency path for feature modules; low-risk action-bus/global consumers have been migrated where practical.

## Key Modules
- Dashboard: `static/js/app-features-dashboard.js`, `static/js/app-dashboard-data.js`, `app/api/v1/endpoints/dashboard.py`.
- Analytics calendar: `static/js/app-features-analytics-calendar.js`, `static/css/components-analytics-summary.css`, `tests/e2e/test_analytics_mobile_e2e.py`.
- Categories: `static/js/app-categories.js`, `static/js/app-categories-ui.js`, `static/js/app-categories-table-ui.js`, `static/js/app-bulk-bindings-categories.js`.
- Item catalog: `static/js/app-item-catalog*.js`, `static/js/app-init-features-pickers.js`, `static/js/templates/shell-sections-secondary.js`.
- Activity journal: `app/services/activity_service.py`, `app/schemas/activity.py`, `static/js/app-activity.js`.
- Operations and receipts: `app/services/operation_service.py`, `app/services/operation_money_flow_service.py`, `static/js/app-features-operations.js`, `static/js/app-init-features-operations.js`.
- Frontend contracts and e2e: `tests/api/test_frontend_*_contract.py`, `tests/e2e/`.

## Test Baseline
- Fast frontend contracts: `./.venv/bin/pytest -q tests/api/test_frontend_ui_contract.py tests/api/test_frontend_runtime_contract.py`
- Dashboard/action contracts: `./.venv/bin/pytest -q tests/api/test_frontend_runtime_contract.py tests/api/test_frontend_bootstrap_contract.py tests/api/test_frontend_ui_contract.py`
- Activity journal regression: `./.venv/bin/pytest -q tests/api/test_operations_api.py::test_activity_journal_tracks_operation_create_update_delete`
- Operation money-flow API regression: `./.venv/bin/pytest -q tests/api/test_operations_api.py`
- Targeted e2e used in this audit:
  - `./.venv/bin/pytest -q tests/e2e/test_operations_money_flow_e2e.py::test_operations_period_popover_changes_period -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_operations_money_flow_e2e.py::test_operations_receipt_chip_opens_same_positions_modal_as_kebab -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_bulk_import_sections_e2e.py -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_analytics_mobile_e2e.py::test_mobile_analytics_category_drilldown_opens_operations_with_filter -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_plans_ui_e2e.py::test_plan_kebab_menu_actions_work_from_floating_popover -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_mobile_shell_cards_e2e.py -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_analytics_mobile_e2e.py::test_mobile_analytics_calendar_scroll_wrap_reaches_last_columns tests/e2e/test_analytics_mobile_e2e.py::test_mobile_analytics_year_view_card_opens_month_view -m e2e`
