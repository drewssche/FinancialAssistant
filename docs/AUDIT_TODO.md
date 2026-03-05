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
