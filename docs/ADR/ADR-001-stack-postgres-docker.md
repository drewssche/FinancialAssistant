# ADR-001: Stack Baseline (FastAPI + PostgreSQL + Docker)

## Status
Accepted

## Context
Нужно построить расширяемый личный финансовый сервис с ростом от MVP до модулей долгов, подписок и бюджетирования.

## Decision
- Backend: FastAPI
- Database: PostgreSQL
- Containerization: Docker + docker-compose
- ORM/Migrations: SQLAlchemy + Alembic

## Consequences
### Positive
- Предсказуемый production-путь.
- Нормальная работа с транзакциями и агрегатами.
- Удобный локальный запуск и одинаковое окружение у всех участников.

### Trade-offs
- Сложнее старт, чем JSON/SQLite.
- Требуется дисциплина миграций и env-конфигурации.
