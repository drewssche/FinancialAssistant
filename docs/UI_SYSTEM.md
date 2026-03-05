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
- Reports (post-MVP)
- Budgets (post-MVP)
- Settings

## Settings
- Settings section includes timezone selector
- Timezone options include `Авто (из браузера)` and explicit IANA zones
- Selected timezone is stored in user preferences (`ui.timezone`) and reused by date widgets

## Category Modals
- Group creation uses: name + accent color picker + kind (no group icon field)
- Category creation/edit uses: name + category icon picker popover + group + kind
- Category icon is stored on category entity and rendered in category chips/tables

## Sidebar User Block (Bottom)
At the bottom-left sidebar, show current user:
- avatar
- username or first name

On click, open context menu:
- Settings
- Linked Accounts (future)
- Logout

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
- quick chips (top used for selected operation kind)
- `Еще` is rendered as the last chip in quick row (same chip family, visually distinct dashed style)
- chip action for creating missing category from current search
- Chips reuse the same category chip component styles as tables/lists
- While search query is active, picker shows one result list only (no duplicated chips across quick/full rows)

## CTA Patterns
- Primary create action in modal must be placed in modal footer, centered, visually dominant
- Primary inline add buttons in sections should be content-width (fit text) and centered within the section
- Similar actions must use the same visual class pattern (`cta-main`, `cta-inline`) to preserve consistency
- Categories section uses two primary actions in one row: `Создать группу` and `Создать категорию` (dashboard-style CTA pair)

## Segmented Controls
- Period and type filters should use segmented tabs instead of native selects where interaction frequency is high
- Segmented container width should fit its content, not stretch to unrelated layout width
- Active state switching must use one shared mechanic for all segmented groups
- Period segmented tabs are reused in both `Dashboard` and `Operations` sections with synchronized state

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

## Table Interaction Pattern
- For data rows, inline actions (`Редактировать`, `Удалить`) are hidden by default and shown on row hover
- If a row is selected, inline actions stay visible even without hover
- Selected row has stronger persistent highlight than hover state
- Row hover animation is reused in both dashboard operation table and operations list table
- In categories table, row actions include both `Редактировать` and `Удалить` for user categories
- Categories table layout follows the same structural zones as operations table:
- panel header with title/subtitle and tabs on the right
- bulk row (`Всего/Выбрано` + selected-actions)
- search row (search left, `Удалить все` right)
- then table body
