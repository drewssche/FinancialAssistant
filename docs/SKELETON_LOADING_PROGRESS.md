# Skeleton Loading Progress

Status:
- in progress
- owner: Codex
- scope: phased rollout of cold-load skeletons and lighter inline refresh states

## Agreed UX Contract

- Skeletons are shown on the first cold-load of a section/block instead of empty content or placeholder zeroes.
- Subsequent reloads and filter switches keep the previous data visible; they should not fully collapse back into skeletons.
- Loading state and error state stay visually distinct.
- Initial rollout priority:
  - dashboard
  - debts
- Next phases after this pass:
  - operations and other large lists/tables

## Phase Plan

1. Shared skeleton foundation
- status: done
- add reusable shimmer styles and JS helpers for dashboard/debt placeholders

2. Dashboard cold-load skeletons
- status: done
- KPI period cards
- structure block
- dashboard debts block
- dashboard plans block

3. Debts section cold-load skeletons
- status: done
- debt cards list
- no empty-state flash before first real response

4. Verification and follow-up
- status: in progress
- targeted regression checks
- record remaining rollout for operations/other heavy lists

5. Plans section cold-load skeletons
- status: done
- plans KPI card
- plans list cards
- preserve visible content on later tab/filter switches

6. Analytics section cold-load skeletons
- status: done
- structure donut/list
- calendar totals/grid
- trends range/chart/KPI cards
- preserve visible content on later scope/filter changes

7. Operations section cold-load skeletons
- status: done
- period label
- summary KPI grid
- operations table rows
- preserve visible content on later filter switches and refreshes

8. Dashboard inline refresh-state
- status: done
- keep visible dashboard data during repeat refreshes
- show lightweight panel-level "Обновляется" state instead of collapsing content

9. Analytics inline refresh-state
- status: done
- structure panel
- calendar panel
- trends panel
- keep visible analytics content during repeat loads and tab/period changes

10. Operations inline refresh-state
- status: done
- keep visible operations table and summary during repeat filter/sort reloads
- do not apply the overlay to infinite scroll append loads

## Progress Log

- 2026-03-27: agreed UX direction:
  - skeletons only on first cold-load
  - preserve old data on subsequent reloads
  - start with dashboard and debts
- 2026-03-27: implemented first pass:
  - shared shimmer/skeleton foundation added
  - dashboard cold-load skeletons added for KPI, structure, debts and plans blocks
  - debts section now shows skeleton cards before first real response instead of flashing an empty state
  - logout resets skeleton hydration flags so a new session still gets a true cold-load
- 2026-03-27: verification:
  - `./.venv/bin/pytest tests/e2e/test_debts_flow_e2e.py -q -k "debt_history_action_closes_popover_before_modal or dashboard_debt_actions_load_full_debt_cache_before_open or test_repayment_moves_debt_to_closed"`
  - `./.venv/bin/pytest tests/e2e/test_analytics_mobile_e2e.py -q -k "test_structure_donut_defaults_to_period_total_in_center"`
  - `./.venv/bin/pytest tests/services/test_redis_runtime_advisory_service.py -q`
- 2026-03-27: expanded rollout:
  - full `Планы` section now shows a skeleton KPI card and list on first cold-load
  - full `Аналитика` now shows per-tab cold-load skeletons for `Структура`, `Календарь`, and `Тренды`
  - hydration flags are tracked per analytics tab so filter changes and reloads keep the last real data visible
- 2026-03-27: operations rollout:
  - full `Операции` section now shows a cold-load skeleton for period label, KPI summary and table rows
  - the skeleton only appears before the first uncached load; later filter changes keep already rendered results visible
- 2026-03-27: dashboard inline refresh rollout:
  - dashboard `КПИ периода` and `Структура периода` now use a lightweight inline refresh-state on repeat loads
  - dashboard `Активные долги` and `Ближайшие планы` now keep visible content and show a panel-level updating badge during repeat refreshes
- 2026-03-27: analytics inline refresh rollout:
  - full `Аналитика` now keeps visible content for `Структура`, `Календарь`, and `Тренды` during repeat loads
  - tab switches and period/granularity refreshes now show a lightweight panel-level updating state instead of collapsing content
- 2026-03-27: operations inline refresh rollout:
  - full `Операции` now keeps visible summary and table content during repeat reset-loads
  - inline refresh is limited to full reloads of the section and does not interfere with infinite scroll append behavior

## Next Phase

- use the same pattern selectively for other heavy lists where it improves perceived responsiveness
- optionally tighten visual polish for inline states if the current badge/veil feels too subtle or too strong
