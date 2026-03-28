# Currency Feature Plan

Status:
- mostly complete
- owner: Codex
- scope: currency positions, exchange deals, dashboard KPI, analytics, and telegram notifications

## Implementation Progress

Implemented:
- backend models and migration for `fx_trades` and `fx_rate_snapshots`
- API endpoints:
  - `GET /api/v1/currency/overview`
  - `POST /api/v1/currency/trades`
  - `PUT /api/v1/currency/rates/current`
- weighted-average position calculation from trade history
- dashboard summary integration for currency KPI
- dashboard currency block
- dashboard currency block promoted into a separate panel above period KPI
- dashboard rate widget enriched with day-over-day `+/-` vs previous snapshot
- dashboard currency block gets force-refresh actions for rates
- dedicated `Валюта` section with:
  - tracked-currency filter
  - current positions
  - CTA `Сделка` routed into the shared create modal on the `Валюта` tab
  - manual current-rate form
  - recent trades list
- settings support for:
  - tracked currencies
  - show/hide dashboard currency block
  - daily Telegram digest preference flag
- automatic daily tracked-rate refresh via Telegram bot scan loop
- daily Telegram currency digest with separate reminder time and anti-duplicate guard
- Telegram currency threshold alerts:
  - `выше курса`
  - `ниже курса`
- currency mode inside the common add-operation modal
- analytics tab `Валюта` with KPI, rate-history chart, deal list, and period controls
- admin diagnostics for currency runtime:
  - tracked users
  - digest enabled
  - alert rules
  - stale / missing rates
- currency code presentation improved with symbol labels like `USD ($)` and `EUR (€)`
- operations support original currency plus base conversion snapshot
- operations currency-scope control:
  - `Все`
  - `<BASE>` for base-currency operations only, for example `BYN`
  - `Другая валюта` for non-base operations only
- multi-currency plans with live `≈ BYN` conversion
- multi-currency debts with live `≈ BYN` conversion
- debt forgiveness flow:
  - separate action `Простить долг`
  - API endpoint `POST /api/v1/debts/{id}/forgivenesses`
  - debt history distinguishes `Погашение` and `Прощение`
  - debt closes with `closure_reason=forgiven`
  - UI keeps main status `Закрыт` and secondary meta `Прощен`
  - forgiveness is available both as a dedicated debt action and from the repayment modal as `Простить остаток`
  - debt cards, history, and dashboard preview now use chips for `Погашено` and `Прощено`
- currency UX finalized around:
  - `Покупка / Продажа` terminology in FX contexts
  - inline currency selector next to amount in regular operation mode
  - conditional `Курс в базовую валюту` only for non-base operations
  - tighter currency modal flow:
    - `Покупка / Продажа`
    - `Дата | Валюта`
    - `Количество | Курс | Комиссия`
    - `Комментарий`
  - contextual trade semantics:
    - for `Покупка`, the main amount field is the spent base/quote amount
    - for `Продажа`, the main amount field is the sold asset quantity
  - direction-aware FX preview:
    - buy: `BYN -> USD`
    - sell: `USD -> BYN`
  - analytics currency history backfill
  - combined multi-line chart for `Все` in `Аналитика -> Валюта`
  - dashboard currency balances row and rate widgets with last-known-rate fallback
  - dashboard currency widgets keep comparing against the previous real snapshot even if the new official day has not been published yet
  - receipt and preview flows now recalculate `≈ BYN` by the latest available rate instead of falling back to `1:1`
  - debt create/edit flow now keeps counterparty suggestions available even before visiting the debts section
  - debt create amount + currency layout now follows the same row pattern as the operation modal
  - debt card info is de-duplicated:
    - redundant `Погашено` chip removed from the card action area
    - forgiveness amount stays in the card meta/history context instead of crowding the action column
- targeted e2e coverage for:
  - currency analytics `Все`
  - debt forgiveness flow

Remaining polish only:
- richer dashboard/widget polish such as sparkline or extended daily change metadata
- broader e2e coverage for all multi-currency operation / plan / debt permutations if needed
- settings/reminders polish:
  - replace the current checkbox-only reminder UX with explicit `Вкл / Выкл` scenario controls
  - expose a unified currency-notifications contract where disabling the scenario also disables digest time and threshold-alert inputs
  - add a dedicated persisted enable flag for currency threshold alerts instead of treating filled thresholds as implicitly active forever
