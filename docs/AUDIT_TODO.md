# Audit TODO

## Post-Audit Priority Queue

1. Fix stale category chip in Dashboard operations table
- Status: done (2026-03-04)
- Problem: after category/group update, `Dashboard -> Операции за период` may keep old category/group chip until full page reload.
- Expected: dashboard operations table must refresh immediately after category/group changes.
- Direction: trigger `loadDashboardOperations()` (or shared data refresh event) after `loadCategories()` updates.

2. Show available category groups in Categories section
- Status: done (2026-03-04)
- Problem: user creates groups but has no always-visible summary of existing groups.
- Expected: grouped categories are visible in table hierarchy (group -> nested categories).
- Direction: render groups and nested categories in one table with shared selection behavior.

2.1 Add group management actions in groups strip
- Status: done (2026-03-04)
- Expected: each group can be edited or deleted without leaving Categories section.
- Direction: inline actions + edit modal + backend PATCH `/api/v1/categories/groups/{group_id}`.

3. One-time binding for icon popovers
- Status: done (2026-03-04)
- Problem: repeated `setupCategoryIconPickers()` can stack listeners on same popover node.
- Expected: each popover has one stable delegated click handler.
- Direction: idempotent initializer (`if (inited) return`) + render-only refresh.

4. Unify category modal API for reuse across contexts
- Status: done (2026-03-04)
- Problem: operation module directly mutates category modal internals.
- Expected: single action `openCreateCategoryModal(options)` with `kind`, `prefillName`, `source`.
- Direction: move prefill logic into categories module and keep cross-module calls declarative.

5. Split oversized frontend modules (rule compliance)
- Status: done (2026-03-04)
- Files above hard threshold:
- `static/js/app-features.js` (reduced: moved operation modal/picker logic to `static/js/app-features-operation-modal.js`; moved dashboard/session to `static/js/app-features-dashboard.js` and `static/js/app-features-session.js`)
- `static/js/app-core.js` (reduced: moved network/action helpers to `static/js/app-core-actions.js`)
- `static/js/app-categories.js` (decomposed into `static/js/app-categories-ui.js` + `static/js/app-categories-data.js`, kept as thin actions facade)
- `static/js/app-bulk.js` (decomposed into `static/js/app-bulk-ui.js` + `static/js/app-bulk-bindings.js`, kept as thin actions facade)
- `static/js/app-init.js` (decomposed into `static/js/app-init-core.js` + `static/js/app-init-features.js` + `static/js/app-init-startup.js`, kept as thin bootstrap facade)
- `static/js/app-bulk-bindings.js` (decomposed into `static/js/app-bulk-bindings-operations.js` + `static/js/app-bulk-bindings-categories.js`, kept as thin binding coordinator)
- Expected: keep modules under soft 300-400 lines; hard threshold 500.
- Direction:
- split `app-features.js` into `operations`, `dashboard`, `session/preferences`
- split `app-core.js` into `state`, `dom`, `utils/net`.

6. Add focused regression tests
- Status: done (2026-03-05)
- Cover create-category-from-operation flow
- Cover dashboard category chip live refresh after category/group update
- Cover chip-picker no-duplication behavior when search is active
- Added:
- `tests/api/test_operation_category_flow.py::test_create_category_then_create_operation_with_it`
- `tests/api/test_operation_category_flow.py::test_group_update_changes_category_group_fields_in_list`
- `tests/e2e/test_chip_picker_no_duplicates_e2e.py::test_operation_category_search_renders_single_chip_without_duplicates`

7. Migrate list/table loading to unified infinite scroll baseline
- Status: in progress (started 2026-03-05)
- Requirement:
- initial batch `20`
- next batches `+20` on scroll
- no visible numbered pagination controls in relevant high-volume sections
- Scope:
- Operations list (implemented: 20 + infinite scroll, numbered pagination hidden)
- Categories list/table (implemented: backend pagination + UI infinite scroll `20/+20`)
- future debts/history lists
- Notes:
- keep backend pagination contract (`page/page_size` or cursor), only UI interaction changes to infinite loading

8. Debt module backend foundation
- Status: in progress (started 2026-03-05)
- Implemented:
- DB schema/migration for `debt_counterparties`, `debts`, `debt_repayments`
- API `/api/v1/debts`:
- `POST /debts`
- `POST /debts/{debt_id}/repayments`
- `GET /debts/cards?include_closed=...`
- service-level counterparty deduplication (`name_ci`) and repayment overpay guard
- API tests for create/list/repayment/closed-card flow
- Frontend debts section skeleton:
- sidebar navigation item `Долги`
- cards render from `GET /api/v1/debts/cards`
- `Внести погашение` modal and submit flow
- operation create modal mode switch (`Обычная операция` / `Долг`) with `POST /api/v1/debts`
- UX refinements:
- debt search input + status segmented filter (`Активные/Все/Закрытые`)
- due-priority highlighting for debt rows (`overdue`/`soon`)
- compact repayment history hints (count + last repayment date)
- Added e2e:
- `tests/e2e/test_debts_flow_e2e.py::test_create_debt_from_operation_modal`
- `tests/e2e/test_debts_flow_e2e.py::test_repayment_moves_debt_to_closed`
- Debt CRUD follow-up:
- `PATCH /api/v1/debts/{debt_id}` + edit debt modal
- `DELETE /api/v1/debts/{debt_id}` + UI delete flow
- Added e2e:
- `tests/e2e/test_debts_flow_e2e.py::test_edit_and_delete_debt`
- Next:
- debt cards UX refinements (denser history/pagination if needed)
- expand debt e2e with edge cases (overpay rejection, counterparty rename merge)

9. UX/observability issues from manual review (2026-03-05)
- Status: todo
- Improve startup partial-load toast:
- current message `Часть данных не загружена: Ошибка запроса` is not actionable
- show endpoint/context and http status so user understands what exactly failed
- Investigate `Долги` section request error:
- on opening `Долги`, request fails with generic `Ошибка запроса`
- identify root cause and ensure readable user-facing error
- UI direction change request:
- move away from native `select` controls in high-frequency flows
- align UI system/docs with preferred alternatives (segmented/chips/popovers/custom pickers)
- include this in next UI pass after debt CRUD baseline

10. Debt UX follow-ups from manual review (2026-03-05)
- Status: todo
- Counterparty search parity check:
- keep debts search on same reusable pattern/mechanics as operations search (shared debounce + `highlightText`, avoid per-section hardcoded variants)
- Reuse debt create modal for debt edit flow:
- avoid separate edit modal, reduce UI/code duplication
- keep create/edit states in one component with mode-aware title/CTA
- Improve debt repayment UX:
- design modern repayment sheet with stronger visual cues (direction/status accents, iconography, quick preset amounts, outstanding meter)
- Debt card header wording refinement:
- split `Выдано/взято` into separate metrics for clarity (e.g., `Выдано`, `Взято`, `Погашено`, `Остаток`)
- Dashboard debt visibility:
- decide and implement debt-aware widgets in dashboard/KPI layer (separate debt cards or explicit debt-impact toggle for balance/tables)

11. Sorting strategy unification for lists/tables (2026-03-05)
- Status: todo
- Add consistent priority sorting presets across sections:
- Debts: `overdue -> soon -> future -> none`, then nearest due date
- Operations: reusable sort presets (`date`, `amount`, `priority/risk`) with same UI pattern
