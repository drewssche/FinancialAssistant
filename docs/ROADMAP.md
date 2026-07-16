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
### Currency, Debt KPI And Position Metrics 2026-07-16
- [x] P0: replace the fragile private-font BYN glyph with the portable `Br` label in the shared currency formatter and cover the frontend contract.
- [x] P1: add contextual debt KPI states: receivables positive, payables negative, and net position colored by sign while zero remains neutral.
- [x] P1: make quantity the default position-ranking metric, keep amount visible in ranking context, and leave purchase/event count in the KPI summary and optional metric switch.

### Analytics Prices, Discounts And Drilldown Navigation 2026-07-16
- [x] P0: keep the category structure chart inside its fixed desktop panel and responsive mobile bounds.
  - Size the donut from the available card width and height instead of allowing a `36rem` square inside a `34rem` panel with padding.
  - Keep SVG hover expansion clipped to a deliberate chart viewport and cover 320/390/768/desktop widths without page overflow.
  - Done 2026-07-16: donut sizing now uses the card's available inner height, SVG overflow is clipped, and desktop geometry asserts that the chart remains inside the equal-height card.
- [x] P0: make contextual back navigation visible and stateful.
  - Preserve the existing section-back stack during analytics/category/position drilldowns instead of clearing it in the following section switch.
  - Use one compact icon button with a destination tooltip; restore the analytics tab, period, selected position, filters, sort order, and useful scroll context.
  - Keep ordinary sidebar navigation as a fresh navigation that clears contextual history.
  - Done 2026-07-16: contextual switches preserve the stack and open the destination at the top so the icon Back control is visible; Back restores the source tab, position analytics state, filters, and scroll position.
- [x] P1: add a dedicated `Цены и скидки` analytics tab and remove price/discount rankings from `Структура`.
  - Reuse the global analytics period and present `Цены` / `Скидки` as an internal segmented mode.
  - Price view: ranked bars for percentage change, absolute change, and current average price; expose previous/current purchase counts so one-off observations are not presented as reliable trends.
  - Discount view: ranked bars for saved amount, discount rate, and purchase count; filter by all/promo/coupon/loyalty-points using compact chips.
  - Selecting an item opens a focused time view and bucket drilldown to matching operations. Keep popular positions in `Позиции`, categories in `Структура`, and defer unrelated anomalies/largest operations to a future observations surface.
  - Done 2026-07-16: `Структура` contains only category/group composition. `Цены и скидки` reuses the global period and provides price/discount modes, metric rankings, discount-type filters, compact KPI summaries, selected-item timelines, and operation drilldown.
  - Done 2026-07-16: highlights include template IDs, absolute price change, current/previous sample and purchase counts, price timelines, discount type breakdowns, and type-aware savings timelines without an additional request.
- [x] P1: make position analytics visibly interactive.
  - Add restrained hover/focus motion, stronger active color, pointer affordance, and an explicit operation-drilldown tooltip to non-empty ranking/bucket controls.
  - Respect `prefers-reduced-motion`; do not add persistent pulse or layout-shifting animation.
  - Done 2026-07-16: ranking rows and non-empty timeline/matrix buckets use restrained hover/focus motion, stronger feedback, explicit pointer behavior, and operation-drilldown tooltips with reduced-motion support.
- [x] P1: replace passive operation filter labels with a consistent active-filter strip.
  - Render compact label/value chips with individual removal and one icon-only reset-all action.
  - Ensure reset-all clears every visible drilldown constraint, while Back restores the source analytics context.
  - Done 2026-07-16: active filters render as compact label/value controls with individual removal plus one icon-only reset-all action; drilldown Back remains independent from filter reset.
- [x] P1: extend tests and visual validation.
  - Cover price/discount API semantics, comparison sample counts, discount-type filtering, ranking sort, bucket drilldown, Back restoration, filter removal, and desktop/mobile overflow.
  - Done 2026-07-16: dashboard/API and frontend contracts pass; the full analytics browser suite covers Back restoration, filter removal, structure containment, and the new tab at 320/390/768/1440px. Targeted operations and session browser regressions also pass.