- optional UX extension:
  - extend the same currency-scope control pattern to similar list views where it stays meaningful beyond operations
  - this should help separate domestic/base-currency cashflow from foreign-currency activity quickly
- immediate post-rollout regression batch:
  - current corrective slice:
    - step 1: dashboard currency cards
      - remove duplicated comparison text
      - keep delta visually close to the main rate value, not detached on another edge of the card
    - step 2: operation / plan / currency preview math
      - keep currency-deal preview rate identical to the rate shown in the input field
      - limit currency selectors to tracked currencies where current-rate autofill is expected
      - when selectors are restricted, still preserve the currently stored currency while editing old records
      - keep amount labels and receipt-position labels synchronized with the selected currency
      - stop showing a visible manual FX field in regular operation mode when the rate should be auto-derived
    - step 3: debt create and debt card polish
      - place counterparty field directly below `Я дал / Я взял`
      - keep amount + currency on the next row with the same proportions/pattern as regular operation create flow
      - keep debt-row kebab in the top-right card corner by the established pattern
    - step 4: dashboard currency widget final alignment
      - keep compare metadata visually attached to the main rate value instead of drifting to the far right edge

## Agreed Implementation Order

1. Reminders
- prefs schema changes
- frontend `Вкл / Выкл` scenario toggles
- dedicated alert enable flag
- backend gating for digest / alerts delivery

2. Analytics
- secondary currency summary in calendar
- do this without rewriting the existing calendar backend in the initial pass

3. Skeleton
- `Аналитика -> Валюта`
- standalone `Валюта` section
- dashboard currency panel

## Agreed Product Direction

- `BYN` remains the main base currency for totals, portfolio valuation, and profit/loss calculations.
- Currency should not be modeled as a plain income/expense operation only.
- Currency deals should have their own domain model and their own UI mode, while still fitting naturally into the existing app flow.
- The app should support optional tracked currencies such as `USD`, `EUR`, `RUB`, and others.
- Dashboard should get a separate currency KPI row above the period KPI block.
- A dedicated `Валюта` section should be added.
- `Добавить операцию` should get a separate mode/tab for currency deals.
- `Аналитика` should get a dedicated `Валюта` tab.
- Exchange rates should be refreshed daily.
- Telegram should be able to send a daily currency digest for tracked currencies.
- Operations, plans, and debts should later support their own original currency in addition to the base currency.
- Plans should not fix an exchange rate at creation time.
- Plans should display live conversion to base currency by the latest available rate.
- Operations should keep a historical fx snapshot for accounting, but can display a live `≈ base currency` secondary label.
- Debts should keep original currency as the source of truth and display current base-currency equivalent in UI.
- Debt forgiveness should be represented as:
  - action: `Простить долг`
  - close reason: `forgiven`
  - final status: `Закрыт`
  - secondary status/meta: `Прощен`

## Terminology

Use user-facing wording instead of `PnL`.

Preferred labels:
- `Прибыль / убыток`
- `Результат по валюте`
- `Текущая оценка`
- `Средняя цена покупки`
- `Отклонение от текущего курса`

Avoid in UI by default:
- `PnL`
- `unrealized`
- `realized`

Possible internal/technical terms:
- `unrealized_pnl_base`
- `realized_pnl_base`

These can stay in code/model names if needed, but UI should show clearer wording.

## UX Agreement

### 1. Dashboard

Add a new row above the current dashboard KPI block:
- `Валютный портфель`
- total current valuation in `BYN`
- total profit/loss in `BYN`

Below or inside the row show mini-cards for tracked currencies:
- currency code: `USD`, `EUR`, `RUB`
- current quantity
- average buy price
- current rate
- current valuation in `BYN`
- profit/loss in `BYN`

Rules:
- show only currencies enabled for tracking
- if no currencies are tracked, hide the block or show a compact empty-state
- provide small force-refresh actions for rates directly in the block
- currency KPI wording should remain domain-specific:
  - action summaries use `Покупки` / `Продажи`
  - avoid reusing `Доход` / `Расход` in FX-specific summaries

### 2. Currency Section

Add a separate section: `Валюта`.

Preferred interaction:
- filter by currency via controls/chips
- not separate screens per currency

Why:
- simpler navigation
- easier to extend
- consistent with the rest of the app

Suggested structure:
- top summary block
- currency filter controls
- positions block
- deals history block
- current rates widget block

