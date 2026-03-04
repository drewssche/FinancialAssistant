# Project Log

## 2026-03-02
- Перезапуск проекта с чистого листа.
- Цель MVP: учет доходов/расходов по структуре таблицы `Финансы.xlsx`.
- Принято решение: на первом этапе не включать долги и переводы в интерфейс операций.
- Реализован UI главной страницы:
  - кнопка `+ Добавить операцию`;
  - модальное окно с полями операции;
  - выбор общей категории `Доход/Расход`;
  - динамическая подстановка подкатегорий для выбранного типа;
  - аналитический блок с переключением `День/Неделя`;
  - табличные секции по доходам/расходам и последние операции.
- Подкатегории взяты по примеру `Финансы.xlsx` и очищены от долговых/переводных пунктов.

## Governance Update
- Зафиксирована командная договоренность:
  - если пользователь пишет `давай согласуем`, реализация не начинается;
  - сначала обсуждаем идею и варианты;
  - разработка стартует только после явного подтверждения (`делай`, `ок`, `внедряем`).

## Docs Baseline Added
- Добавлены документы проекта:
  - `docs/PRODUCT_CONTEXT.md`
  - `docs/TAXONOMY.md`
  - `docs/UI_SYSTEM.md`
  - `docs/ARCHITECTURE.md`
  - `docs/ENGINEERING_PATTERNS.md`
  - `docs/ADR/ADR-001-stack-postgres-docker.md`
  - `docs/ADR/ADR-002-ui-action-hierarchy.md`

## 2026-03-02 (infra/backend upgrade)
- Переведено хранилище операций с JSON на PostgreSQL.
- Внедрен SQLAlchemy слой:
  - `app/db/*` (engine/session/base)
  - `app/models/operation.py`
  - `app/services/operations.py`
  - `app/core/config.py`, `app/core/taxonomy.py`
- Обновлен `app/main.py` для работы через DB-сессию.
- Добавлена контейнеризация:
  - `Dockerfile`
  - `docker-compose.yml` (`api` + `db`)
  - `.env.example`
  - `.dockerignore`
- Добавлен Alembic baseline:
  - `alembic.ini`
  - `alembic/env.py`
  - `alembic/versions/20260302_0001_create_operations.py`
- Удален JSON storage (`data/operations.json`).
- Исправлен docker port conflict для PostgreSQL:
  - `db` порт на хосте изменен на `${DB_EXPOSE_PORT:-5433}`.
- Исправлено подключение API внутри docker-сети:
  - `DATABASE_URL` в сервисе `api` теперь указывает на `db:5432`.

## 2026-03-02 (routing/tests)
- Роуты вынесены из `app/main.py` в `app/api/routes.py`.
- `app/main.py` переведен на orchestration:
  - include router
  - mount static
  - startup init DB
- Добавлен флаг `SKIP_DB_INIT=1` для изолированных тестов.
- Добавлены базовые API-тесты (`pytest`):
  - создание операции
  - day/week summary
  - валидационная ошибка по подкатегории
- Добавлен `pytest.ini` и зависимость `pytest`.

## 2026-03-02 (ui edit mode + chip pickers)
- Core CTA `+ Добавить операцию` перенесен под заголовок и выровнен по центру.
- В модалке `select` заменены на лаконичные chip-пикеры:
  - подкатегории (с поиском)
  - счета
- Добавлен режим редактирования операции в той же модалке:
  - загрузка данных операции
  - сохранение изменений
  - удаление с подтверждением
- В таблице последних операций добавлена колонка `Действие` с кнопкой `Изменить`.
- Добавлены API-эндпоинты для CRUD-операций:
  - `GET /api/operations/{id}`
  - `PUT /api/operations/{id}`
  - `DELETE /api/operations/{id}`
- `POST /api/operations` теперь возвращает `id` созданной операции.
- Расширены тесты API на сценарии редактирования и удаления.

## 2026-03-02 (category ux refinement)
- Согласованы и внедрены правки UX для подкатегорий:
  - поиск категории оставлен как основной способ;
  - показываются только top-6 чипов;
  - остальные категории доступны через кнопку `Еще` в popover-блоке;
  - при отсутствии совпадений показывается `Создать категорию "..."`.
- Добавлено управление категориями:
  - список категорий по выбранному типу (`Доход/Расход`);
  - переименование категории;
  - удаление категории (запрещено, если категория уже используется в операциях).
- Добавлены backend API для категорий:
  - `GET /api/categories?kind=...`
  - `POST /api/categories`
  - `PUT /api/categories/{id}`
  - `DELETE /api/categories/{id}`
- Категории переведены на хранение в БД (таблица `categories`) с сидингом дефолтных значений.
- UI-переключатели (`Общая категория`, `Счет`) сделаны компактными: fit-content без растяжения на всю ширину.
- Из MVP исключен счет `Валюта`, оставлены `Карта` и `Наличные`.
- `Валюта` перенесена в low-priority backlog как future enhancement (вместе с мультивалютным учетом).

