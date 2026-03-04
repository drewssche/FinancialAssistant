# Implementation TODO

Статусный roadmap по согласованным задачам. Используется как основной чеклист реализации.

## Stage 0 - Context Freeze
Status: completed
- Зафиксированы продуктовый контекст, таксономия, UI-system, архитектурные решения.
- Зафиксировано правило: если пользователь пишет `давай согласуем`, реализация ставится на паузу.

## Stage 1 - Tech Debt Baseline
Status: completed
- [x] Перевести `startup` с `on_event` на lifespan.
- [x] Перевести `datetime.utcnow()` на timezone-aware UTC.
Definition of done:
- Нет deprecation warnings по этим пунктам в тестовом прогоне.

## Stage 2 - UI Decomposition (Partials)
Status: completed
- [x] Вынести шаблон на partial-компоненты:
  - header actions
  - KPI section
  - table section
  - operation modal
- [x] Исключить дубли в шаблонах.
Definition of done:
- Главный экран собирается из partials, поведение не меняется.

## Stage 3 - Button Taxonomy Completion
Status: completed
- [x] Привести все кнопки к ролям: `core-primary`, `primary`, `secondary`, `ghost`, `danger`.
- [x] Унифицировать состояния: `default/hover/active/disabled/loading`.
- [x] Закрепить порядок destructive-actions: secondary слева, danger справа.
Definition of done:
- Нет локальных исключений по стилям кнопок в текущем UI.

## Stage 4 - Reusable Search/Filter/Sort/Highlight Pattern
Status: completed
- [x] Реализован паттерн для таблиц доходов/расходов.
- [x] Вынести в переиспользуемый UI/JS-модуль для всех текущих и будущих окон.
- [x] Документировать контракт подключения нового table-section.
Definition of done:
- Новый блок подключается через конфиг без копипаста логики.

## Stage 5 - Category Taxonomy Cleanup
Status: completed
- [x] Подготовлена таблица переименований `old -> new`.
- [x] Добавлена миграция переименований и переноса операций.
- [x] Вынести runtime-seeding в миграционный/seed flow, минимизировать зависимость от кода.
Definition of done:
- Категории полностью data-driven из БД, без рассинхрона код/данные.

## Stage 6 - Category Groups (General -> Detailed)
Status: completed
- [x] Введена сущность `CategoryGroup` (name, color, order, archive).
- [x] Связь `Category -> CategoryGroup` добавлена.
- [x] Добавлен API CRUD групп и CRUD детальных внутри групп.
- [x] Добавлен перенос детальных между группами через API.
- [x] Добавлен reorder групп/детальных (drag sort order persistence).
- [x] Добавлен сценарий `детальная категория без группы`.
Definition of done:
- Управление категориями работает по иерархии group -> category.

## Stage 7 - Category Manager UX Rework
Status: completed
- [x] Аккордеоны групп в панели управления.
- [x] Hover action-chip с иконкой edit для групп и детальных.
- [x] Edit modal/sheet для группы и детальной (встроенный editor-sheet в панели).
- [x] Drag & drop между группами (desktop) + fallback "перенести" (через API).
- [x] Удаление с проверкой использования + archive-policy.
Definition of done:
- Панель визуально чистая, управление быстрым и безопасным.

## Stage 8 - Visual Semantics and Interaction Polish
Status: completed
- [x] Цветовые акценты чипов по общим категориям (groups) с единым state-map `default/hover/active/soft`.
- [x] Применить accent-state-map ко всем category-чипам (quick + popover `Еще` + manager) через один reusable pattern.
- [x] Закрепить re-use правило для control-чипа `Еще (N)` (visual trigger, не выбор значения).
- [x] Спец-стиль `Еще (N)` как раскрывающего control.
- [x] Иконки для счета + tooltip + равные размеры переключателей.
- [x] Плавные анимации появления для всех появляющихся UI-элементов (с учетом prefers-reduced-motion).
Definition of done:
- UI визуально консистентен, семантика элементов читается без подсказок.

## Low Priority / Future
- [ ] Мультивалютный контур (`Валюта`, курсы, пересчет, отчеты).
- [ ] Расширенная аналитика и экспорт.
- [ ] Переключатель масштаба UI (`0.75 / 0.85 / 1.0`) с сохранением в `localStorage`.

## Stage 9 - Chip Semantics Alignment
Status: completed
- [x] Исправить active-highlight category-чипов: повторять форму чипа без "квадратного" halo.
- [x] Сортировать чипы в popover `Еще` группами (cluster по цвету/группе), а не в смешанном порядке.
- [x] Перевести `Счет` на pill-форму как `Доход/Расход` с icon+text и одним tooltip-поведением (без дублей).
- [x] Перевести preview операции на единый chip-render (`Тип`, `Категория`, `Счет`).
- [x] Перевести таблицу последних операций на chip-render (`Тип`, `Категория`, `Счет`) с акцентной семантикой.
Definition of done:
- Семантика операции в модалке и таблице визуально идентична, чип-паттерн единый и повторно используемый.

## Stage 10 - Form and Group Icon Upgrade
Status: completed
- [x] Исправить clipping active-outline у category-чипов.
- [x] Добавить icon+text для `Общая категория` и синхронизировать в preview/таблицах.
- [x] Компактно отображать комментарий в preview/последних операциях.
- [x] Вынести дату в отдельный блок с быстрыми действиями (`Сегодня/Вчера/-1/+1`).
- [x] Добавить иконки групп категорий (модель+API+миграция+icon-picker в editor).
Definition of done:
- Форма операции и менеджер категорий визуально консистентны, иконография управляется централизованно.