Suggested filters:
- `Все`
- `USD`
- `EUR`
- `RUB`
- dynamic tracked currencies

### 3. Add Operation Modal

Add a new mode/tab:
- `Операция`
- `Долг`
- `План`
- `Валюта`

For `Валюта` mode:
- action: `Покупка` / `Продажа`
- currency
- quantity
- exchange rate
- fee
- trade date
- note

The original purchase price must always be fixed in the trade record.

Interaction rule:
- CTA `Сделка` from the `Валюта` section should open the shared create modal directly on the `Валюта` tab
- avoid keeping a competing inline trade form on the section page
- do not show the regular `Расход / Доход` switch while the modal is in `Валюта` mode

For regular `Операция` mode:
- keep the amount and currency tightly coupled in one row
- render currency as a compact inline selector near the amount field, without a separate label block
- show `Курс в базовую валюту` only when the selected currency differs from the main base currency

### 4. Analytics

Add a new analytics tab: `Валюта`.

Preferred scope for first release:
- selected currency filter
- current position metrics
- exchange rate trend
- deal history
- selectable history period with a sensible default of `30 days`

Preferred internal layout:
- top KPI strip
- rate chart
- position/result chart or summary
- trade list

This is better than mixing currency into the existing category/expense/income analytics.

### 5. Settings

Add settings for:
- base currency: default `BYN`
- tracked currencies
- show/hide currency KPI on dashboard
- enable/disable daily Telegram currency digest
- optional thresholds for future notifications

## Data Model Direction

Recommended first implementation:
- weighted average cost model
- not FIFO in V1

Needed entities:

### `fx_trade`
- id
- user_id
- side: `buy` / `sell`
- asset_currency
- base_currency
- quantity
- rate
- fee_base
- trade_date
- note
- created_at

### `fx_position`
- user_id
- currency
- quantity
- average_buy_rate
- invested_base
- current_rate
- current_value_base
- profit_loss_base
- updated_at

### `fx_rate_snapshot`
- currency
- base_currency
- rate
- snapshot_date
- source
- created_at

### `tracked_currency`
- user_id
- currency
- dashboard_visible
- notifications_enabled
- sort_order

## Calculation Rules

### Current valuation
- `current_value_base = quantity * current_rate`

### Book value
- `invested_base = quantity * average_buy_rate`

### Profit/loss
- `profit_loss_base = current_value_base - invested_base`

User-facing wording:
- `Прибыль`, if positive
- `Убыток`, if negative
- `Результат`, as neutral wording

### First release accounting model

Use weighted average price:
- easier to explain
- easier to implement
- good enough for personal finance use

Do not start with FIFO unless there is a hard accounting reason.

## Notifications

### Daily Telegram Digest

Add once-a-day Telegram message for tracked currencies.

Recommended daily digest content:
- currency code
- current rate
- change vs previous day
- current position quantity
- current valuation in `BYN`
- profit/loss in `BYN`

Example structure:
- `USD: курс 3.27, +0.04 за день, позиция 1200 USD, оценка 3924 BYN, результат +108 BYN`
- `EUR: курс 3.54, -0.02 за день, позиция 300 EUR, оценка 1062 BYN, результат -21 BYN`

Digest rules:
- send only if user enabled it
- once per day
- only for tracked currencies

### Future notification layer

Not part of the first MVP, but compatible with the model:
- threshold crossed
- daily change above X%
- position result above/below threshold

## V1 Scope

Ship first:
- `Валюта` section
- currency mode in add-operation modal
- tracked currencies in settings
- daily stored exchange rate
- current positions by tracked currencies
- dashboard currency KPI row
- analytics currency tab
- daily Telegram digest for tracked currencies

## V1.1 Scope

Later:
- richer charts for currency position history
- improved breakdown widgets
- historical valuation snapshots
- configurable chart ranges and optional custom date range for currency analytics

## V1.2 Scope

Later:
- threshold-based alerts
- per-currency notification rules
- more detailed profit/loss split for partial sales

## Phase 2 Roadmap: Multi-Currency Records Beyond FX

After the current FX slice is stable, extend the rest of the app:

### Operations
- add original `currency` to operations
- store `amount`, `currency`, `base_amount`, `base_currency`, `fx_rate`
- keep entered value and converted base value together

Status:
- implemented in current slice

