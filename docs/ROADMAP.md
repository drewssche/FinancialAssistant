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
- align critical actions with Telegram interaction model (`BackButton`, `MainButton`) where useful
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

See detailed execution queue: `docs/AUDIT_TODO.md`
