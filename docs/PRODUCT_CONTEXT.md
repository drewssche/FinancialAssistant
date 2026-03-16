# Product Context

## Product Idea
Financial Assistant is a web-first personal finance tracker for income and expenses. The same backend API is designed to support both:
- Web application (primary UI)
- Telegram Mini App client (secondary UI)

Current delivery direction:
- near-term goal is controlled transition to production with Telegram-first authentication
- Telegram Mini App adaptation is not limited to responsive layout; it also includes Telegram WebApp runtime behavior and mobile-first interaction rules

## Core Jobs To Be Done
- Track income and expense operations quickly
- Optionally store receipt line-item details inside operation (`чек`) with discrepancy visibility
- Keep a clean category structure
- View simple but actionable dashboard totals
- Preserve user-selected display preferences between sessions
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
- on operation save, each line item price is persisted both in operation snapshot (`receipt_items.unit_price`) and in template price history timeline
- receipt template identity supports optional store grouping (`shop_name + position_name`) for more precise chip reuse
- Example: two `Еда` entries on the same date are stored as two separate operations.
- Period totals are calculated as sums of all operations in selected date range.
- Monthly totals work the same way: sum of all operation rows in that month range.

## List Loading Standard
- For tables/lists with potentially large volume, UI standard is:
- initial load `20` rows
- incremental load `+20` on scroll (infinite scroll)
- Backend pagination semantics stay internal (`page/page_size` or cursor), while classic numbered pagination controls are hidden.
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

## Aggregation Strategy for Trends (Planned)
- Keep raw operations atomic (event-level records) as the source of truth.
- For trend analytics, use aggregated views/queries on top (`day/week/month` buckets by kind/category), without merging original records.
- This keeps edit/delete auditability and avoids data loss, while still allowing fast trend calculations.
- Position-level analytics is explicitly deferred to backlog and not part of current MVP.

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
