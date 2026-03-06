# Roadmap

## MVP-1
- Telegram auth
- Dashboard summary (day/week/month/year/`all_time`/custom)
- Operations CRUD + search/filter/sort basics
- Categories + category groups (icon/color), chip rendering
- Bulk actions for operations/categories (select, bulk edit/delete, delete all)
- Batch operation create flow
- Persisted user preferences for display/filter state
- Docker Compose stack (app + postgres + redis)
- List loading standard for high-volume sections: `20` rows initially + `+20` on scroll (infinite scroll; no visible numbered pagination)

## MVP-2
- Google auth provider
- Budgets/limits
- richer reports/charts
- export/import options
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

## Audit Plan (Current)
1. Stabilize shared UI mechanics
- fix one-time binding for reusable popovers (avoid duplicate listeners)
- move modal open/close flows to shared helpers with options payload

2. Reduce module size and coupling
- split `static/js/app-features.js` into focused modules (`operations`, `dashboard`, `preferences`)
- split `static/js/app-core.js` into `state`, `dom-refs`, `format/helpers`
- keep each module under soft 300-400 lines, hard cap 500

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

See detailed execution queue: `docs/AUDIT_TODO.md`
