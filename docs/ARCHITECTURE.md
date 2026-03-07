# Architecture

## High-Level
- Backend: FastAPI
- DB: PostgreSQL
- Migrations: Alembic
- Cache/queue-ready: Redis
- Runtime: Docker Compose

## Layering
- `api`: transport and validation
- `services`: business workflows
- `repositories`: DB access patterns
- `db/models`: persistence schema
- `schemas`: API contracts

## Auth Model
- Provider-first identities (`auth_identities`)
- Single internal user profile (`users`)
- Telegram provider in MVP-1
- Google provider planned with same identity model

## Shared API for Multi-Client
One API serves both Web and Telegram Mini App clients.
Client-specific logic stays at UI layer; domain logic stays in backend services.

## Operations Receipt Extension (MVP)
- Add receipt-detail entities linked to operation:
- `operation_receipt_items` (snapshot line items inside operation)
- `operation_item_templates` (reusable chip catalog per user)
- `operation_item_prices` (immutable price history per template)
- Service-level rules:
- operation amount is source-of-truth for totals, but receipt total/discrepancy are computed and exposed
- save is allowed with discrepancy (warning use-case)
- template price history appends on each use; old prices are preserved
- template resolution for receipt items is batch-oriented (prefetch by `(name_ci, source_ci)` + bulk price inserts) to avoid N+1 query growth on long receipts
- category-at-line-item is out of current MVP scope

## Debt Module (Planned Architecture)
- Add dedicated domain objects (separate from category semantics):
- debt counterparty card (`debt_counterparties`)
- debt entries (`debts`) with principal, dates, direction (`lend`/`borrow`)
- repayment entries (`debt_repayments`) linked to debt entry
- Aggregation rules in service layer:
- card outstanding = sum(principal) - sum(repayments)
- card status (`active`/`closed`) is computed from outstanding
- API-first reuse:
- web and Telegram Mini App use same debt endpoints
- dashboard receives compact active-debt summary endpoint (not full debt history payload)
