# UX Patterns

## Persisted View State (Required)
User display settings must persist until user changes them.

MVP-1 persisted items:
- dashboard period (`day`, `week`, `month`, `year`, `custom`)
- operations filters
- operations sorting
- active main section/tab

Persistence strategy:
- Source of truth: server-side `user_preferences`
- Fast fallback cache: local storage

Behavior:
- Save changes with debounce to avoid noisy writes
- Restore last state on next open/session
- Provide clear `Reset filters` action

## Action Hierarchy
- One primary CTA per screen (for example, `Add operation`)
- Secondary actions grouped nearby
- Destructive actions require explicit confirmation
- Submit actions (create/update/apply) use one reusable loading flow:
- disable button while request in progress
- show temporary loading label on button
- show unified success/error status messages

## Destructive Actions and Undo
- Delete actions must show explicit confirmation before execution
- After delete, show bottom session-level toast with undo action
- Toast must include animated countdown progress indicator
- Toast must persist while user switches tabs in current session
- Destructive flow must use one reusable handler, not per-screen copy-paste logic

## Time Filters
- Dashboard and operations period controls should support:
- current day
- current week
- current month
- current year
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

## Row Interaction
- Selecting row via checkbox applies persistent selected highlight
- Clicking row body toggles checkbox selection (except clicks on controls)
- Inline row actions appear on hover and for selected row
- Bulk counter in operations is always visible:
- no selection: `Всего: N`
- with selection: `Выбрано: M из N`
- In categories hierarchical table:
- selecting group checkbox selects group and all nested categories
- partial nested selection puts group checkbox in indeterminate state

## Category Inputs
- Group color is chosen via color picker with synchronized hex value
- Category icon is selected from a predefined icon popover, not free text input
- In create operation modal, category is selected via reusable chip-picker flow:
- search input (realtime filter)
- quick chips (`часто используемые`)
- `Еще` button to expand full chip list
- when search has no match, show chip action `Создать категорию «...»` and open category modal prefilled
- Operation preview row must always include category chip with the same renderer as operations tables

## Responsive Behavior
- Desktop: sidebar visible
- Mobile: sidebar collapses, priority actions remain accessible
