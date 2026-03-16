# UI System

## Layout
- Left sidebar for global navigation
- Central working area for content and forms
- Top action bar inside content area for search and filters
- Dashboard period tabs are placed in the operations table panel header, next to the table title/actions
- Sidebar contains persistent day/date block (large typography) visible across sections

## Mobile-First Baseline
- Telegram Mini App/mobile layout is a required target, not an optional afterthought
- desktop layout may stay richer, but all core flows must remain fully usable on narrow screens first
- target baseline widths:
- `320px` minimum supported flow
- `360-430px` primary Telegram phone range
- horizontal overflow in critical screens is not acceptable unless interaction is intentionally scrollable
- primary actions must stay reachable without hover and without precision cursor behavior

## Telegram Mini App Runtime UX
- UI must account for Telegram WebApp container behavior:
- safe-area insets
- dynamic viewport height changes
- in-app browser chrome and keyboard overlap
- current baseline intentionally does not depend on Telegram-native `BackButton` navigation
- shell and modal navigation must stay fully handled by regular in-app controls even inside Telegram
- Telegram-specific runtime hooks must not leak into shared domain logic
- Telegram runtime should call optional WebApp APIs only after capability/version checks; cosmetic APIs like header/background color must not generate avoidable console warnings on older Telegram containers

## Sidebar Navigation
Primary items:
- Dashboard
- Analytics
- Operations
- Categories
- Debts
- Reports (post-MVP)
- Budgets (post-MVP)
- Settings

Sidebar grouping baseline (when section groups are introduced):
- `Обзор`: Dashboard, Analytics
- `Учет`: Operations, Categories, Item Catalog, Debts
- `Планирование`: Budgets, Reports
- `Система`: Admin (only for admins), Settings
- Dashboard is always first and default active on first open/session reset.

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
- On mobile, settings choice fields should prefer sheet/modal pickers over native visible `select` dropdowns, because WebView/native popup positioning is inconsistent and often visually detached from the triggering control.

## Access Control UI
- Login mode is environment-driven:
- production: Telegram auth
- inside Mini App: Telegram WebApp auth (`initData`)
- in browser: Telegram Login Widget / browser Telegram auth payload
- Frontend auth visibility contract:
- `#telegramLoginBtn` is visible only when Mini App `initData` is present
- browser login widget visibility depends on `/api/v1/auth/public-config` (`telegram_bot_username` + `browser_login_available`)
- e2e scenarios must mock these two inputs consistently; otherwise startup can fail before reaching the target screen
- For non-approved users:
- `pending`: informative waiting state
- `rejected`: informative denied state
- main workspace is not available until approval
- Admin section is rendered only for admin users.
- Admin section baseline:
- status filters (`pending/approved/rejected/all`)
- actions (`Approve`, `Reject`, `Delete user`)

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
- Static shell assets should include a favicon placeholder so browser/WebView startup does not generate repeated `favicon.ico` 404 noise

## Mobile Interaction Rules
- critical actions must not rely on row hover
- inline row actions need mobile-safe alternative access:
- always-visible compact action button
- swipe/menu/sheet trigger
- stacked action area inside card/list row
- large modal flows should be reviewed for mobile replacement with bottom-sheet or full-screen form where appropriate
- sticky footer CTA is preferred for long mobile forms
- tap target size should be comfortable for touch-first use
- modal header close action should keep a stable square hit area (`44-48px`) and must not collapse into a visually narrow icon slot
- mobile grouped tables/cards should not keep desktop inline metas/actions in one row:
- parent/group metas wrap below title
- nested child rows keep visible inset/guide
- grouped mobile cards should preserve parent-child relation with shared accent rail/border color where the hierarchy is important (`Categories`, `Item Catalog`, debt-by-counterparty surfaces)
- action buttons are always visible, full-width or stacked, and may wrap text instead of overflowing
- dense mobile picker-like buttons (`settings`, `select` replacements) should use the same control height as primary form fields
- when a desktop table becomes unreadable on phone width, prefer a dedicated mobile renderer over `td[data-label]` fallback; `Categories` and `Item Catalog` should render as `parent card -> nested child cards`
- sticky mobile modal footers must reserve matching bottom scroll space in the content area and stay above popovers/autocomplete surfaces so CTA never covers the last actionable field
- mobile list/card action zones should default to full-width stacked buttons unless the feature explicitly benefits from a denser layout (`Debts` currently remains an exception)
- section-specific action contracts must stay isolated:
- `Operations`: desktop row actions stay compact and right-aligned for every row variant; mobile operation cards use full-width stacked actions
- `Categories`: mobile layout should follow the same dedicated nested-card pattern as `Item Catalog`, not desktop `td[data-label]` table fallback
- `Debts History`: direction pill (`Я дал` / `Я взял`) must remain single-line on narrow screens
- semantic pills/chips (`Тип`, debt direction, category/type pills) should size to content by default and must not stretch to the full row unless the component is explicitly designed as a segmented/full-width control
- analytics section/tab contract:
- opening `Аналитика` must immediately load data for the active analytics tab/state without requiring any extra control toggle
- switching analytics internal tabs must trigger the corresponding data load immediately
- desktop action buttons should preserve compact horizontal sizing; wrap/full-width action behavior is mobile-only
- desktop grouped-row contract:
- parent row content (`title`, `metas`) stays left-aligned
- row actions stay pinned to the right edge
- mobile grouped-row contract:
- `Categories` should mirror the clearer `Item Catalog` parent/child card pattern
- `Operations` card actions should use full-width stacked buttons
- analytics donut center content on mobile must stay safely inside the hole; prefer a larger hole and smaller secondary text over letting text approach the chart slices
- sticky modal CTA overlay contract:
- footer stays visually above lower content and popovers
- content below must not bleed through the CTA surface

