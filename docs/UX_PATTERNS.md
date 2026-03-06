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
- dashboard debt-cards visibility

Persistence strategy:
- Source of truth: server-side `user_preferences`
- Fast fallback cache: local storage

Behavior:
- Save changes with debounce to avoid noisy writes
- Restore last state on next open/session
- Provide clear `Reset filters` action

## Action Hierarchy
- Primary CTA is defined at screen-zone level, not as strict single-button rule.
- Canonical paired-primary zones:
- top actions in `Dashboard`/`Operations`: `+ Добавить операцию` and `+ Массовое добавление`
- categories CTA row: `+ Создать группу` and `+ Создать категорию`
- Secondary actions grouped nearby
- Destructive actions require explicit confirmation
- Submit actions (create/update/apply) use one reusable loading flow:
- disable button while request in progress
- show temporary loading label on button
- show unified success/error status messages
- Sidebar user area is not a navigation menu:
- static identity block + dedicated logout icon action

## Destructive Actions and Undo
- Delete actions must show explicit confirmation before execution
- After delete, show bottom session-level toast with undo action
- Toast must include animated countdown progress indicator
- Toast must persist while user switches tabs in current session
- Destructive flow must use one reusable handler, not per-screen copy-paste logic
- Account removal (`Удалить меня`) is a separate destructive flow in Settings `Danger Zone` (explicit confirmation, no undo)

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

## Date Header
- Day/date block is always visible in sidebar (all sections), without `Сегодня:` prefix
- Day/date use `ru-RU` formatting and selected user timezone (fallback to browser timezone)
- Refresh on load and at next local midnight
- If saved timezone is invalid, UI must fallback gracefully to browser timezone without breaking date rendering

## Realtime Search
- Search input for tables/lists is placed in a dedicated row directly above the table
- Operations search is realtime with debounce (no explicit apply button)
- Search targets: operation kind, category name, comment
- Matching text is highlighted with a reusable contrast mark style

## List Loading Pattern (Required)
- Standard pattern for large lists/tables: initial load `20` rows, then incremental load by scroll (`+20` each batch).
- UI keeps backend pagination semantics (page/cursor) internally, but hides classic numbered pagination controls.
- Reuse this pattern in sections where list volume can grow (`Операции`, `Категории`, future debt/history lists).
- Keep virtualization as optional optimization if row count/performance requires it.

## Row Interaction
- Selecting row via checkbox applies persistent selected highlight
- Clicking row body toggles checkbox selection (except clicks on controls)
- Inline row actions appear on hover and for selected row
- Bulk counter in operations is always visible:
- no selection: `Всего: N`
- with selection: `Выбрано: M из N`
- In categories hierarchical table:
- selecting group checkbox selects group and all nested categories
- selecting category checkbox does not auto-select group checkbox
- partial nested selection puts group checkbox in indeterminate state
- selection summary keeps stable typography/spacing between `Ничего не выбрано` and `Выбрано: ...` states
- categories search matches both category names and group names

## Category Inputs
- Group color is chosen via color picker with synchronized hex value
- Category icon is selected from a predefined icon popover, not free text input
- In create operation modal, category is selected via reusable chip-picker flow:
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

## Debt UX Rules (Planned)
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

## Responsive Behavior
- Desktop: sidebar visible
- Mobile: sidebar collapses, priority actions remain accessible
