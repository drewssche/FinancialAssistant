# Engineering Principles

## Performance and Reuse
- API-first architecture for maximum reuse between Web and Telegram Mini App
- Reuse business logic through service and repository layers
- Push filtering/pagination/sorting to server side
- Client list rendering baseline for large datasets: initial `20` rows + incremental `+20` on scroll (infinite scroll UI over server pagination)
- Cache stable reference data when useful (categories, user preferences)

## Scalability Baseline
- PostgreSQL as primary datastore
- Redis included in compose for cache/session/queue evolution
- Dockerized local stack matching production concepts

## Code Organization
- Keep files small and focused by responsibility
- Soft file size target: 300-400 lines
- Hard refactor threshold: over 500 lines
- Avoid monolithic files and duplicate business logic
- Frontend code must be split into modules (`core`, `ui`, `features`) when file grows over 500 lines
- Shared UX behaviors (confirm, toast, undo, modal open/close) must be implemented as reusable helpers, not duplicated handlers

## Localization and Formatting
- Product UI language is Russian by default
- Date display format in UI tables/cards is `DD.MM.YYYY`
- Monetary and semantic statuses must use consistent meaning-based color patterns across all screens

## Reliability
- DB constraints and indexes from day one
- Alembic migrations required for schema changes
- Structured logging and request tracing ids (next iterations)