### Session Reliability And Telegram Startup 2026-07-16
- [x] P0: make Telegram Mini App startup reliable without a manual reload.
  - Replace the one-shot `Telegram.WebApp.initData` check with a bounded readiness wait and short backoff while the branded session-check animation remains visible.
  - Retry automatic login on `pageshow` and when the document becomes visible if no token exists and Telegram later provides `initData`.
  - Coalesce startup/login attempts so SDK readiness, visibility events, and user actions cannot submit duplicate authentication requests or bootstrap the app twice.
  - Stop waiting after a small fixed deadline and show the existing actionable login state instead of leaving an endless loader.
  - Cover delayed `initData`, immediate `initData`, absent Telegram SDK, resumed WebApp, failed authentication, and duplicate-event behavior with runtime and browser tests.
  - Done 2026-07-16: startup keeps the branded checking state while waiting up to five seconds for Telegram launch data, retries on `pageshow`/visibility recovery, and coalesces both authentication and bootstrap work.
- [x] P0: add in-place session renewal that never closes an operation modal or clears a receipt draft.
  - Add an authenticated `POST /api/v1/auth/refresh` endpoint that renews only a still-valid approved session and returns the new token with its exact expiration time.
  - Replace only the client token and expiration metadata; do not call `bootstrapApp()`, `logout()`, section navigation, modal close handlers, or data reloads after a successful refresh.
  - Coalesce parallel refresh attempts and renew automatically five minutes before expiry while the document is active; recheck immediately after the app returns to the foreground.
  - Keep a bounded absolute session lifetime (target: 12 hours) before full Telegram authentication is required.
  - Cover refresh authorization, expiry boundaries, rejected/deleted users, parallel requests, modal continuity, and preservation of a large receipt form.
  - Done 2026-07-16: authenticated `/auth/refresh` rotates a still-valid JWT, preserves its original session start, enforces a configurable 12-hour absolute lifetime, and returns exact expiration metadata without a database migration.
  - Done 2026-07-16: the shared request pipeline performs one background recovery and retries the original request after `401`; it no longer calls destructive logout for an authentication timeout.
- [x] P1: expose a quiet session status and manual renewal control.
  - Add a compact status to the user area, updated every 30 seconds: normal remaining time, an amber warning near expiry, and an icon button with the tooltip `Продлить сессию`.
  - Keep the control usable in desktop, mobile, and Telegram layouts without competing with primary operation actions.
  - Show success/failure feedback through the existing toast system and keep renewal fully background-safe for open modals.
  - Done 2026-07-16: the user block shows remaining time and a compact renewal control; create/edit operation headers expose the same control while a modal covers the sidebar. Automatic checks run every 30 seconds and refresh inside the final five-minute window.
- [x] P1: use the same branded authorization motion in browser and Telegram WebApp flows.
  - Explicitly enter the shared session-check state before stored-token validation and Telegram auto-login, reusing the lightweight logo float/pulse and `prefers-reduced-motion` behavior.
  - Do not add an artificial delay: animation remains visible only while readiness, authentication, or bootstrap work is actually pending.
  - Done 2026-07-16: stored-token validation and Telegram auto-login explicitly reuse the existing lightweight logo motion, with no artificial delay and unchanged reduced-motion behavior.
- [x] P1: preserve unsaved work if a session has already expired.
  - Do not invoke the current destructive `logout()` path immediately on an authentication timeout because it closes modals and clears runtime state.
  - Present a compact re-authentication layer over the current app, keep operation/receipt fields mounted, and resume the interrupted action after successful authentication when safe.
  - Treat explicit user logout and account rejection/deletion as destructive flows that still clear protected UI state.
  - Done 2026-07-16: failed background recovery opens a dedicated re-authentication layer over the mounted app. Telegram can recover in place; browser login can temporarily show the login surface without invoking modal close handlers.
  - Covered by auth API tests, frontend/modal contracts, and browser tests for delayed Telegram `initData`, single-login/bootstrap behavior, session refresh, `401` retry, retained operation amount/comment, and 390px modal geometry.

