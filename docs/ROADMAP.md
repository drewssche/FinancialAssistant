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
### Category And Catalog Interaction Fixes 2026-06-23
- [x] Category group creation modal reliability.
  - Done 2026-06-23: `Создать группу` no longer depends on bulk-import bindings for close, kind switch, and submit handlers. Create-group modal controls are bound in the regular app init path, with bulk duplicate bindings removed to avoid double submits.
- [x] Category group picker stability.
  - Done 2026-06-23: create/edit category group pickers now use the shared popover lifecycle with owner scopes and guarded click propagation, so clicking the group field keeps the picker open until selection, Escape, or outside click.
- [x] Contextual `+` placement.
  - Done 2026-06-23: category-group and item-source hover/focus `+` buttons moved next to the group/source name instead of the far-right action area; kebab actions remain on the right and touch-device actions remain in menus.
- [x] Regression coverage.
  - Covered by `tests/e2e/test_bulk_import_sections_e2e.py -m e2e`: category picker stays open and selects a group, create-group modal submits once and closes, contextual `+` prefill still works, and category/catalog `+` geometry stays close to the visible name.

### Product Utility And Naming 2026-06-23
- [x] Finance calculator side drawer, first increment.
  - Done 2026-06-23: added a local-only right drawer calculator with discount, price-change, unit-price, and split-check modes. The drawer is available from the topbar, uses current frontend money formatting, and has a mobile bottom-sheet layout.
  - Covered by frontend UI contract and isolated finance-calculator e2e geometry/calculation test. Future iteration: optional integration with operation/receipt forms after visual review.
- [x] Product naming first pass.
  - Done 2026-06-23: visible web title/login heading and sidebar mark now use `ФинАсист` / `ФА`.
  - Remaining manual step: update Telegram BotFather display name/description/username if the final public name is approved and available.

### Release Validation 2026-06-16
- [x] Commit under validation: `34870fa f`; working tree was clean before validation fixes.
- [x] API suite: `./.venv/bin/pytest -q tests/api` passed.
- [x] E2E domain suites passed in isolated pytest processes: operations money-flow, analytics mobile/desktop structure, bulk/contextual actions, mobile shell cards, debts, plans, currency, receipt/category pickers, batch create, and sort preference persistence.
- [x] Local Docker stack is running; app health is OK from inside the app container via `http://127.0.0.1:8000/health`.
- Notes:
  - `tests/e2e/test_sort_preset_persistence_e2e.py` must remain an isolated pytest process because it owns a sync Playwright lifecycle and conflicts with pytest-playwright async-loop fixtures when mixed into a large command.
  - Host `curl http://127.0.0.1:8001/health` failed in this validation shell even though `docker compose ps` showed the app published on `8001` and container-internal health returned OK.

### Production Hardening 2026-06-16
- [x] Browser Telegram login default safety.
  - Done 2026-06-16: `.env.example` no longer enables browser Telegram login by placeholder username. `TELEGRAM_BOT_USERNAME` placeholders (`change_me`, `change_me_bot`, `your_bot_username`) normalize to empty, while real usernames normalize without leading `@`.
  - Covered by config/auth API tests and auth-login UI e2e.
- [x] Release check script hardening.
  - Done 2026-06-16: `scripts/release_check.sh` no longer mixes all e2e tests into one pytest process when `RUN_E2E=1`; it runs domain e2e groups explicitly and keeps sort-preference sync Playwright tests isolated.
  - Fast release mode (`./scripts/release_check.sh`) passes locally: non-e2e baseline, request-budget guard, and tokenless health-check skip path.
  - Full local release mode (`RUN_E2E=1 ./scripts/release_check.sh`) passes with elevated socket permissions: non-e2e baseline, auth, operations money-flow, analytics, bulk/batch, mobile shell, debts, plans, currency, receipt/category pickers, isolated sort preferences, and request-budget guard.
- [x] Legacy plan confirmation compatibility.
  - Done 2026-06-16: plan confirmation and serialization fall back from zero/empty `original_amount` to positive `amount`, so older or manually-created plan rows can still be confirmed from Telegram without creating a zero-amount operation.
  - Covered by Telegram plan bot service tests and adjacent plan/reminder service tests.
- [x] Release/deploy checklist documentation sync.
  - Done 2026-06-16: release docs now prefer `release_check.sh` over a mixed full pytest command, VPS checklist documents placeholder-safe `TELEGRAM_BOT_USERNAME`, and scripts README explains the isolated e2e release mode.
- [ ] Production deploy checklist execution.
  - Next: decide whether to run the deploy-side checklist against a real VPS/domain or keep validation local until a production snapshot/domain is available.

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