## 2026-03-02 (ui consistency + table pattern)
- Для destructive actions унифицирован порядок кнопок:
  - secondary слева, danger справа.
- Для режима `День/Неделя` добавлен явный текст периода:
  - `День: dd.mm.yyyy`
  - `Неделя: dd.mm.yyyy - dd.mm.yyyy`
- Для блоков `Доходы/Расходы` внедрен reusable table pattern:
  - поиск
  - фильтр по минимальной сумме
  - сортировка
  - подсветка совпадений (highlight)
  - колонка `Доля` для наглядности структуры трат/доходов.
- Управление категориями переведено из отдельной модалки в side-panel внутри текущей модалки операции.
- Подкатегории в модалке адаптированы под одну строку чипов (динамический fit) + чип `Еще`.

## 2026-03-02 (taxonomy cleanup + panel animation)
- Добавлена документированная таблица переименований категорий:
  - `docs/CATEGORY_TAXONOMY_RENAME.md`
- Добавлена миграция таксономии:
  - `alembic/versions/20260302_0003_rename_category_taxonomy.py`
- Обновлен дефолтный справочник категорий (`DEFAULT_CATEGORY_MAP`) под новые названия.
- Панель `Управление категориями` переделана в присоединенный правый блок к модалке:
  - модалка не сжимается внутри;
  - центрируется весь блок (модалка + панель);
  - панель без горизонтального скролла;
  - sticky header внутри панели;
  - кнопки действий строки показываются по hover.
- Добавлены плавные анимации появления для основных интерфейсных элементов:
  - карточки/хедер страницы
  - модалка и popover
  - правая панель управления
  - строки списка категорий

## 2026-03-03 (context sync)
- Перед следующим циклом реализации зафиксирован единый roadmap/checklist:
  - `docs/IMPLEMENTATION_TODO.md`
- В roadmap отражены все согласованные этапы:
  - tech debt (`lifespan`, timezone-aware datetime)
  - UI decomposition на partials
  - button taxonomy completion
  - reusable search/filter/sort/highlight
  - category groups и UX rework управления категориями
  - visual semantics (group accents, `Еще (N)`, icons + tooltips)

## 2026-03-03 (stage 1 + stage 2)
- Закрыт Tech Debt Baseline:
  - `startup` переведен с `on_event` на `lifespan`.
  - `datetime.utcnow()` заменен на timezone-aware UTC (`datetime.now(UTC)`).
- Закрыт UI Decomposition:
  - `templates/index.html` разложен на partial-шаблоны (`templates/partials/*`).
  - Вынесены отдельные блоки: header actions, KPI section, category table section, recent operations section, operation modal.
- Проверка: `docker compose exec api python -m pytest -q` -> `6 passed`.

## 2026-03-03 (stage 3 partial + stage 4 complete)
- Stage 3 (частично):
  - добавлены единые loading-state для action-кнопок через helper `setButtonLoading(...)`.
  - добавлен визуальный `is-loading` state в CSS.
- Stage 4 (завершен):
  - вынесен reusable table-pattern в `static/table_pattern.js`.
  - `static/app.js` переведен на использование модульного table-controller (config-based).
  - подключение фронтенд-логики переведено на `type=module`.
  - добавлена документация контракта: `docs/TABLE_PATTERN.md`.
- Проверка: `docker compose exec api python -m pytest -q` -> `6 passed`.

## 2026-03-03 (stage 3 complete)
- Полностью унифицирована button taxonomy на текущем UI:
  - внедрен базовый класс `btn` + role-модификаторы (`btn--core`, `btn--primary`, `btn--secondary`, `btn--ghost`, `btn--danger`, `btn--toggle`, `btn--chip`).
  - удалены legacy-классы кнопок из шаблонов и JS-генерации.
- Унифицированы состояния кнопок:
  - `default/hover/active/disabled/loading`.
  - добавлен единый loading-indicator через `is-loading`.
- Порядок destructive-actions зафиксирован по экрану:
  - secondary слева, danger справа.

## 2026-03-03 (stage 6 + stage 7 in progress)
- Добавлена иерархия категорий `group -> category` на уровне моделей/данных:
  - новая сущность `CategoryGroup`;
  - `Category` расширен полями `group_id`, `sort_order`, `is_archived`.
- Добавлена миграция:
  - `alembic/versions/20260303_0004_category_groups.py`
  - миграция сделана идемпотентной для уже частично созданной runtime-схемы.
- Backend API расширен:
  - `GET /api/category-groups?kind=...` (группы с вложенными категориями)
  - `POST /api/category-groups`
  - `PUT /api/category-groups/{id}`
  - `DELETE /api/category-groups/{id}`
  - `PUT /api/categories/{id}` теперь поддерживает перенос в другую группу (`group_id`).
