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