### Currency Alert Reliability And Context Actions 2026-07-15
- [x] P0: send currency threshold alerts only when the rate enters the configured zone.
  - Replace snapshot-marker semantics (`rate_date + rate + threshold`) with persisted above/below zone state. A new rate snapshot must not repeat an alert while the condition remains true.
  - Rearm a direction only after the rate leaves its trigger zone; changing the configured threshold also rearms the corresponding direction.
  - Guard the alert scan against overlapping bot instances during deploy/restart and preserve structured logs for trigger, suppression, rearm, delivery, and failure outcomes.
  - Cover transitions below -> above -> above -> below -> above, both threshold directions, threshold edits, bot restarts, and overlapping scans.
  - Done 2026-07-15: alert markers now persist the active threshold zone instead of a rate snapshot, legacy markers remain compatible, leaving the zone rearms delivery, and threshold edits create a new zone state.
  - Done 2026-07-15: the scan uses a PostgreSQL advisory lock with a local test fallback; structured events cover trigger, suppression, rearm, sent, failed, and overlapping-scan outcomes.
- [x] P1: keep contextual row/kebab actions and edit-modal actions in sync.
  - Introduce one entity-action registry used to derive both row menus and modal actions instead of maintaining duplicated button markup.
  - Add `История` to the item-template edit modal; add contextual `Добавить категорию` to category-group editing and `Добавить позицию` to item-source editing.
  - Preserve the already-correct category actions (`Журнал`, `Операции`) and avoid redundant actions where the modal already exposes the same content, such as receipt positions inside operation editing.
  - Show at most three frequent non-destructive actions directly in a modal header; keep destructive and less frequent actions in a compact modal action menu, especially on mobile.
  - Add contract tests for action parity plus desktop/mobile e2e for item history, contextual creation, modal-menu geometry, and action routing.
  - Done 2026-07-15: one contextual action registry now drives category, category-group, item-template, and source row menus; edit modals expose the applicable frequent actions.
  - Done 2026-07-15: item editing includes `История`; group/source editing includes prefilled child creation. Contract coverage and mobile item-history routing e2e pass.
- [x] P1: add visual position-purchase analytics for day, week, month, and year periods.
  - Add a dedicated `Позиции` analytics tab with a matrix chart: position rows, period buckets on the horizontal axis, intensity/short bars for values, and a fixed total scale per row.
  - Use one bucket and ranked horizontal bars for a day, Monday-Sunday daily buckets for a week, calendar days for a month, and months for a year. Do not imply hourly precision while operations store only a date.
  - Provide segmented metrics `Покупки` (distinct receipts/operations), `Количество` (sum of receipt quantity), and `Сумма`; default to purchases.
  - Keep position/source labels and totals sticky on desktop with controlled horizontal scrolling. On mobile, show the selected position's bucket chart above a ranked position list, while retaining access to the full scrollable matrix.
  - Support position search, source filtering, top-10/all display, period arrows, tooltips, and drilldown from a bucket to matching operations.
  - Aggregate directly in SQL by operation date and item template, with a normalized name/source fallback for legacy or deleted templates; cover API semantics, cache invalidation, interaction routing, and 320/390/768/desktop geometry.
  - Done 2026-07-15: the `Позиции` tab provides day/week/month/year buckets, purchases/quantity/amount metrics, search and source filtering, top-10/all, period navigation, sticky totals, mobile focus bars, and bucket drilldown into filtered operations.
  - Refined 2026-07-16: week view uses Monday-Sunday daily buckets; the mobile period control has equal compact arrows around a wider `Текущий` action, and summary values use compact KPI chips.
  - Done 2026-07-15: API aggregation groups receipt positions by operation date and template with historical name/source fallback. Existing operation and receipt composite indexes already cover the query path, so no redundant schema migration is required.
  - Covered by API aggregation tests, frontend/runtime contracts, action-routing e2e, and screenshot-backed overflow/sticky-column checks at 320, 390, 768, and 1440px.
  - [x] Add a visual ranking above the position timeline: horizontal bars follow the selected metric, selecting a row focuses the timeline/matrix, and an icon control switches value order between descending and ascending with an explicit title (`Чаще` / `Реже`, etc.).
    - Done 2026-07-16: ranking order follows purchases, quantity, or amount; selection drives the adjacent timeline and matrix, while the compact arrow control switches between explicit descending and ascending views.
  - [x] Add a fixed descending top-5 `Чаще всего покупали` dashboard block for the dashboard period, with purchases as the primary value, quantity/amount as context, operation drilldown, and a link to the full positions tab.
    - Done 2026-07-16: the dashboard highlights response includes a distinct-purchase top five with quantity and spend context; rows drill into matching operations and `Все позиции` opens the full analytics tab with the dashboard period.
  - [x] Replace the positions-specific period layout and date shifting with the shared `period-control` markup, popover lifecycle, and `period-control-utils.shiftPeriodBounds`, while retaining independent day/week/month/year state and excluding unbounded matrix ranges.
    - Done 2026-07-16: positions reuse the shared arrows, central period trigger, popover lifecycle, and period shifting utility while retaining independent day/week/month/year preferences. Compact control dates remain readable at 320px.
  - Covered by dashboard/API contracts and browser scenarios for ranking order, selection, weekly shifting, operation drilldown, shared-control geometry, sticky columns, and page overflow at 320, 768, and desktop widths.