- UI управления категориями переработан:
  - правая панель отображает группы как аккордеоны;
  - hover action-chip для групп и детальных;
  - drag&drop переноса категории между группами;
  - добавлен чип `Еще (N)` и акцентные цвета чипов по группе.
- Исправлен баг дублирования категорий в блоке `Еще`.
- Тесты:
  - добавлен тест `test_category_group_create_and_move_category`;
  - `docker compose exec api python -m pytest -q` -> `7 passed`.

## 2026-03-03 (manager editor-sheet)
- Убраны `prompt`-сценарии редактирования категорий/групп в UI.
- Добавлен встроенный editor-sheet в правой панели управления категориями:
  - редактирование и создание группы (название + цвет);
  - редактирование и создание детальной категории;
  - перенос категории в другую группу через select в editor-sheet;
  - удаление группы/категории из editor-sheet.
- Обновлены стили панели под editor-sheet без горизонтального скролла.
- Проверка: `node --check static/app.js` и `docker compose exec api python -m pytest -q` -> `7 passed`.

## 2026-03-03 (archive-policy + persist reorder)
- Добавлены backend API для soft-archive:
  - `PUT /api/categories/{id}/archive`
  - `PUT /api/category-groups/{id}/archive`
- Добавлены backend API для сохранения порядка:
  - `POST /api/categories/reorder` (bulk reorder категорий с group_id + sort_order)
  - `POST /api/category-groups/reorder` (порядок групп)
- Реализована archive-policy:
  - нельзя архивировать последнюю активную группу вида (`income`/`expense`);
  - архив группы архивирует вложенные категории;
  - удаление группы возможно только если она полностью пустая;
  - удаление категории с операциями по-прежнему запрещено.
- UI:
  - editor-sheet получил кнопку `Архивировать`;
  - drag&drop групп теперь сохраняет порядок;
  - drag&drop категорий сохраняет порядок внутри/между группами.
- Тесты:
  - добавлен сценарий `test_reorder_groups_and_categories_and_archive`;
  - `docker compose exec api python -m pytest -q` -> `8 passed`.

## 2026-03-03 (dn d fix + ungrouped + picker ux)
- Исправлен `Method Not Allowed` на DnD reorder:
  - статические роуты `/api/categories/reorder` и `/api/category-groups/reorder` вынесены выше динамических `/{id}`.
- Добавлена полноценная поддержка детальных категорий вне групп:
  - виртуальная секция `Без группы` в менеджере;
  - выбор `Без группы` в editor-sheet (`group_id = null`);
  - создание категории с `group_id = null` поддерживается.
- Улучшен UX блока подкатегорий:
  - кнопка `Создать категорию "..."` перенесена ближе к полю поиска;
  - `Еще (N)` теперь раскрывает popover, привязанный к кнопке `Еще`;
  - popover расширен по ширине.
- В панели управления улучшено использование высоты:
  - список групп занимает доступное пространство (`flex: 1`), без пустого нижнего блока.
- Усилен цветовой акцент чипов в окне управления категориями.
- Тесты:
  - добавлен тест `test_category_can_be_created_and_moved_to_ungrouped`;
  - `docker compose exec api python -m pytest -q` -> `9 passed`.

## 2026-03-03 (agreement: chip accent reuse)
- Зафиксирована договоренность по визуальной системе category-чипов:
  - единый accent-token группы (`--chip-accent`) для всех category-чипов;
  - единый state-map (`default/hover/active/soft`);
  - popover `Еще` использует тот же accent-pattern для категорий;
  - control-чип `Еще` остается нейтральным.
- Обновлены документы:
  - `docs/UI_SYSTEM.md`
  - `docs/IMPLEMENTATION_TODO.md`

## 2026-03-03 (chip accent state-map implementation)
- Реализован единый reusable accent-pattern для category-чипов:
  - один token группы `--chip-accent`;
  - единые состояния `default/hover/active/soft`.
- Accent-state-map применен ко всем category-чипам:
  - quick чипы в модалке операции,
  - чипы в popover `Еще`,
  - чипы в панели управления категориями.
- Control-чип `Еще` оставлен нейтральным (без наследования group accent).
- Проверка:
  - `node --check static/app.js`
  - `docker compose exec api python -m pytest -q` -> `9 passed`.

## 2026-03-03 (agreement: stage 8 continuation)
- Согласовано продолжение Stage 8 с обязательной фиксацией в MD перед кодом:
  - довести `Еще (N)` как control-trigger с отдельной семантикой;
  - внедрить icon-toggle для `Счет` с tooltip и равной геометрией;
  - унифицировать motion-паттерн появления UI-элементов с fallback `prefers-reduced-motion`.

