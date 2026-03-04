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
