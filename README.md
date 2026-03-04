# Financial Assistant

MVP-сервис для учета личных доходов и расходов по структуре таблицы `Финансы.xlsx`.

## Текущее состояние
- UI: модалка добавления операций, сводка день/неделя, таблицы.
- Backend: FastAPI + SQLAlchemy.
- DB: PostgreSQL.
- Infra: Docker + docker-compose.
- Миграции: Alembic.

## Быстрый запуск через Docker

1. Подготовить env:
```bash
cp .env.example .env
```

2. Поднять инфраструктуру:
```bash
docker compose up --build
```

Если локально уже занят `5432`, используется `DB_EXPOSE_PORT` (по умолчанию `5433`) для доступа к контейнерному Postgres с хоста.

3. Открыть приложение:
- `http://127.0.0.1:${APP_EXPOSE_PORT:-8010}`

## Локальный запуск без Docker

Требуется локальный PostgreSQL с параметрами из `.env`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Миграции

```bash
alembic upgrade head
```

## Тесты

```bash
pip install -r requirements.txt
pytest -q
```

## Документация
- `docs/PRODUCT_CONTEXT.md`
- `docs/TAXONOMY.md`
- `docs/UI_SYSTEM.md`
- `docs/ARCHITECTURE.md`
- `docs/ENGINEERING_PATTERNS.md`
- `docs/IMPLEMENTATION_TODO.md`
- `docs/TABLE_PATTERN.md`
- `docs/ADR/`

## Правило согласования
Если в коммуникации звучит `давай согласуем`, реализация ставится на паузу.
Сначала обсуждение, затем внедрение только после явного подтверждения.
