# Product Context

Baseline reviewed against `e5eaee1` on 2026-10-12; purchase semantics updated through comparable quantity metrics (stage 2c). Current implementation is described here; agreed future changes are in [RECEIPTS_AND_PRODUCT_ANALYTICS_PLAN.md](RECEIPTS_AND_PRODUCT_ANALYTICS_PLAN.md).

## Product Idea
Financial Assistant is a web-first personal finance tracker for income and expenses. The same backend API is designed to support both:
- Web application (primary UI)
- Telegram Mini App client (secondary UI)

Current delivery direction:
- the application is deployed for a small controlled audience with Telegram-first authentication
- Telegram Mini App adaptation is not limited to responsive layout; it also includes Telegram WebApp runtime behavior and mobile-first interaction rules

## Core Jobs To Be Done
- Track income and expense operations quickly
- Optionally store receipt line-item details inside operation (`чек`) with discrepancy visibility
- Keep a clean category structure
- View simple but actionable dashboard totals
- Preserve user-selected display preferences between sessions
- Manage planned operations and recurring confirmations without mixing forecasts with completed money flows
- Reuse common catalog products and source-specific offers, brands and categories
- Track work days, salary-cycle estimates and actual payroll payments
- Track personal debts with transparent progress:
- create debt records (`я дал` / `я взял`)
- record partial repayments (`мне вернули` / `я вернул`)
- keep one aggregated card per counterparty with outstanding amount

## Current Operation Semantics
- Each created operation is an independent record (no auto-merge by category/date).
- Operation may include optional receipt line items:
- operation amount can be entered manually or auto-derived from receipt items total
- if manual amount differs from receipt total, discrepancy is stored and shown as warning (non-blocking save)
- receipt items are reusable through per-user item templates with price history
- each purchase line keeps its paid price in the receipt snapshot; template price history is incomplete as an observation timeline because repeated price values are suppressed. For discounted lines it records a known regular price, not necessarily the paid price. Full observation history is planned.
- receipt template identity supports optional store grouping (`shop_name + position_name`) for more precise chip reuse
- Example: two `Еда` entries on the same date are stored as two separate operations.
- Period totals are calculated as sums of all operations in selected date range.
- Monthly totals work the same way: sum of all operation rows in that month range.
- Legacy receipt totals derive from quantity and paid unit price. New line discounts support an amount, percentage, or authoritative paid line total; a derived six-decimal unit price never overwrites that total. In the receipt editor, enable «Скидка», expand «Скидка от суммы позиции», and choose the calculation method. Amount/percent modes require an explicitly entered regular price; direct final can leave that price unknown. Optional sale units and package contents are available in product/receipt forms and preserved as independent purchase/plan snapshots. Unknown historic units remain unknown. Purchase frequency, sale pieces/packages, mass, volume and spending per currency are now separate metrics; shrinkflation comparisons remain planned.

## Plans, Catalog and Work

- Completed plans can be edited through linked operations, history and activity. Resuming recurrence is an explicit action; ordinary edits preserve completed status.
- A catalog product groups source offers while retaining source-specific names. Merge, separate, price-history and operation drilldown actions exist. The consolidated product modal, GTINs, retailer links, receipt OCR and website-price monitoring are future work.
- Work estimates use the salary cycle and employment settings. Actual earnings statistics use payment dates and payroll linkage; they do not count forecast salary as received money.
- Structure and financial calendar remain in their current analytics locations. Rarely used analytics views will be consolidated only after their useful workflows have replacements.

## List Loading Standard
- For paginated tables/lists with potentially large volume, the default UI pattern is:
- initial load `20` rows
- incremental load `+20` on scroll (infinite scroll)
- Backend pagination semantics stay internal (`page/page_size` or cursor), while classic numbered pagination controls are hidden.
- This is not universal implementation parity: the current product catalog fetches server pages of up to 100 until it has the full result set. Preserve correct search/sort behavior when changing that loading strategy.
- Grouped/collapsible table pattern is now validated in Position Catalog:
- parent group rows + nested child rows
- parent/child hierarchy should be visually explicit:
- parent rows use stronger surface + summary metas
- child rows use inset layout (`indent + left guide/rail`) instead of full heavy borders per row
- the same hierarchy contract is a reusable baseline for `Categories` and debt-by-counterparty views
- persisted collapse state per user preferences
- persisted sort preset per user preferences (`usage/recent/name`)
- active search auto-expands matched groups
- explicit group actions (`collapse all / expand all / reset`) for fast navigation in larger catalogs
- this pattern is a reusable baseline candidate for future Categories table refactor.

## Aggregation and Analytics
- Keep raw operations atomic (event-level records) as the source of truth.
- For trend analytics, use aggregated views/queries on top (`day/week/month` buckets by kind/category), without merging original records.
- This keeps edit/delete auditability and avoids data loss, while still allowing fast trend calculations.
- «Чаще всего покупали» ranks products by distinct expense receipts. «Позиции» separately shows packages, pieces, kg/l and paid line totals in each original currency. Repeated lines count once per product/receipt; missing historic units remain visibly unknown. Catalog edits do not alter past measurement totals.
- Trend/calendar/highlight queries and `/api/v1/dashboard/analytics/positions` are implemented. Catalog offers also link to price history and filtered operations. The future product view should consolidate these workflows without losing access to the underlying receipts.

## Debt Domain (Implemented MVP Baseline)
- Debt records are not expense/income categories; they are a separate workflow with dedicated fields:
- counterparty (`кому`/`кто`)
- principal amount
- start date
- due date
- note
- Each debt record belongs to a counterparty card.
- Counterparty card aggregates active debt records and current outstanding amount.
- Fully repaid cards are hidden from dashboard debt widget by default (kept in Debt section history/filter).

## Authentication Scope
MVP-1 production mode uses Telegram sign in only:
- Telegram WebApp `initData` inside Mini App
- Telegram Login Widget in regular browser when `TELEGRAM_BOT_USERNAME` is configured
- Google auth is planned as provider #2 without changing core user model.

## Production Scope (Current)
- first production target is a small controlled audience with admin-approved access
- release quality is defined by:
- stable Telegram auth
- predictable access governance (`pending/approved/rejected`)
- release checklist compliance
- acceptable request budgets and health-check metrics

## Telegram Mini App Scope (Current)
- Mini App is treated as a first-class client runtime, not just a resized desktop web UI
- required adaptation areas:
- narrow mobile screens
- touch-first navigation and actions
- Telegram WebApp container specifics (`initData`, viewport/safe-area, in-app browser constraints)
- API/domain logic remains shared with web client; Telegram-specific adjustments stay in UI/runtime layer

## Access Governance
- Product access is admin-governed:
- new users -> `pending`
- allowed users -> `approved`
- denied users -> `rejected`
- Admin identities are configured via env (`ADMIN_TELEGRAM_IDS`) and are auto-approved on login.
- Admin can remove user completely with all related DB data.

## Data Minimization
We store only the minimum profile data required for product operation:
- internal user id
- provider identity ids
- display name/avatar optional
- account status and timestamps

No password storage in MVP-1.
