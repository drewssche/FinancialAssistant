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
- Status: in progress (updated 2026-03-07)
- Files above hard threshold:
- `static/js/app-features.js` (reduced: moved operation modal/picker logic to `static/js/app-features-operation-modal.js`; moved dashboard/session to `static/js/app-features-dashboard.js` and `static/js/app-features-session.js`; moved Item Catalog feature block to `static/js/app-features-item-catalog.js`; moved operations flow to `static/js/app-features-operations.js`)
- `static/js/app-core.js` (reduced: moved network/action helpers to `static/js/app-core-actions.js`)
- `static/js/app-categories.js` (decomposed into `static/js/app-categories-ui.js` + `static/js/app-categories-data.js`, kept as thin actions facade)
- `static/js/app-bulk.js` (decomposed into `static/js/app-bulk-ui.js` + `static/js/app-bulk-bindings.js`, kept as thin actions facade)
- `static/js/app-init.js` (decomposed into `static/js/app-init-core.js` + `static/js/app-init-features.js` + `static/js/app-init-startup.js`, kept as thin bootstrap facade)
- `static/js/app-bulk-bindings.js` (decomposed into `static/js/app-bulk-bindings-operations.js` + `static/js/app-bulk-bindings-categories.js`, kept as thin binding coordinator)
- `static/js/app-init-features.js` (reduced from 608 to 367 by extracting debt/picker bindings)
- `static/js/app-categories-ui.js` (reduced from 740 to 471 by extracting icon/table ui modules)
- `static/js/app-core.js` (reduced from 575 to 430 by extracting shared utils)
- `static/js/app-features-debts.js` (reduced from 539 to 347 by extracting debt cards renderer)
- `static/js/app-features-operation-modal.js` (reduced from 615 to 460 by extracting preview module)
- `static/index.html` reduced to thin shell (from 831 to 69 lines) via template modules
- Expected: keep modules under soft 300-400 lines; hard threshold 500.
- Direction:
- split `app-features.js` into `operations`, `dashboard`, `session/preferences`, `item-catalog`
- split `app-core.js` into `state`, `dom`, `utils/net`.
- Remaining files over 500:
- `static/js/app-features-operation-modal.js` (`1338`)
- `static/js/app-features-operations.js` (`496`)
- `static/js/app-features-item-catalog.js` (`821`)
- `static/js/templates/modals.js` (`550`)
- `static/js/app-init-features.js` (`505`)

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
- Status: done (updated 2026-03-06)
- Requirement:
- initial batch `20`
- next batches `+20` on scroll
- no visible numbered pagination controls in relevant high-volume sections
- Scope:
- Operations list (implemented: 20 + infinite scroll, numbered pagination hidden)
- Categories list/table (implemented: backend pagination + UI infinite scroll `20/+20`)
- Debts cards list (implemented: client render batching `20/+20` via sentinel)
- Debt history modal timeline (implemented: event batching `20/+20` via sentinel in scroll container)
- Added e2e regression:
- `tests/e2e/test_debts_flow_e2e.py::test_debts_cards_infinite_scroll_loads_next_batch`
- `tests/e2e/test_debts_flow_e2e.py::test_debt_history_infinite_scroll_loads_next_batch`
- Notes:
- keep backend pagination contract (`page/page_size` or cursor), only UI interaction changes to infinite loading

8. Debt module backend foundation
- Status: done (updated 2026-03-06)
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
- Implemented (2026-03-06):
- debt cards/history pagination refinements delivered (`20/+20` batching with sentinels in debts section and history modal)
- added debt e2e edge-cases:
- `tests/e2e/test_debts_flow_e2e.py::test_overpay_creates_reverse_direction_debt`
- `tests/e2e/test_debts_flow_e2e.py::test_edit_counterparty_name_merges_with_existing_card`
- `tests/e2e/test_debts_flow_e2e.py::test_debts_cards_infinite_scroll_loads_next_batch`
- `tests/e2e/test_debts_flow_e2e.py::test_debt_history_infinite_scroll_loads_next_batch`

