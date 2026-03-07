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
- Operations receipt detail:
- optional receipt line items in operation
- reusable position catalog (chips/templates)
- per-position price history
- discrepancy warning (`operation amount` vs `receipt total`) with non-blocking save
- Debt management module (`Долги`) with:
- counterparty cards
- debt create flow (`дал`/`взял`)
- repayment flow (`вернули`/`вернул`)
- outstanding progress and due-date tracking

## Feature Draft: Debts (Design Approved, Implementation Pending)
1. Navigation and information architecture
- New sidebar section: `Долги`
- Dashboard keeps debt widget compact (only active/high-priority debt cards), full list stays in `Долги`

2. Operation modal integration
- Operation modal adds mode switch: `Обычная операция` / `Долг`
- In `Долг` mode:
- hide categories/tags inputs
- show debt-specific fields (`Кто/Кому`, `Сумма`, `Когда`, `До какого числа`, `Комментарий`)

3. Counterparty reuse and anti-duplication
- Counterparty input uses suggestions from existing debt cards
- New debt with existing counterparty updates that card (adds new debt row), not a duplicate card

4. Repayment mechanics
- Debt card stores:
- principal total
- repaid total
- outstanding total
- Debt card is active while outstanding > 0
- When outstanding becomes 0, card is hidden from dashboard widget and marked closed in debts history

## MVP-3
- deeper Telegram Mini App optimization
- async jobs and notifications
- advanced analytics and recommendations
- optional position-level analytics (backlog candidate, depends on product demand)

## Audit Plan (Current)
1. Stabilize shared UI mechanics
- fix one-time binding for reusable popovers (avoid duplicate listeners)
- move modal open/close flows to shared helpers with options payload

2. Reduce module size and coupling
- continue splitting `static/js/app-features.js` into focused modules (`operations`, `dashboard`, `preferences`, `item-catalog`)
- done: Item Catalog extracted to `static/js/app-features-item-catalog.js`
- done: operations flow extracted to `static/js/app-features-operations.js`
- split `static/js/app-core.js` into `state`, `dom-refs`, `format/helpers`
- keep each module under soft 300-400 lines, hard cap 500; current heavy modules above hard cap: `app-features-operation-modal.js`, `app-features-item-catalog.js`, `app-features-operations.js`, `templates/modals.js`, `app-init-features.js`

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

See detailed execution queue: `docs/AUDIT_TODO.md`
