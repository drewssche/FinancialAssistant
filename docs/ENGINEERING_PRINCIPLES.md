# Engineering Principles

## Performance and Reuse
- API-first architecture for maximum reuse between Web and Telegram Mini App
- Reuse business logic through service and repository layers
- Push filtering/pagination/sorting to server side
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

## Reliability
- DB constraints and indexes from day one
- Alembic migrations required for schema changes
- Structured logging and request tracing ids (next iterations)