### Plans
- add original `currency` to plans
- define how plan-vs-fact comparison works when currencies differ
- decide whether conversion should use the planned rate, actual operation rate, or current rate depending on screen

### Debts
- add original `currency` to debts and repayments
- preserve debt principal and outstanding amount in source currency
- show both source-currency balance and base-currency valuation where appropriate

Implementation rule:
- do not start this phase by just adding a `currency` field everywhere
- each entity must store both original currency data and base-currency conversion snapshot

## Open Decisions

- Which source should provide daily exchange rates?
- Should user be allowed to manually override a daily rate?
- Do we need support for currency cash accounts separately from exchange trades in V1?
- Should fees always be stored in base currency or support fee currency too?
- Should hidden tracked currencies remain in history and analytics filters?

## Recommended Implementation Order

1. Data model and migrations
- trades
- positions
- rate snapshots
- tracked currencies

2. Settings and tracked currencies
- enable/disable tracked currencies
- dashboard visibility
- telegram digest toggle

3. Currency deal entry
- new modal mode
- create/update/delete flows

4. Currency section
- filters
- positions
- deals
- rates widget

5. Dashboard currency KPI row
- total portfolio
- per-currency cards

6. Analytics currency tab
- rates + position/result view

7. Daily Telegram digest
- scheduler
- digest format
- user preference integration

## Implementation Plan

### Backend

#### New tables

1. `fx_trades`
- purpose: immutable history of currency buy/sell actions
- columns:
  - `id`
  - `user_id`
  - `side`
  - `asset_currency`
  - `base_currency`
  - `quantity`
  - `rate`
  - `fee_base`
  - `trade_date`
  - `note`
  - `created_at`
  - `updated_at`

2. `fx_positions`
- purpose: materialized current position per user/currency
- columns:
  - `id`
  - `user_id`
  - `currency`
  - `base_currency`
  - `quantity`
  - `average_buy_rate`
  - `invested_base`
  - `current_rate`
  - `current_value_base`
  - `profit_loss_base`
  - `last_trade_at`
  - `last_rate_at`
  - `updated_at`

3. `fx_rate_snapshots`
- purpose: historical daily exchange rates
- columns:
  - `id`
  - `currency`
  - `base_currency`
  - `rate`
  - `snapshot_date`
  - `source`
  - `created_at`

4. `tracked_currencies`
- purpose: per-user visibility and notification preferences
- columns:
  - `id`
  - `user_id`
  - `currency`
  - `dashboard_visible`
  - `analytics_visible`
  - `notifications_enabled`
  - `sort_order`
  - `created_at`
  - `updated_at`

#### Service layer

Recommended backend services:

1. `fx_trade_service`
- create trade
- edit trade
- delete trade
- validate trade payload
- trigger position recalculation

2. `fx_position_service`
- rebuild one position from trade history
- rebuild all user positions
- compute weighted average cost
- compute current valuation
- compute profit/loss

3. `fx_rate_service`
- fetch latest daily rates
- store snapshots
- resolve latest rate for tracked currencies
- provide historical rate series for analytics

4. `fx_dashboard_service`
- aggregate dashboard currency KPI
- build per-currency mini-cards

5. `fx_notification_service`
- build telegram digest text
- send once-a-day currency digest

### API

#### New endpoints

##### Trades

- `GET /api/v1/fx/trades`
  - list trades
  - filter by currency
  - filter by side
  - paginate

- `POST /api/v1/fx/trades`
  - create buy/sell trade

- `PATCH /api/v1/fx/trades/{id}`
  - edit trade

- `DELETE /api/v1/fx/trades/{id}`
  - delete trade

##### Positions

- `GET /api/v1/fx/positions`
  - all current positions
  - filter by tracked/visible

- `GET /api/v1/fx/positions/{currency}`
  - detailed position for one currency

##### Rates

- `GET /api/v1/fx/rates/latest`
  - latest rates for tracked currencies

- `GET /api/v1/fx/rates/history?currency=USD&period=month`
  - historical daily rate series

- `POST /api/v1/fx/rates/refresh`
  - manual refresh
  - probably admin/internal first

##### Dashboard / analytics

- `GET /api/v1/dashboard/fx/summary`
  - total currency portfolio valuation
  - total profit/loss
  - per-currency dashboard cards

- `GET /api/v1/dashboard/fx/analytics`
  - summary for analytics tab
  - position trend
  - rate trend

