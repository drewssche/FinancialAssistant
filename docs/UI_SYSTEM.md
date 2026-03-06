# UI System

## Layout
- Left sidebar for global navigation
- Central working area for content and forms
- Top action bar inside content area for search and filters
- Dashboard period tabs are placed in the operations table panel header, next to the table title/actions
- Sidebar contains persistent day/date block (large typography) visible across sections

## Sidebar Navigation
Primary items:
- Dashboard
- Operations
- Categories
- Debts
- Reports (post-MVP)
- Budgets (post-MVP)
- Settings

## Settings
- Settings section includes timezone selector
- Timezone options include `Авто (из браузера)` and explicit IANA zones
- Selected timezone is stored in user preferences (`ui.timezone`) and reused by date widgets
- Settings include `Интерфейс` block under timezone:
- currency (`BYN` first/default, then `RUB`, `USD`, `EUR`, ...)
- currency symbol position (`prefix`/`suffix`)
- toggle `Показывать карточки долгов на дашборде`
- UI scale slider (user-specific)
- All money outputs and amount inputs reuse one currency formatting rule from preferences
- Settings include red `Danger Zone` with `Удалить меня` action (full user data removal)

## Category Modals
- Group creation uses: name + accent color picker + kind (no group icon field)
- Category creation/edit uses: name + category icon picker popover + group + kind
- Category group selection in create modal uses chip-picker popover (not native select in visible UI):
- trigger input
- chip `Без группы`
- chips for groups filtered by current kind (`Расход`/`Доход`)
- Category icon is stored on category entity and rendered in category chips/tables

## Sidebar User Block (Bottom)
At the bottom-left sidebar, show compact static user block:
- avatar
- username + handle aligned close to avatar
- separate logout icon button on the right
- no user context dropdown menu

## Core UI Element Categories
- Buttons: primary, secondary, danger, ghost
- Inputs: text, number, date, select
- Search and filter bar: above the table only in sections that actually support search (tables/lists)
- Lists and tables: sortable headers where applicable
- Modal dialogs: create/edit operations and categories
- Status views: loading, empty, error

## Operation Modal Category Picker
- Create operation modal uses chip-based category picker instead of plain select control
- Picker layout:
- search input
- one chip list sorted by usage frequency (no duplicate quick/full blocks)
- chip action for creating missing category from current search
- Chips reuse the same category chip component styles as tables/lists
- While search query is active, picker shows one result list only (no duplicated chips across quick/full rows)

## Debt Modal Pattern (Planned)
- Operation modal supports two modes:
- `Обычная операция`
- `Долг`
- In `Долг` mode:
- category/tag controls are hidden
- debt form fields are shown:
- `Дата операции`
- `Направление` (`Я дал`/`Я взял`) as segmented control
- `Имя контрагента`
- `Сумма`
- `На срок`
- `Комментарий`
- Submit action creates debt record (not regular operation category flow)

## Debt Cards (Planned)
- Debt cards are grouped by counterparty (one card per name)
- Card content:
- counterparty name
- totals (`выдано/взято`, `погашено`, `остаток`)
- nearest due date
- list of debt records and repayment records
- quick action: `Внести погашение`
- Cards with `остаток = 0` are not shown in dashboard widget by default

## Dashboard Debt Block
- Dashboard includes dedicated debt KPI row:
- `Мне должны`
- `Я должен`
- `Чистая позиция по долгам`
- Dashboard includes compact cards by counterparty (not table).
- Card layout:
- left: `контрагент + статус`
- right: compact debt rows (up to 2 visible) with per-debt metrics:
- direction-scoped principal
- repayment progress with `N из M`
- due-date chip + days-left chip + due-progress bar
- Debt KPIs are displayed separately from cash-flow KPI (`Доход/Расход/Баланс`) to avoid semantic mixing
- Dashboard debt cards block can be hidden by user interface preference

## CTA Patterns
- Primary create action in modal must be placed in modal footer, centered, visually dominant
- Section-level actions are rendered in a shared topbar CTA zone and aligned to the right
- One primary CTA per active section/screen; secondary actions use secondary/ghost style in same zone
- Similar actions must use the same visual class pattern (`cta-main`, `cta-inline`) to preserve consistency
- Canonical mapping:
- `Dashboard/Operations`: primary `+ Добавить операцию`, secondary `+ Массовое добавление`
- `Debts`: primary `+ Новый долг`
- `Categories`: primary `+ Создать категорию`, secondary `+ Создать группу`

## Segmented Controls
- Period and type filters should use segmented tabs instead of native selects where interaction frequency is high
- Segmented container width should fit its content, not stretch to unrelated layout width
- Active state switching must use one shared mechanic for all segmented groups
- Period segmented tabs are reused in both `Dashboard` and `Operations` sections with synchronized state
- Period tabs order target (planned refinement): `День` -> `Неделя` -> `Месяц` -> `Год` -> `За все время` -> `Настроить`
- `За все время` means full user range (`from first operation date` -> `today` in selected timezone)

## Chips and Bulk
- Categories and category groups are displayed as chips (icon + color accent)
- Categories section uses hierarchical table view:
- ungrouped categories first
- then group row and nested category rows
- Group row supports inline actions: `Редактировать`, `Удалить`
- Tables/lists support checkbox selection and reusable bulk action bar:
- `Редактировать выбранные`
- `Удалить выбранные`
- `Удалить все`
- `Удалить все` is placed in the table-search row (right side), while selected-item actions stay in bulk bar
- Categories bulk counter text is compact:
- no selection: `Ничего не выбрано`
- with selection: `Выбрано: N (...)`
- Bulk counter container keeps fixed typography/spacing between empty and selected states to avoid layout jumps
- Hidden bulk actions are removed from layout flow (`display: none`) to avoid floating gaps in action row

## Table Interaction Pattern
- For data rows, inline actions (`Редактировать`, `Удалить`) are hidden by default and shown on row hover
- If a row is selected, inline actions stay visible even without hover
- Selected row has stronger persistent highlight than hover state
- Row hover animation is reused in both dashboard operation table and operations list table
- In categories table, row actions include both `Редактировать` and `Удалить` for user categories
- In categories table, selecting child category does not auto-select parent group checkbox
- Categories search matches both category names and group names
- Large list/table loading standard: `20` initial rows, then `+20` per scroll batch (infinite scroll), without numbered pagination controls.
- Categories table layout follows the same structural zones as operations table:
- panel header with title/subtitle and tabs on the right
- bulk row (`Всего/Выбрано` + selected-actions)
- search row (search left, `Удалить все` right)
- then table body
