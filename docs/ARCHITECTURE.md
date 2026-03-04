# Architecture

## Target Stack
- Backend: `FastAPI`
- DB: `PostgreSQL`
- ORM: `SQLAlchemy`
- Migrations: `Alembic`
- Frontend: server-side templates + vanilla JS (MVP), с последующим выделением компонентов
- Containerization: `Docker`, `docker-compose`

## Runtime Topology
- `api` container:
  - FastAPI приложение
  - доступ к PostgreSQL по внутренней сети docker compose
- `db` container:
  - PostgreSQL (persistent volume)

## Data Model (MVP)
- `operations`
  - `id` (uuid, pk)
  - `kind` (`income|expense`)
  - `subcategory` (text)
  - `amount` (numeric(12,2))
  - `occurred_on` (date)
  - `account` (text)
  - `comment` (text, nullable)
  - `created_at` (timestamp)
  - `updated_at` (timestamp)

## Service Boundaries
- `operation_service`: создание, валидация, чтение операций.
- `summary_service`: агрегация по периодам.
- `taxonomy_service`: конфигурация категорий/подкатегорий.

## API Guidelines
- REST-подход, префикс `/api`.
- Ошибки: единый формат (`detail`, `code` позже).
- Валидация через Pydantic схемы.

## Environments
- `.env` для конфигурации.
- Локально: `docker-compose up`.
- Далее: staging/prod через отдельные compose/k8s манифесты.

## Non-Functional Requirements
- Идемпотентность чтения и предсказуемые ошибки.
- Простая горизонтальная масштабируемость API.
- Бэкапы PostgreSQL и миграции без ручного SQL в проде.
