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
- `Учет`: Operations, Plans, Categories, Item Catalog, Debts
- `Планирование`: Budgets, Reports
- `Система`: Admin (only for admins), Settings
- Dashboard is always first and default active on first open/session reset.

## Plans Section
- New first-level section: `Планы`
- Placement in sidebar: immediately after `Операции`
- Purpose: future operations/income records that are prepared in advance but do not affect fact/statistics until explicit confirmation
- All plan entries require confirmation by default; there is no separate `requires confirmation` toggle
- `План` is not a regular operation row with a flag; it is a separate entity and should stay outside normal operations/statistics until confirmed
- `Подтвердить` should create a real operation immediately
- `Редактировать` should edit the plan itself, not the resulting operation
- plan form should reuse the existing operation form contract as much as possible, excluding debt mode
- current implementation uses the existing create-operation modal in dedicated `plan` mode instead of a separate form
- reusable fields baseline:
- operation kind (`Расход` / `Доход`)
- date / due date
- category
- amount
- comment
- optional receipt/positions flow
- current recurrence contract:
- segmented switch `Разовая / Повторяющаяся`
- frequency: `daily | weekly | monthly | yearly`
- interval step
- daily plans can optionally run only on weekdays (`Пн-Пт`)
- weekly plans may target multiple weekdays in one recurring cycle
- monthly plans can be pinned to the last day of month
- optional recurrence end date
- current plan actions:
- `Подтвердить` -> creates a normal operation immediately
- `Редактировать` -> reopens the same modal in `plan` mode
- `Пропустить` -> available for recurring plans and shifts next due date forward
- `Удалить`
- section-level plan monitoring UI:
- KPI layer should be compact and finance-first, not split into five separate operational cards
- primary KPI surface should show the financial baseline plus plan delta, not isolated planned totals
- the displayed value should be computed as current all-time balance plus/minus the sum of pending plan operations
- preferred reading order:
- first show current balance as the main anchor value
- immediately next to it show signed plan delta (`-64` / `+64`) with expense/income color semantics
- only below that show the projected post-plan result as a quieter secondary line
- current balance must remain the dominant number; the signed delta is a compact adjacent modifier, not a replacement for the base figure
- `К подтверждению` and `Просрочено` should not consume standalone large cards by default; prefer compact status chips/counters near the main KPI surface
- current compact status set should favor `Активных`, `Сегодня`, `Просрочено` over the more ambiguous `К подтверждению`
- the old explanatory subtitle about plans not affecting fact before confirmation is redundant and should stay removed both in the section and in the dashboard plans block
- status-scope filter: `Все сроки / Просрочено / Сегодня / Впереди`
- initial dashboard strategy: replace the current recent operations block with `Ближайшие планы`
- dashboard plans block should show pending/planned workload, not factual accounting data
- dashboard plans block supports a local period switch `Эта неделя / Этот месяц / Все время`; it is scoped only to this block and must not reuse the global dashboard analytics period
- `Эта неделя` and `Этот месяц` in dashboard plans should still include overdue plans, so urgent items do not disappear from the block
- dashboard plan cards should use a compact action set; `Подтвердить` is enough there, while edit/delete belong to the main `Планы` section
- plans controls should keep a separate row under KPI; search belongs in the controls row, not glued directly to the KPI card
- on desktop the plans toolbar should be split into two clear rows:
- first row: segmented controls only
- second row: full-width search
- plan list rows/cards should reuse the same information rhythm as regular `Операции` rows where practical:
- core fields/meta should be rendered like an operation item
- contextual plan chips should explain plan state/recurrence
- plan cards should keep only the primary CTA `Подтвердить` visible; secondary actions like `Редактировать`, `Пропустить`, and `Удалить` should live in a compact top-right kebab menu
- reusable list/card pattern: when an entity has one dominant CTA and several secondary management actions, keep the dominant CTA visible, move secondary actions into a square top-right kebab trigger, and make the free card body open the edit/details flow on click
- interactive list cards should use a subtle hover/focus treatment (slight lift + border glow), not an aggressive animation
- plan cards should use semantic left accent rails by `kind`: expense plans use red/pink rail, income plans use green rail
- receipt items from plans should also sync into the shared item template catalog; item catalog is not restricted to confirmed operations only
- item catalog should also be able to backfill from existing historical `plan_receipt_items`, so plans created before a sync fix do not stay permanently invisible in the catalog
- on desktop, contextual plan chips should sit in a compact top-left row above the main data line
- due/progress indicator by term should be visible
- the main difference from `Операции` rows should be the action set (`Подтвердить`, `Редактировать`, optional `Пропустить`, `Удалить`)
- when a plan/operation contains receipt positions without one shared default category, category display should be derived from receipt item categories and rendered as deduplicated chips rather than a misleading `Без категории`
- operation/plan payloads should carry category meta (`category_name`, icon/accent when available) so list UIs do not depend exclusively on a separately preloaded category catalog
- `Позиций: N` in plan meta should behave as an inline link/action that opens the same receipt-items modal used by `Операции`
- when `Позиций: N` is already rendered as the interactive value, the extra field label above that column should stay removed
- plan create/edit preview should not reuse the old table-row preview when `createFlowMode === plan`; it should render the actual plan-card contract used in the `Планы` section
- preview should stay non-interactive: do not render action buttons inside preview cards
- recurrence controls should use a desktop main row for frequency/interval/end-date, with a separate option row for contextual toggles like `Только по будням` and `В последний день месяца`
- contextual recurrence options should use the same segmented `Выкл / Вкл` contract instead of mixing checkboxes with segmented controls
- when `В последний день месяца` is enabled, the main plan date field should become rule-driven and disabled/read-only to avoid conflicting manual input
- desktop recurrence controls should stretch evenly across the available modal width instead of collapsing into narrow intrinsic-width inputs
- frequency, interval, and recurrence end date should have explicit field labels in the modal; placeholder-only recurrence controls are not acceptable
- on desktop, plan cards should not keep the tall mobile-style column stack; use a denser horizontal distribution with:
- left: operation-like fields/meta row
- center/right: due/progress block integrated into the same horizontal rhythm, without large dead vertical space
- right edge: visible action column
- desktop polish target: amount stays right-aligned inside the data row, due/progress reads as one compact line, and the action column should sit visually close enough to the content to avoid a "hole" in the card
- if receipt positions exist, `Позиции` should occupy its own desktop data column between category and amount rather than leaving an empty middle zone
- backend storage baseline:
- `plan_operations`
- `plan_receipt_items`
- `plan_operation_events`
- plans are fetched via `/api/v1/plans` and confirmed via `/api/v1/plans/{id}/confirm`
- plans history feed is fetched via `/api/v1/plans/history`
- `История` tab is backed by real event rows (`confirmed`, `skipped`, `reminded`), not by a derived filter over closed plans
- `История` tab also supports explicit event-type filtering (`all / confirmed / skipped / reminded`)
- Telegram reminder baseline is implemented through the existing `bot` worker:
- the bot worker should not full-scan all plans continuously; it should poll only a queue of pending reminder jobs
- reminder jobs are (re)scheduled when a plan is created, edited, confirmed, skipped, deleted, or when reminder settings change
- reminder delivery is controlled by preferences toggle `plans.reminders_enabled`
- reminder time is controlled by `plans.reminder_time` in the user's configured `ui.timezone`
- when `ui.timezone` stays on `auto`, reminder scheduling must use the saved browser timezone snapshot (`ui.browser_timezone`) instead of falling back to UTC
- plan cards may show a reminder chip (`Напоминание HH:MM` / `Напоминание скоро`) derived from the next queued reminder
- reminder chip time must be rendered in the same effective user timezone as settings; browser-local drift is not acceptable
- plan due progress should be time-based from the current cycle anchor to the due date, not a static status percentage
- plan preview in the modal must update immediately when switching `Разовая / Повторяющаяся`; stale `Разовый` chips in recurring mode are not acceptable
- recurring controls in the plan modal should span the full modal width on desktop instead of collapsing to the width of the segmented switch
- non-confirm plan mutations must not reset the factual all-time balance baseline inside plans KPI; only `Подтвердить` changes fact

