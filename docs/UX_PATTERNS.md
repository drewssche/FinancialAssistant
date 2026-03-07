# UX Patterns

## Persisted View State (Required)
User display settings must persist until user changes them.

MVP-1 persisted items:
- dashboard period (`day`, `week`, `month`, `year`, `all_time`, `custom`)
- operations filters
- operations sorting
- active main section/tab
- ui timezone
- ui currency + symbol position
- ui scale
- dashboard analytics block visibility
- dashboard debt-cards visibility
- dashboard operations block visibility
- dashboard operations row limit (`5/8/12`)
- analytics period/granularity and calendar month anchor
- analytics top insight limits (`top operations`, `top positions`)
- admin users filter in admin section (`pending/approved/rejected/all`)

Persistence strategy:
- Source of truth: server-side `user_preferences`
- Fast fallback cache: local storage

Behavior:
- Save changes with debounce to avoid noisy writes
- Restore last state on next open/session
- Provide clear `Reset filters` action

Settings UX additions:
- dashboard visibility toggles should preview in-place without full page reload
- analytics top limits are applied to insight lists after save/apply
- scale slider uses fine step (`1%`) and must not break page background continuity

## Access Approval UX
- Authorization and product access are separated:
- user can authenticate, but usage access depends on status
- statuses:
- `pending` -> show waiting message, hide workspace
- `approved` -> normal workflow
- `rejected` -> show denied message, hide workspace
- Admin workflow:
- pending queue should be first default filter
- status change actions require immediate list refresh
- destructive action `Delete user` requires explicit confirmation

## Navigation Priority
- Default landing section is always `Dashboard` for first open/session reset.
- Sidebar should support semantic grouped blocks with headers when item count grows.
- `Analytics` is a first-level section, but not the startup override for Dashboard.

## Action Hierarchy
- Primary CTA is defined at screen-zone level and remains single per active section.
- Secondary CTA is allowed in the same zone when it is part of the same scenario.
- Canonical mapping (current baseline):
- `Dashboard`/`Operations`: primary `+ Добавить операцию`, secondary `+ Массовое добавление`
- `Categories`: primary `+ Создать категорию`, secondary `+ Создать группу`
- `Debts`: primary `+ Новый долг`
- `Item Catalog`: primary `+ Создать позицию`, secondary `+ Создать источник`
- Secondary actions must stay grouped near primary in shared top actions zone
- Destructive actions require explicit confirmation
- Submit actions (create/update/apply) use one reusable loading flow:
- disable button while request in progress
- show temporary loading label on button
- show unified success/error status messages
- Sidebar user area is not a navigation menu:
- static identity block + dedicated logout icon action

## Position Catalog Consistency
- `+ Создать источник` is placed next to `+ Создать позицию` in section-level top CTA zone.
- In create/edit position modal, field `Источник` reuses chip-picker interaction from operation modal/category flow:
- trigger input + popover suggestions
- realtime search
- create-if-missing chip action
- deterministic close on outside click / `Esc` / chip selection
- Source creation modal keeps simple text input flow (without chip-picker popover).
- Create/edit source-position flows include live preview of resulting table element.
- Position history modal matches `Позиции чека` interaction style and renders source as chip.
- Item Catalog interaction settings (`sort`, `collapsed groups`, source-group create) persist with debounce to avoid noisy `preferences` writes.
- Item Catalog search should prefer local filtering when full catalog snapshot is already loaded; server search is fallback when local snapshot is incomplete.

## Destructive Actions and Undo
- Delete actions must show explicit confirmation before execution
- After delete, show bottom session-level toast with undo action
- Toast must include animated countdown progress indicator
- Toast must persist while user switches tabs in current session
- Destructive flow must use one reusable handler, not per-screen copy-paste logic
- Account removal (`Удалить меня`) is a separate destructive flow in Settings `Danger Zone` (explicit confirmation, no undo)
- Post-mutation refresh should be section-aware: refresh active section data first; avoid unconditional cross-section reloads