9. UX/observability issues from manual review (2026-03-05)
- Status: done (updated 2026-03-06)
- Improve startup partial-load toast:
- current message `Часть данных не загружена: Ошибка запроса` is not actionable
- show endpoint/context and http status so user understands what exactly failed
- Investigate `Долги` section request error:
- on opening `Долги`, request fails with generic `Ошибка запроса`
- identify root cause and ensure readable user-facing error
- Implemented (2026-03-06):
- `refreshAll()` now reports failed blocks with context:
- `Часть данных не загружена (N/5): Дашборд: ...; Долги: ...`
- details include status and endpoint from `requestJson` error format
- opening `Долги` now shows explicit section-scoped error:
- `Не удалось открыть раздел «Долги»: ...`
- UI direction change request:
- move away from native `select` controls in high-frequency flows
- align UI system/docs with preferred alternatives (segmented/chips/popovers/custom pickers)
- this is a product/UI evolution track, moved to dedicated backlog item (see #20)

10. Debt UX follow-ups from manual review (2026-03-05)
- Status: done (updated 2026-03-06)
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
- Implemented (2026-03-06):
- debts search now uses server-side `q` + shared realtime flow with request cancellation; renderer keeps `highlightText` and no extra client-side query filtering
- card-level aggregate metrics were intentionally removed from counterparty header (they were semantically confusing for mixed lend/borrow cards); details stay per-debt row
- debt edit now fully reuses create debt modal flow; legacy `editDebtModal` markup/handlers removed
- debt history timeline now renders in strict chronological order (`date -> created_at -> type -> id`) with explicit initial step and per-step `Остаток после шага`
- repayment modal quick preset buttons (`25%/50%/Весь остаток`) now calculate amount from raw debt state (not formatted DOM text)
- debt terminology labels are now unified via shared debt-ui helpers across dashboard/debts/modals/history (`Я дал/Я взял`, `Мне должны/Я должен`)
- repayment and issuance events in history now use direction-aware wording (`Погашение: мне вернули/я вернул`, `Добавление: я дал/взял в долг`)
- Added e2e regression:
- `tests/e2e/test_debts_flow_e2e.py::test_repayment_presets_fill_amount_from_current_outstanding`
- `tests/e2e/test_debts_flow_e2e.py::test_debt_history_uses_directional_event_labels`
- dashboard debt visibility delivered via debt-aware KPI cards and compact active-debts panel in dashboard

11. Sorting strategy unification for lists/tables (2026-03-05)
- Status: done (updated 2026-03-06)
- Add consistent priority sorting presets across sections:
- Debts: `overdue -> soon -> future -> none`, then nearest due date
- Operations: reusable sort presets (`date`, `amount`, `priority/risk`) with same UI pattern
- Implemented (2026-03-06):
- unified segmented sort controls added:
- operations: `По дате` / `По сумме` / `Риск`
- debts: `Приоритет` / `По сумме` / `По имени`
- operations presets are persisted in preferences (`operations.sort_preset`) and applied in list query/render flow
- debts presets are persisted in preferences (`debts.sort_preset`) and applied in card renderer
- Added e2e regression:
- `tests/e2e/test_sort_preset_persistence_e2e.py::test_operations_sort_preset_persists_after_reload`
- `tests/e2e/test_sort_preset_persistence_e2e.py::test_debts_sort_preset_persists_after_reload`

12. Search optimization alignment (2026-03-06)
- Status: done (updated 2026-03-06)
- Implemented:
- Operations search moved to server-side query (`q`) with backend filtering by note/category/kind and RU prefixes (`доход`/`расход`)
- Added API regression:
- `tests/api/test_operations_api.py::test_operations_search_by_note_category_and_kind_ru`
- Debts search moved to server-side query (`q`) in `GET /api/v1/debts/cards`
- Added API regression:
- `tests/api/test_debts_api.py::test_debts_cards_search_by_counterparty_note_and_direction`
- Frontend realtime search now uses request cancellation (`AbortController`) for:
- operations list
- categories table
- debts cards

13. Template layer extraction for maintainability (2026-03-06)
- Status: done
- Implemented:
- Introduced template layer:
- `static/js/templates/shell.js`
- `static/js/templates/modals.js`
- `static/js/app-templates.js`
- `static/index.html` now contains only login block + template roots + script includes
- Risk note:
- template files can become new monoliths; keep split by domain (`shell`, `modals`, future `sections/*`)

14. Test baseline after refactor (2026-03-06)
- Status: done
- Result:
- `./.venv/bin/pytest -q` => `30 passed`
- Known warning:
- third-party `python-jose` deprecation (`datetime.utcnow`) tracked separately, no functional regressions

15. Cache rollout plan (2026-03-06)
- Status: done (updated 2026-03-06)
- Goal:
- reduce repeated API/DB load while preserving correctness after mutations
- Phase A (frontend, low-risk):
- introduce per-section in-memory cache policy table (what is cached, TTL, invalidation event)
- start with `debts cards` and `categories list` (read-heavy, bounded payload)
- Phase B (backend, targeted):
- add Redis cache for expensive aggregated dashboard reads (summary/card totals)
- cache key must include `user_id + period/filter params + schema/version`
- Implemented (2026-03-06):
- `DashboardService.get_summary` now uses Redis cache key format `dashsum:v1:u:{user}:p:{period}:from:{date_from}:to:{date_to}` with TTL `60s`
- cache invalidation wired after successful mutations in:
- `OperationService.create/update/delete`
- `DebtService.create/add_repayment/update/delete`
- Phase C (stability/guardrails):
- add automated checks for stale-data regressions after create/update/delete flows
- add telemetry counters (`cache_hit`, `cache_miss`, `cache_invalidate`) for key endpoints
- Implemented (2026-03-06):
- backend telemetry for dashboard summary:
- counters: `cache_hit_total`, `cache_miss_total`, `cache_invalidate_total`, `cache_invalidated_keys_total`
- latency windows: `latency_total` and `latency_miss_compute` with `avg/min/max/p50/p95`
- API endpoint: `GET /api/v1/dashboard/summary/metrics`
- stale-cache regression API tests for CRUD invalidation:
- `tests/api/test_dashboard_api.py::test_dashboard_summary_cache_is_invalidated_after_operation_update_and_delete`
- `tests/api/test_dashboard_api.py::test_dashboard_summary_cache_is_invalidated_after_debt_mutations`
- Done criteria:
- documented cache map in docs
- no stale UI after CRUD (validated by tests/manual checklist)
- measurable gain on repeated reads (latency and request count)

16. High ROI optimization track (2026-03-06)
- Status: done (updated 2026-03-06)
- Ranking (`effort -> impact`):
- P1: add DB composite indexes for hot API filters/sorts
- P1: introduce Redis cache for dashboard aggregate endpoints
- P1: unify server-side search contracts + add UI request cancellation (`AbortController`)
- P2: add render batching / optional virtualization for large tables
- Implemented:
- added Alembic migration `20260306_0006_perf_indexes.py` with composite indexes for `operations`, `debts`, `categories`
- added Redis-backed cache for dashboard aggregate endpoint with mutation invalidation hooks
- Execution rule:
- do not start next item without baseline and post-change metrics
- Metrics to track:
- API latency p50/p95
- request count per user action
- UI render/interaction timing on list-heavy screens

17. Baseline/Post-change metrics snapshot (2026-03-06)
- Status: done
- Method:
- local benchmark with seeded data (30 operations + 1 active debt), then:
- baseline = 40x `GET /api/v1/dashboard/summary?period=all_time`
- mutation = 1x `POST /api/v1/operations`
- post-change = 20x `GET /api/v1/dashboard/summary?period=all_time`
- Metrics source: `GET /api/v1/dashboard/summary/metrics`
- Baseline snapshot:
- `cache_hit_total=39`, `cache_miss_total=1`, `cache_invalidate_total=0`, `hit_ratio=0.975`
- `latency_total.p50=0.014ms`, `p95=0.026ms`
- `latency_miss_compute.p50=3.423ms`, `p95=3.423ms`
- Post-change snapshot:
- `cache_hit_total=58`, `cache_miss_total=2`, `cache_invalidate_total=1`, `cache_invalidated_keys_total=1`, `hit_ratio=0.9667`
- `latency_total.p50=0.014ms`, `p95=0.043ms`
- `latency_miss_compute.p50=2.038ms`, `p95=3.423ms`
- `endpoint_request_totals` now available in same payload (example sample: `GET /api/v1/dashboard/summary=8`, `POST /api/v1/operations=1`)

18. Request count per user action (2026-03-06)
- Status: done
- Script:
- `PYTHONPATH=. ./.venv/bin/python scripts/measure_request_scenarios.py`
- Script docs:
- `scripts/README.md`
- Output snapshot:
- `Open Dashboard`: `GET /api/v1/dashboard/summary=1`, `GET /api/v1/debts/cards=1`, `GET /api/v1/operations=1`
- `Operations Search`: `GET /api/v1/operations=1`
- Automated budget gate extended:
- `tests/api/test_request_budgets_api.py::test_request_budget_section_switch_no_front_cache`
- `tests/api/test_request_budgets_api.py::test_request_budget_section_switch_front_cache_ttl`
- guard verifies request-count delta for section-switch flow (`operations/debts/categories`) with and without frontend TTL cache reuse
- canonical budget source is now centralized in:
- `docs/REQUEST_BUDGETS.md` (JSON block + table), consumed directly by `tests/api/test_request_budgets_api.py`
- `Create Operation + Refresh`: `POST /api/v1/operations=1`, `GET /api/v1/dashboard/summary=1`, `GET /api/v1/operations=2`
- `Debts Search`: `GET /api/v1/debts/cards=1`
- Notes:
- request profile matches current frontend flows after `AbortController` integration (single final request per search action)
- Regression guard:
- added API budget tests to lock request ceilings:
- `tests/api/test_request_budgets_api.py`
- Conclusion:
- cache behavior is correct (`invalidate` after mutation + one recompute miss + subsequent hits)
- current miss-compute path stays sub-5ms in local benchmark
- Next:
- lightweight ops policy for current scale (`~2-3` users):
- keep CI budget/cache guardrails as mandatory gate
- skip full-time production monitoring for now
- run weekly manual health check (`GET /api/v1/dashboard/summary/metrics` + quick UI response sanity)
- revisit full monitoring/alerts at `20+` active users or on first performance complaints
- helper command for weekly check:
- `TOKEN=... BASE_URL=http://localhost:8001 ./scripts/health_check.sh`
- release gate checklist documented in:
- `docs/RELEASE_CHECKLIST.md`

19. Frontend cache policy and bounded read-through cache (2026-03-06)
- Status: done
- Why next (ROI):
- closes open Phase A from item #15 with low risk and immediate reduction of repeated reads on section toggles
- Scope (first pass):
- document cache policy table (`dataset -> ttl -> invalidation events -> fallback`)
- implement read-through in-memory TTL cache for:
- `GET /api/v1/debts/cards` (short TTL, e.g. 15-30s)
- `GET /api/v1/categories` list/table payloads (short TTL, e.g. 30-60s)
- mandatory invalidation triggers:
- debt create/update/delete/repayment
- category/group create/update/delete
- user preference changes that affect visibility/filtering
- Done criteria:
- no stale data after mutations (API/e2e regression)
- measurable drop in repeated GET count for section switching scenario
- docs synchronized (`ENGINEERING_PRINCIPLES`, `UX_PATTERNS`, `UI_SYSTEM`, `AUDIT_TODO`)
- Implemented (2026-03-06):
- added shared frontend cache helpers in `core`:
- `getUiRequestCache`, `setUiRequestCache`, `invalidateUiRequestCache`
- bounded cache map with FIFO eviction (`max_entries=80`)
- enabled read-through TTL cache for debts cards:
- key includes `include_closed + q`, TTL `20s`
- enabled read-through TTL cache for operations list:
- key includes full list query (`page/page_size/sort/date bounds/kind/q`), TTL `15s`
- enabled read-through TTL cache for categories:
- groups TTL `60s`, catalog TTL `60s`, table-page payload TTL `45s`
- explicit invalidation wired for:
- operation create/update/delete (including undo recreate)
- debt create/update/delete/repayment
- category/group create/update/delete and bulk operations
- preferences load/save and logout reset
- category/group mutations also invalidate operations list cache (search-by-category consistency)
- Metrics snapshot (2026-03-06, script-based):
- command: `PYTHONPATH=. ./.venv/bin/python scripts/measure_request_scenarios.py`
- section switch baseline (no front cache):
- `GET /api/v1/operations=2`
- `GET /api/v1/debts/cards=2`
- `GET /api/v1/categories/groups=2`
- `GET /api/v1/categories=4`
- section switch with front TTL cache:
- `GET /api/v1/operations=1`
- `GET /api/v1/debts/cards=1`
- `GET /api/v1/categories/groups=1`
- `GET /api/v1/categories=2`
- Result:
- repeated section revisit read load reduced by ~50% for measured endpoints

20. UI controls modernization track (post-audit UX backlog)
- Status: pending
- Scope:
- replace remaining native `select` controls in high-frequency user flows with unified segmented/chips/popover/custom pickers
- keep visual/interaction patterns aligned with `docs/UI_SYSTEM.md` and `docs/UX_PATTERNS.md`
- Guardrails:
- do not regress keyboard accessibility/focus behavior
- add/update focused e2e checks for changed controls

21. Operations receipt line-items and position catalog (2026-03-06)
- Status: in progress
- Scope decisions (agreed):
- add optional receipt line-items inside operation create/edit flow
- operation amount can be manual or derived from receipt total
- allow save on discrepancy with explicit warning
- source-grouped reusable position templates with immutable price history
- add separate position catalog view/API (history + usage frequency)
- Explicitly out of MVP:
- no category per line-item
- no position-level analytics (moved to future backlog)
- Implemented (backend foundation, 2026-03-06):
- DB models/migration:
- `operation_receipt_items`
- `operation_item_templates`
- `operation_item_prices`
- operations API extended with receipt payload support (`receipt_items`)
- operation output includes `receipt_total` and `receipt_discrepancy`
- receipt line item price is persisted on operation save:
- in operation receipt snapshot (`unit_price`)
- in reusable template price history (`operation_item_prices`)
- new API:
- `GET /api/v1/operations/item-templates`
- `GET /api/v1/operations/item-templates/{template_id}/prices`
- Implemented (frontend MVP slice, 2026-03-06):
- create operation modal now has optional `Чек (позиции)` block
- receipt rows use inline fields in one line (`позиция`, `цена`, `кол-во`)
- next empty row is auto-added when `позиция` is filled; large manual `+ добавить позицию` CTA removed as redundant
- line items support inline quantity/price editing and auto line totals
- receipt summary shows `Сумма чека` and non-blocking `Расхождение`
- quick action `Подтянуть сумму из чека` fills operation amount field
- interactive position picker moved to chip-style popover (same UX family as category picker)
- Added fix pass (2026-03-06):
- `+ Создать позицию` now performs optimistic local template upsert, so next rows can reuse it immediately before operation save
- receipt position popover close now uses deterministic rule (`outside active name cell/picker` closes on first click)
- local template list is merged with server hints to keep newly created local suggestions available during current modal session
- receipt rows now support optional `источник` picker; source chips are used as grouping filter for position chips in the same row
- receipt read-only modal now shows source chip per item when available
- Added QA/e2e pass (2026-03-06):
- `tests/e2e/test_receipt_picker_store_scope_e2e.py` covers:
- source-scoped receipt position chips in picker
- optimistic `+ Создать позицию` reuse in next rows
- outside-click close behavior for receipt name popover
- Added UX follow-up (2026-03-06):
- sidebar now includes dedicated `Каталог позиций` section under `Категории`
- edit operation modal now has full receipt block (`источник/позиция/цена/кол-во`) with same picker mechanics as create modal
- edit operation `PATCH` now sends `receipt_items` payload, so receipt rows can be edited in-place
- position catalog table switched to grouped source view with collapsible groups and compact group aggregates
- grouped table behavior (collapse persistence + search auto-expand) marked as reusable pattern for future `Категории` table migration
- Added table controls follow-up (2026-03-06):
- position catalog now has explicit sort presets (`Частота`, `Недавние`, `Имя`)
- sort preset is persisted in user preferences (`ui.item_catalog_sort_preset`)
- added group actions (`Свернуть все`, `Развернуть все`)
- group actions are disabled during active search to preserve deterministic auto-expand behavior
- item rows now have hover actions (`Редактировать`, `Удалить`)
- catalog has dedicated actions: top CTA `+ Создать позицию`, section-level `Удалить все`, backend CRUD endpoints for templates
- Next done criteria for #21:
- position catalog screen/API follow-up (history + usage frequency) as separate increment