## Settings
- Settings section includes timezone selector
- Timezone options include `Авто (из браузера)` and explicit IANA zones
- Selected timezone is stored in user preferences (`ui.timezone`) and reused by date widgets
- Settings include `Интерфейс` block under timezone:
- currency (`BYN` first/default, then `RUB`, `USD`, `EUR`, ...)
- currency symbol position (`prefix`/`suffix`)
- toggle `Показывать карточки долгов на дашборде`
- UI scale slider (user-specific)
- Settings include a separate `Напоминания` block for plans:
- toggle `Напоминать о планах в Telegram`
- `Время напоминания`
- obsolete analytics top-limit settings were removed from Settings because they no longer drive live analytics rendering
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
- responsive renderer contract: sections that choose different mobile/desktop DOM structures (`Operations`, `Categories`, `Item Catalog`, similar table/card surfaces) must re-render on breakpoint transition, not only on full page reload
- breakpoint-driven re-render should reuse already loaded client state and must not trigger duplicate data requests just because DevTools/device mode or viewport width changed
- section-specific action contracts must stay isolated:
- reusable row/card interaction contract:
- click on free row/card body opens edit/details
- checkbox is used only for selection
- group/source headers are used only for expand/collapse
- explicit buttons/links/popovers must not trigger row-level open
- clickable rows/cards should also expose a subtle visual affordance on hover/focus (light lift + border glow), so edit-on-click is discoverable without relying on guesswork
- `Operations`: desktop row actions stay compact and right-aligned for every row variant; mobile operation cards use full-width stacked actions
- `Operations`: click on row body opens edit; mass selection lives only on the checkbox column
- `Categories`: mobile layout should follow the same dedicated nested-card pattern as `Item Catalog`, not desktop `td[data-label]` table fallback
- `Categories`: group header click expands/collapses; child category row/card click opens edit
- `Item Catalog`: source header click expands/collapses; child item row/card click opens edit
- `Debts`: debt row/card body click opens edit while repayment/history/delete stay explicit CTA actions
- `Debts History`: direction pill (`Я дал` / `Я взял`) must remain single-line on narrow screens
- semantic pills/chips (`Тип`, debt direction, category/type pills) should size to content by default and must not stretch to the full row unless the component is explicitly designed as a segmented/full-width control
- analytics section/tab contract:
- opening `Аналитика` must immediately load data for the active analytics tab/state without requiring any extra control toggle
- switching analytics internal tabs must trigger the corresponding data load immediately
- desktop action buttons should preserve compact horizontal sizing; wrap/full-width action behavior is mobile-only
- desktop grouped-row contract:
- parent row content (`title`, `metas`) stays left-aligned
- row actions stay pinned to the right edge
- desktop modal footer/action contract:
- secondary close buttons in modal footers should not collapse into narrow square-ish chips with wrapped text
- `Закрыть` should stay a normal readable secondary button with stable horizontal padding and single-line label
- mobile grouped-row contract:
- `Categories` should mirror the clearer `Item Catalog` parent/child card pattern
- `Operations` card actions should use full-width stacked buttons
- analytics donut center content on mobile must stay safely inside the hole; prefer a larger hole and smaller secondary text over letting text approach the chart slices
- sticky modal CTA overlay contract:
- footer stays visually above lower content and popovers
- content below must not bleed through the CTA surface
- medium-width (`tablet/compact desktop`) toolbar contract:
- do not keep every section in one dense horizontal toolbar if controls begin to deform the layout
- `Operations`: low-value sort toggles `По дате / По сумме / Риск` should be removed instead of compressing the toolbar further
- `Debts`: search does not need to stay artificially full-width; it may shrink to a sensible content width while the toolbar rearranges into controlled rows
- `Debts` compact-wide layout should prefer stacked rows over overflow:
- row 1: search + destructive action if space allows
- row 2: status segmented control
- row 3: sort segmented control
- if width tightens further, destructive action may drop to its own row instead of forcing every control to collapse