## Operation Modal Category Picker
- Create/edit operation modals use chip-based category picker instead of plain select control
- Picker layout:
- search input
- one chip list sorted by usage frequency (no duplicate quick/full blocks)
- chip action for creating missing category from current search
- Chips reuse the same category chip component styles as tables/lists
- While search query is active, picker shows one result list only (no duplicated chips across quick/full rows)

## Operation Receipt Pattern (MVP)
- Operation modal supports optional `Чек (позиции)` block.
- Receipt line item fields:
- `Категория` (optional chip-picker, per line item)
- `Источник` (chip/template picker style, source chips)
- `Позиция` (chip/template picker style, same mechanics as category chip picker)
- `Кол-во`
- `Цена`
- `Сумма позиции` (auto)
- `Комментарий` (optional)
- Amount modes:
- manual operation amount
- auto-from-receipt (fill amount from receipt total)
- If manual amount differs from receipt total, show non-blocking discrepancy warning.
- Saving with discrepancy is allowed.
- Picker behavior contract:
- popover closes on first outside click / `Esc` / chip selection
- `+ Создать позицию «...` adds position into local picker source immediately for next rows (optimistic UI), DB persistence remains on operation save
- source chips act as grouping filter for position chips inside the same row (`Источник` -> filtered `Позиция`)
- Operation rows with receipt items expose separate hover action `Позиции` (read-only modal with item list); note column is not auto-augmented by receipt metadata
- Receipt item category remains optional and complements, not replaces, operation-level category.
- Position analytics is currently exposed through analytics highlights (`top positions`, `price increases`); a dedicated per-position deep-dive screen is still backlog.

## Position Catalog (MVP)
- Separate catalog view/modal for reusable receipt positions:
- item name
- usage frequency
- last used timestamp
- price history timeline
- Catalog data drives template chips in receipt editor.
- Current table pattern for position catalog is grouped by source with collapsible group rows:
- group row: chevron + source title + compact aggregates (`позиции`, `исп`, `ср`, `посл`)
- child rows: positions inside selected source group
- hierarchy baseline:
- group/source row uses stronger parent surface
- child position rows are nested with inset layout and left guide, not only by repeated source text
- search behavior: realtime across `source + position`, matching groups auto-expanded while query is active
- search loading strategy: use local filtering when full catalog snapshot is available; fallback to API query when snapshot is partial/outdated
- table controls:
- sort presets (`Частота`, `Недавние`, `Имя`)
- group actions (`Свернуть все`, `Развернуть все`)
- sort preset is persisted in preferences (`ui.item_catalog_sort_preset`)
- persist writes for sort/collapse/source-group ui state must be debounced
- item rows expose hover actions (`Редактировать`, `Удалить`)
- current section actions:
- top CTA: primary `+ Создать позицию`, secondary `+ Создать источник`
- search-row controls: sort/group controls and `Удалить все`
- in create/edit position modal, source field reuses chip-picker mechanics from operation/category flows (search, suggestions, create-if-missing)
- source create modal keeps simple text input (without chip-picker popover)
- source/position create flows include live preview of resulting table row
- price history modal is visually/interaction-consistent with receipt positions modal and includes source chip in meta
- This grouped-table pattern is reused in `Categories` table structure for consistency.
- The same visual parent/child contract should also be reused in debt-by-counterparty blocks where one parent card contains multiple debt records.
- On mobile, parent/group metas should wrap onto their own row below title instead of competing with title width in one line.
- On mobile, group/source metas may be rendered as short stacked lines for clarity instead of one compressed inline strip.

## Debt Modal Pattern (Implemented MVP Baseline)
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
- Repayment modal quick presets:
- `25%`, `50%`, `Весь остаток`
- preset amount must be computed from current debt outstanding in state/API payload, not by parsing formatted UI string