##### Tracking preferences

- `GET /api/v1/fx/tracked`
  - list tracked currencies for user

- `PUT /api/v1/fx/tracked`
  - replace/update tracked currencies config

#### Suggested response shapes

##### Dashboard summary

```json
{
  "base_currency": "BYN",
  "portfolio_value_base": "4986.40",
  "profit_loss_base": "154.32",
  "currencies": [
    {
      "currency": "USD",
      "quantity": "1200.00",
      "average_buy_rate": "3.18",
      "current_rate": "3.27",
      "current_value_base": "3924.00",
      "profit_loss_base": "108.00"
    }
  ]
}
```

##### Position detail

```json
{
  "currency": "USD",
  "base_currency": "BYN",
  "quantity": "1200.00",
  "average_buy_rate": "3.18",
  "invested_base": "3816.00",
  "current_rate": "3.27",
  "current_value_base": "3924.00",
  "profit_loss_base": "108.00",
  "last_rate_at": "2026-03-27"
}
```

### Frontend

#### New section

Add `Валюта` to main navigation.

Suggested section structure:
- top KPI strip
- tracked-currency filter controls
- positions list
- trade history list/table
- current rates widget

Suggested runtime modules:
- `app-features-fx.js`
- `app-features-fx-rates.js`
- `app-features-fx-analytics.js`
- `app-features-fx-modal.js`

#### Add Operation modal integration

Extend create flow mode selector:
- `operation`
- `debt`
- `plan`
- `currency`

For currency mode, add:
- side toggle
- currency select
- quantity
- rate
- fee
- date
- note

Suggested principle:
- reuse existing modal shell
- do not force FX trades into generic income/expense form fields
- keep payload and preview clearly separate

#### Dashboard

Add a new dashboard block below current KPI:
- `Валютный портфель`
- total valuation
- total result
- currency cards

This block should:
- respect tracked currencies
- be hideable through settings
- later support skeleton and inline refresh the same way as other dashboard blocks

#### Analytics

Add new analytics tab:
- `Валюта`

Suggested controls:
- currency filter
- period filter
- chart mode toggle:
  - `Курс`
  - `Позиция`

Suggested panels:
- KPI summary
- daily rate trend
- position/result trend
- trade history

#### Settings

Add settings controls:
- base currency
- tracked currencies
- show dashboard currency block
- enable daily telegram digest

### Background Jobs

#### Daily rate refresh

Add scheduled job:
- runs once per day
- fetches rates for supported currencies
- stores a daily snapshot
- refreshes current rates in positions

#### Daily telegram digest

Add scheduled job:
- runs once per day after rates update
- finds users with notifications enabled
- sends digest for tracked currencies

Recommended order:
1. update rates
2. rebuild current valuations
3. send digest

### UI Copy Guidance

Use consistent labels:
- `Валютный портфель`
- `Текущая оценка`
- `Средняя цена покупки`
- `Текущий курс`
- `Прибыль`
- `Убыток`
- `Результат`

Avoid in first release:
- accounting jargon
- `PnL`
- `realized / unrealized` in UI

### Migration Strategy

#### Phase 1
- add schema
- no UI exposure yet
- seed tracked currencies config if needed

#### Phase 2
- add trade create/list endpoints
- add section UI

#### Phase 3
- add dashboard block
- add analytics tab

#### Phase 4
- add daily rates updater
- add telegram digest

### V1 Delivery Slice

To keep scope under control, V1 should include only:
- tracked currencies in settings
- create/list currency trades
- current positions
- daily rate snapshots
- dashboard currency KPI block
- basic analytics currency tab
- daily telegram digest

Explicitly out of V1:
- threshold alerts
- FIFO accounting
- advanced lot matching
- fee currency different from base currency
- complex broker/account modeling

### Suggested File/Module Impact

Likely backend impact:
- new SQLAlchemy models
- new Alembic migration
- new service modules under `app/services`
- new API router under `app/api/v1`
- scheduler/background task integration

Likely frontend impact:
- new nav item
- new section template
- new modal mode
- new settings controls
- dashboard template extension
- analytics tab extension

### Readiness Checklist Before Coding

- pick exchange-rate source
- confirm supported currencies list
- confirm weighted average cost for V1
- confirm digest timing for Telegram
- confirm whether dashboard block is visible by default when tracked currencies exist