### Operation Modal Calculator And Row Toggles 2026-06-23
- [x] Calculator in operation modals.
  - Done 2026-06-23: create/edit operation modals now expose a calculator button in the header action area. The existing calculator opens in a modal-attached side panel without the global overlay and closes automatically when the operation modal closes.
  - Mobile behavior remains a bottom sheet to preserve usable modal width.
- [x] Wider group/source row toggles.
  - Done 2026-06-23: category group rows and item source rows now collapse/expand from clicks on the row surface, while buttons, kebab menus, inputs, links and popovers keep their own actions.
- [x] Regression coverage.
  - Covered by finance-calculator e2e for modal-attached geometry/calculation/autoclose and by category/catalog e2e for row collapse/expand plus preserved contextual `+` actions.
- [x] Calculator entry points and drawer overflow.
  - Done 2026-06-24: calculator buttons remain only in create/edit operation modals; the side panel uses a compact close control and prevents horizontal overflow.
- [x] Compact analytics calendar picker.
  - Done 2026-06-24: month/year popovers size to their longest option instead of inheriting the wide generic popover width, with a viewport cap for small screens.
- [x] Reproducible production dependency resolution.
  - Done 2026-06-24: pin Pydantic to a version compatible with the current FastAPI and pydantic-settings stack so Docker builds do not backtrack across unavailable pydantic-core releases.
- [x] Calculator tab fit.
  - Done 2026-06-24: calculator modes use four equal compact columns, with a two-column fallback on very narrow screens, so `Разделить` stays inside the drawer.
- [x] Branded session loading and favicon.
  - Done 2026-06-24: reloads show a centered `ФинАсист` session check instead of flashing the login form; the login card is compact and centered, and the favicon uses the new orange Cyrillic `Ф` with a mint status accent.
  - Refined 2026-06-24: the login mark is constrained to 52px in widget environments; session checking uses a lightweight transform/opacity pulse with reduced-motion support.
  - Refined 2026-06-24: the sidebar now uses the same branded `Ф` mark instead of the legacy `ФА` badge.
- [x] Receipt discount input and analytics.
  - Done 2026-06-27: receipt item price fields now accept the same math expressions as the main operation amount, including discounted regular-price fields and the finance calculator's amount inputs.
  - Done 2026-06-27: discounted receipt rows store a compact discount type (`promo`, `coupon`, `loyalty_points`) through operations, plans, activity diffs, and API responses. The UI uses inline chips (`Акция`, `Купон`, `Баллы`) instead of selects.
  - Done 2026-06-27: analytics highlights keep the existing total savings KPI and add a compact savings breakdown by discount type for future product reporting.
  - Covered by receipt e2e for receipt-only amount creation and discounted receipt creation with math input plus `Купон` payload.
  - Refined 2026-06-27: regular operations can convert the entered amount into a one-line discounted receipt, keeping discount analytics on receipt items instead of duplicating operation-level discount fields.

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