## Money Formatting
- All money values must use one shared formatter driven by user settings
- Currency setting supports at least `BYN`, `RUB`, `USD`, `EUR`
- Currency symbol position is configurable (`prefix`/`suffix`)
- For current RU/BY UX baseline, default display uses suffix style (`1 234,56 Br`)
- Amount inputs show currency adornment as visual hint only; raw numeric value remains clean for API payload

## Time Filters
- Dashboard and operations period controls should support:
- current day
- current week
- current month
- current year
- all time (from first user operation to current date)
- custom range (`date_from/date_to`)
- Period switcher is shown in the operations table panel where result data is displayed
- Current period label is always visible above the table:
- for `День`: `DD.MM.YYYY`
- for other ranges: `DD.MM.YYYY - DD.MM.YYYY`

## Analytics Calendar Pattern (Planned Baseline)
- Calendar tab keeps only grid controls:
- `Grid controls`: calendar view (`Месяц`/`Год`) + prev/current/next navigation for grid only
- Monthly view uses calendar grid with Monday-first week (`Пн..Вс`).
- Each day cell includes:
- income total
- expense total
- operations count
- Each week row has right-side totals:
- week income
- week expense
- week operations count
- Calendar summary is KPI-style cards (not plain sentence text) and follows selected grid view (month/year):
- primary KPI cards: income/expense/balance/operations
- secondary compact metric: single period result (`Профицит`/`Дефицит`/`Нулевой баланс`)
- Year view uses month cards (`12` cells) with the same metrics at month granularity.
- Empty days are rendered as explicit zero values for visual continuity.

## Date Header
- Day/date block is always visible in sidebar (all sections), without `Сегодня:` prefix
- Day/date use `ru-RU` formatting and selected user timezone (fallback to browser timezone)
- Refresh on load and at next local midnight
- If saved timezone is invalid, UI must fallback gracefully to browser timezone without breaking date rendering

## Realtime Search
- Search input for tables/lists is placed in a dedicated row directly above the table
- Operations search is realtime with debounce (no explicit apply button)
- Operations realtime search persists filters with debounced preferences write (typing burst should not trigger one `PUT` per keystroke)
- Search targets: operation kind, category name, comment
- Matching text is highlighted with a reusable contrast mark style
- Position catalog search targets both source names and position names
- For grouped tables (source -> positions), active search temporarily auto-expands matched groups

## Analytics Trends Pattern (Planned Baseline)
- Trend panel supports `day/week/month/year/custom` granularity.
- Trend controls must be semantically separated:
- `Окно` (analysis window/range)
- `Шаг` (bucket size)
- Baseline visual:
- income and expense as bars
- balance as line
- Trend panel should show period-over-period delta near chart headline.
- Clicking chart bucket should open or focus `Операции` with matching date filter.

## Analytics Information Architecture
- Analytics section uses internal tabs to keep information density manageable.
- Baseline tabs:
- `Общий`: period KPI controls and compact period summary
- `Календарь`: month/year matrix + week totals + grid-view totals
- `Операции`: top operations, categories, anomalies, positions insights
- `Тренды`: expanded charts and period-over-period comparisons
- Dashboard remains default landing section; analytics is deep-dive only.

## List Loading Pattern (Required)
- Standard pattern for large lists/tables: initial load `20` rows, then incremental load by scroll (`+20` each batch).
- UI keeps backend pagination semantics (page/cursor) internally, but hides classic numbered pagination controls.
- Reuse this pattern in sections where list volume can grow (`Операции`, `Категории`, `Долги` cards, debt history timeline).
- Keep virtualization as optional optimization if row count/performance requires it.