## Debt Cards (Implemented MVP Baseline)
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

## Dashboard Analytics Preview
- Dashboard includes compact analytics preview widget:
- mini trend sparkline for selected period
- short deltas vs previous period (`Доход`, `Расход`, `Баланс`)
- CTA `Открыть аналитику`
- This block is summary-only and does not replace full analytics section.

## Dashboard Operations Block Review (Planned)
- Operations block on dashboard is treated as optional context, not core workspace.
- Baseline direction:
- keep compact recent operations subset on dashboard
- full operations list/edit flows remain in `Операции`
- visibility can be preference-driven to reduce dashboard overload

## CTA Patterns
- Primary create action in modal must be placed in modal footer, centered, visually dominant
- Section-level actions are rendered in a shared topbar CTA zone and aligned to the right
- One primary CTA per active section/screen; secondary actions use secondary/ghost style in same zone
- Similar actions must use the same visual class pattern (`cta-main`, `cta-inline`) to preserve consistency
- Canonical mapping:
- `Dashboard/Operations`: primary `+ Добавить операцию`, secondary `+ Массовое добавление`
- `Debts`: primary `+ Новый долг`
- `Categories`: primary `+ Создать категорию`, secondary `+ Создать группу`
- `Item Catalog`: primary `+ Создать позицию`, secondary `+ Создать источник`

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
- Operations tables support checkbox selection and reusable bulk action bar:
- `Редактировать выбранные`
- `Удалить выбранные`
- Categories section uses row-level actions and section-level `Удалить все` without checkbox bulk-select.
- In dense mobile rows, long chip text should truncate with ellipsis inside the chip instead of stretching the row/card beyond available width.

## Table Interaction Pattern
- For data rows, inline actions (`Редактировать`, `Удалить`) are hidden by default and shown on row hover
- In operations tables, if a row is selected, inline actions stay visible even without hover
- In operations tables, selected row has stronger persistent highlight than hover state
- Row hover animation is reused in both dashboard operation table and operations list table
- In categories table, row actions include both `Редактировать` and `Удалить` for user categories
- Categories search matches both category names and group names
- Operations realtime search uses debounced preferences persistence to avoid one server write per keystroke
- Large list/table loading standard: `20` initial rows, then `+20` per scroll batch (infinite scroll), without numbered pagination controls.
- After create/update/delete actions, data refresh is section-aware (active section first) to avoid unnecessary cross-section request bursts
- Categories table layout follows the same structural zones as operations table:
- panel header with title/subtitle and tabs on the right
- search row (`Поиск` left, `Свернуть/Развернуть все` center, `Удалить все` right)
- then table body

## Analytics Section (Planned MVP Baseline)
- Main layout:
- top tab row inside analytics section:
- `Общий`
- `Календарь`
- `Операции`
- `Тренды`
- each tab has focused content to reduce visual overload
- positions insights are placed inside `Операции` tab
- Calendar monthly grid:
- calendar tab has one control zone for grid only:
- `Сетка`: view (`Месяц`/`Год`) + grid navigation (`←`, `Текущий`, `→`)
- 7 columns (`Пн..Вс`) and 5-6 week rows
- each day cell shows income, expense, operations count
- right side of each week row shows weekly totals (`доход/расход/операции`)
- year grid mode:
- 12 month cards (`Янв..Дек`) instead of day rows
- each month card shows income/expense/ops/balance
- calendar summary block uses KPI cards instead of plain text footer:
- primary cards only: income / expense / balance / operations count
- secondary compact row: single result (`Профицит`/`Дефицит`/`Нулевой баланс`)
- `Общий` tab contains period-level KPI controls (`Неделя`/`Месяц`/`Год`/`Настроить`) and expanded summary chips

## Settings: Dashboard + Analytics
- Dashboard block visibility is preference-driven:
- `show_dashboard_analytics`
- `show_dashboard_operations`
- `show_dashboard_debts`
- Dashboard operations block supports configurable row count (`5/8/12`) via `ui.dashboard_operations_limit`.
- Analytics insight limits are user-configurable:
- `analytics.top_operations_limit` (`3/5/10`)
- `analytics.top_positions_limit` (`5/10/20`)

## Interface Scale
- UI scale slider range: `85%..115%`, step `1%`, with reset to `100%`.
- Background must remain visually continuous for low/high scale values (no hard seams or repeat artifacts).
- Known optimization direction:
- avoid `body zoom` for long-term stability
- migrate to token-based scaling (`font-size/spacing/control-height`) to reduce rendering artifacts
- Trend charts:
- combo chart baseline: income+expense bars and balance line
- chart click can drill down to operations list filtered by bucket/date
- Analytics `Operations` tab includes:
- top heavy operations
- top categories
- anomaly block
- expensive positions and price-increase highlights