## 2026-03-03 (stage 8 complete)
- Доведена visual-semantics часть Stage 8:
  - `Еще (N)` оформлен как явный control-trigger (dashed/neutral style + caret), без смешения с category selection.
  - Логика popover стабилизирована через единый `closeSubcategoryPopover()` (сброс active-state control-чипа).
- Блок `Счет` переведен на icon-toggle:
  - равные размеры account-чипов;
  - SVG-иконки вместо текста;
  - tooltip + aria-label для читаемости и доступности.
- Добавлен системный fallback для motion:
  - `@media (prefers-reduced-motion: reduce)` отключает animation/transition.
- Проверка:
  - `node --check static/app.js`
  - `docker compose exec api python -m pytest -q` -> `9 passed`.

## 2026-03-03 (stage 5 seed-flow completion)
- Убрана зависимость API-запросов от runtime-seeding:
  - вызовы `ensure_default_categories(...)` удалены из роутов и из `get_category_map`.
- Сидинг дефолтных категорий перенесен в seed-flow:
  - one-time сидинг на `lifespan` startup через `seed_default_categories(...)`;
  - тестовый seed добавлен в `tests/conftest.py` после `Base.metadata.create_all(...)`.
- Добавлен backward-compatible alias `ensure_default_categories(...)` в сервисе категорий для безопасного перехода.
- Проверка:
  - `node --check static/app.js`
  - `docker compose exec api python -m pytest -q` -> `9 passed`.

## 2026-03-03 (agreement: stage 9 chip semantics)
- Согласован новый этап выравнивания chip-паттернов:
  - исправить shape-safe active-highlight у category-чипов;
  - упорядочить popover `Еще` по группам/цветовым кластерам;
  - перевести `Счет` в pill icon+text без двойных tooltip;
  - унифицировать отображение `Тип/Категория/Счет` как чипов в preview и в таблице последних операций.

## 2026-03-03 (stage 9 complete)
- Исправлен active-highlight category-чипов:
  - ring теперь shape-safe и повторяет pill-геометрию (без прямоугольного halo).
- Popover `Еще` переведен на кластерную сортировку по группам:
  - grouping по `group_sort`, внутри по `category_sort`.
- `Счет` переведен на pill-переключатели с icon+text:
  - убран дублирующий tooltip-паттерн.
- Обновлен preview операции:
  - `Тип`, `Категория`, `Счет` отображаются как чипы с семантическими акцентами.
- Обновлена таблица последних операций:
  - `Тип`, `Категория`, `Счет` рендерятся чипами;
  - category-чипы в таблице получают accent цвета группы после загрузки справочника.
- Проверка:
  - `node --check static/app.js`
  - `docker compose exec api python -m pytest -q` -> `9 passed`.

## 2026-03-03 (stage 10 form/group icon upgrade)
- Исправлен visual clipping активной обводки category-чипов (shape-safe ring внутри pill-геометрии).
- `Общая категория` (`Расход/Доход`) переведена на icon+text toggle.
- Preview операции дополнен compact-comment строкой (truncate + title).
- Таблица последних операций получила compact-comment pattern.
- Дата вынесена в отдельный блок формы с быстрыми действиями:
  - `-1 день`, `Сегодня`, `Вчера`, `+1 день`.
- Добавлена поддержка иконок групп категорий end-to-end:
  - модель `CategoryGroup.icon`;
  - API create/update/serialize;
  - миграция `20260303_0005_category_group_icons.py`;
  - icon-picker в editor-sheet и отображение иконок в заголовках групп.
- Проверка:
  - `node --check static/app.js`

## 2026-03-03 (date strip + scrollbar system)
- В форме операции дата переведена с inline-календаря в строковый date-strip:
  - быстрый выбор в одну строку (окно -3..+3 вокруг выбранной даты),
  - подсветка `Сегодня` по таймзоне `Europe/Minsk`.
- Сохранен reusable-паттерн сеточного календаря:
  - `static/date_picker.js` оставлен как отдельный компонент для будущих экранов.
- Добавлен единый стиль скроллбаров для всего интерфейса:
  - `scrollbar-width/scrollbar-color` для Firefox,
  - `::-webkit-scrollbar*` для Chromium/WebKit.
- В roadmap добавлен отдельный low-priority пункт:
  - UI-scale toggle (`0.75 / 0.85 / 1.0`) с сохранением в `localStorage`.
  - `docker compose exec api python -m pytest -q` -> `9 passed`.

## Next
- Внедрить полную иерархию кнопок из `docs/UI_SYSTEM.md` по всем экранам.
- Разбить UI на переиспользуемые блоки (header actions, KPI section, table section, modal form).
- Унифицировать состояния элементов (`default/hover/active/disabled/loading`) и добавить loading-индикаторы.
- Low-priority future: мультивалютный контур (`Валюта`, курсы и пересчет).