## Row Interaction
- Inline row actions appear on hover and for selected row
- Operations table supports checkbox selection and bulk actions.
- Categories table does not use checkbox-based bulk selection; actions are row-level and section-level (`Удалить все`).
- categories search matches both category names and group names
- grouped table interaction baseline (introduced in Position Catalog):
- parent/group row can be collapsed/expanded with chevron control
- collapsed state persists in user preferences
- when search is active, manual collapse is disabled and matched groups stay expanded
- grouped table can expose explicit group actions (`Свернуть все` / `Развернуть все` / `Сброс`) near search
- grouped table can expose local sort presets; active sort preset must persist in user preferences

## Category Inputs
- Group color is chosen via color picker with synchronized hex value
- Category icon is selected from a predefined icon popover, not free text input
- In create/edit operation modals, category is selected via reusable chip-picker flow:
- search input (realtime filter)
- single result list sorted by usage frequency (frequent categories first)
- when search has no match, show chip action `Создать категорию «...»` and open category modal prefilled
- Operation preview row must always include category chip with the same renderer as operations tables
- In create category modal, group is selected via the same chip-picker interaction pattern:
- trigger input + popover
- `Без группы` chip
- group chips filtered by selected kind
- popover closes on outside click / `Esc` / chip selection
- outside click close must also work for clicks in modal area outside picker

## Receipt Line Items (MVP)
- Receipt details are optional inside operation create/edit flow.
- Receipt item picker reuses chip-picker mechanics (search, debounce, single list, create-if-missing).
- Receipt row has two linked pickers:
- `Источник` (source chips)
- `Позиция` (item chips filtered by selected source when source is set)
- Editing rule:
- on chip insert, prefill name + latest known price, both editable
- user edits must not overwrite historical prices; new price is appended to history
- if user creates a missing position from picker (`+ Создать позицию`), it must be available in subsequent receipt rows immediately (optimistic local template list update before operation save)
- Amount/discrepancy rule:
- save is allowed when operation amount and receipt total differ
- discrepancy must be visually explicit before submit
- quick action should exist to copy receipt total into operation amount
- Picker close rule (required):
- popover closes deterministically on first outside click, on `Esc`, and on chip selection
- no repeated outside clicks required to close
- Operations table note/comment column must show only user note text (no auto-appended receipt suffix like `Чек: N поз.`).
- If operation has receipt items, row hover actions should include `Позиции` button that opens read-only receipt item list.
- Scope guard:
- no per-item category in MVP
- no item-level analytics in MVP (backlog)

## Debt UX Rules (Implemented Baseline)
- Debt creation flow must be explicit and separate from category logic.
- Suggested interaction:
- mode switch in operation modal (`Обычная операция` / `Долг`)
- repayment is a dedicated action from debt card, not hidden side effect
- Counterparty deduplication:
- if user types existing counterparty name, append debt row to existing card
- if new name, create new card
- Card state:
- active while outstanding amount > 0
- closed when outstanding amount reaches 0
- Dashboard visibility:
- show only active cards with nearest due dates / overdue first
- keep full history in `Долги` section to avoid dashboard overload
- Dashboard debt cards render one compact row per active debt record (grouped by counterparty), so mixed directions are not aggregated into one repayment ratio
- Due date semantics:
- visual priority for overdue/near-due cards
- non-blocking reminders in UI (toast/info badge), no forced modal interruptions
- Search in debts uses the same reusable highlight pattern as operations search (`core.highlightText`)
- Repayment quick presets (`25%`, `50%`, `Весь остаток`) are derived from current outstanding amount from state/API and must update amount input + delta hints in one click

## Dashboard Content Strategy
- Dashboard is overview-first and must stay lighter than dedicated working sections.
- Keep debt cards and analytics preview compact; deep drill-down belongs to `Долги` and `Аналитика`.
- Operations block on dashboard should be limited to recent/context rows; main operations workflow remains in `Операции`.

## Responsive Behavior
- Desktop: sidebar visible
- Mobile: sidebar collapses, priority actions remain accessible