## Dashboard KPI and Summary Contract
- selecting `Все время` must always map to all-time summary data; dashboard KPIs must not remain stuck on a previously selected day/week/custom range after the UI shows `Все время`
- dashboard period label and summary payload must stay synchronized after period changes, including transitions from custom/day ranges back to `all_time`
- leaving dashboard `custom` period must clear stored custom date bounds before loading another preset period

## Operations List Summary Contract
- list rendering may stay virtualized/batched (`20 + infinite scroll`) for performance
- summary counters must still show the real matched total from backend/result metadata, not only the number of rows currently rendered in DOM
- `Всего`/`Операций найдено` should reflect actual filtered total even while the table lazily appends more rows on scroll

## Dashboard Debt Block
- compact debt cards should minimize dead space between counterparty title, state chip and financial/progress content
- `Активный`/status chip should sit closer to the debt title/meta cluster instead of leaving a large empty horizontal gap
- debt summary, progress and CTA should read as one dense compact card, not as widely separated islands inside the same row

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
- compact dashboard debt cards should keep title, status chip, debt rows and CTA visually dense; large empty horizontal gaps are treated as a layout defect
- preferred compact desktop layout:
- left column `1/3`: counterparty identity block (`name`, `status`, `created_at`)
- right column `2/3`: debt working block (`direction/amount`, `progress`, `due`, `Погашение`, `История`)

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
