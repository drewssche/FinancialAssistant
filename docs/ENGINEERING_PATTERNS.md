# Engineering Patterns

## Backend Structure
Рекомендуемая структура:
- `app/api/` - роутеры
- `app/schemas/` - Pydantic схемы
- `app/models/` - SQLAlchemy модели
- `app/services/` - прикладная логика
- `app/repositories/` - доступ к данным
- `app/core/` - конфиг, db session, общие зависимости

Правило: роутер не содержит бизнес-логику, только orchestration.

## Frontend Reuse
- Все визуальные токены в одном файле (`tokens.css` или секция `:root`).
- Повторяющиеся UI-паттерны оформляются как:
  - шаблонные include-фрагменты (Jinja partials), или
  - JS-фабрики для таблиц/строк.
- Календарная сетка хранится как отдельный reusable-компонент (`static/date_picker.js`) и не привязывается к одному экрану формы.

## Validation Pattern
- Входная валидация на API уровне (Pydantic + дополнительные доменные правила).
- Запрет дублирования валидации в нескольких слоях без причины.

## Error Handling Pattern
- Публичные API ошибки без технических деталей.
- Логирование технических причин на backend.

## Migrations Pattern
- Каждое изменение схемы только через Alembic migration.
- Миграции должны быть обратимыми (where possible).

## Testing Pattern
- Unit tests: сервисы агрегации и валидации.
- API tests: критические endpoint-ы (`create operation`, `summary`).
- Минимальный gate: тесты на happy path + 2-3 негативных кейса.

## Performance Pattern
- Индексы по `occurred_on`, `kind`, `subcategory`.
- Агрегации периода выполняются SQL-запросами по мере роста данных.
