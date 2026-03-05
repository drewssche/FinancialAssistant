# Roadmap

## MVP-1
- Telegram auth
- Dashboard summary (day/week/month/year/custom)
- Operations CRUD + search/filter/sort basics
- Categories + category groups (icon/color), chip rendering
- Bulk actions for operations/categories (select, bulk edit/delete, delete all)
- Batch operation create flow
- Persisted user preferences for display/filter state
- Docker Compose stack (app + postgres + redis)

## MVP-2
- Google auth provider
- Budgets/limits
- richer reports/charts
- export/import options

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

See detailed execution queue: `docs/AUDIT_TODO.md`
