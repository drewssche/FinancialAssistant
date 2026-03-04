# UI System

## Button Hierarchy

### 1) Core Primary Button
- Назначение: главный CTA страницы.
- Пример: `+ Добавить операцию`.
- Правила:
  - На странице только один `core-primary`.
  - Максимальный визуальный вес (цвет, контраст, размер).
  - Размещается в зоне первого экрана (header/top area).

### 2) Primary Button
- Назначение: подтверждение действия внутри потока.
- Примеры: `Сохранить`, `Применить`.
- Правила:
  - Не конкурирует с `core-primary` на странице.
  - Допускается несколько в разных контейнерах (например, модалки).

### 3) Secondary Button
- Назначение: вспомогательные операции.
- Примеры: `День`, `Неделя`, `Фильтр`.
- Правила:
  - Ниже визуальный приоритет, чем у `primary`.

### 4) Ghost Button
- Назначение: безопасный выход без изменений.
- Примеры: `Отмена`, `Закрыть`.
- Правила:
  - Минимальный визуальный акцент.

### 5) Danger Button
- Назначение: разрушительные действия.
- Примеры: `Удалить`.
- Правила:
  - Только в контексте конкретной сущности.
- Всегда требует подтверждение (inline confirm или modal confirm).
  - В action-row всегда крайняя справа (secondary/primary слева, danger справа).

## CSS Mapping
- `btn`: базовый класс кнопки.
- `btn--core`: core-primary.
- `btn--primary`: primary action.
- `btn--secondary`: secondary action.
- `btn--ghost`: ghost action.
- `btn--danger`: danger action.
- `btn--toggle`: переключатели (день/неделя, доход/расход).
- `btn--chip`: чипы выбора.

## Chip Accent System
- Все category-чипы (quick, popover `Еще`, manager) используют единый accent-token группы: `--chip-accent`.
- Чипы control-типа (`Еще`, утилитарные действия) не наследуют accent группы.
- Единый state-map для accent-чипов:
  - `default`: слабый tint группы
  - `hover`: усиление tint + контраст border
  - `active`: самый интенсивный tint + ring/shadow группы
  - `soft`: тот же accent, но с пониженной интенсивностью (для popover/list вариантов)
- Запрещены локальные произвольные цвета для category-чипов вне token-модели.
- Для `Еще (N)` используется отдельный control-стиль:
  - dashed-border + нейтральный tint;
  - hover/active показывают, что это trigger раскрытия списка, а не выбор категории.
- Для чипов в `Еще` и в менеджере применяется тот же accent-state-map, что и для quick-чипов, без исключений.
- Для active-состояния запрещен прямоугольный halo: подсветка обязана повторять pill-геометрию чипа (`border-radius: inherit` + shape-safe ring).

## Account Switch Pattern
- Счета (`Карта`, `Наличные`, future `Валюта`) оформляются как pill-toggle с иконкой и текстом.
- Все account-toggle используют единый размер hit-area и те же state-правила (`default/hover/active/disabled`).
- Не допускается дублирование tooltip (одновременно native `title` + custom tooltip).

## Operation Chip Rendering
- `Тип`, `Категория`, `Счет` отображаются как чипы не только в форме выбора, но и в preview/табличных строках операций.
- Семантика цветов:
  - `Тип`: fixed semantic colors (`Доход`/`Расход`);
  - `Категория`: accent группы;
  - `Счет`: нейтральный либо мягкий account-accent, с icon+text.
- Для комментария используется compact-text pattern (truncate + full value в hover/title).

## Group Icon Pattern
- `CategoryGroup` поддерживает `icon` как first-class атрибут (БД/API/UI).
- В editor-sheet группы иконка выбирается из фиксированного пула icon-chip элементов.
- Группы в менеджере отображают иконку в заголовке рядом с названием.

## Date Input Pattern
- Дата операции выделена в отдельный блок формы.
- Добавлены быстрые действия рядом с полем даты: `-1 день`, `Сегодня`, `Вчера`, `+1 день`.

## Motion Pattern
- Все появляющиеся UI-блоки (modal, side-panel, popover, dropdown/actions) используют единый motion-language:
  - короткий `fade/slide` вход;
  - без "прыжков" layout при смене состояний.
- Обязателен fallback для `prefers-reduced-motion: reduce` (анимации и transition отключаются).

## Interaction States
Для всех кнопок обязательны состояния:
- `default`
- `hover`
- `active`
- `disabled`
- `loading`

## Component Patterns
- `Modal/Form Pattern`: заголовок, контент, действия, закрытие по backdrop/esc.
- `Summary Pattern`: KPI-карточки + табличный breakdown.
- `Table Pattern`: фиксированный заголовок, понятные колонки, состояние пустых данных.
- `Filter Pattern`: переключатели периода и дат с мгновенным пересчетом.
- `Search/Filter/Sort Pattern` (reusable):
  - строка поиска
  - фильтр по минимальному порогу
  - сортировка по ключевым полям
  - highlight совпадений
  - одинаковый UX в текущих и будущих окнах.

## Design Tokens (Base)
- Colors:
  - `--bg`: основной фон
  - `--panel`: фон карточек
  - `--line`: цвет границ
  - `--text`, `--muted`
  - `--accent` (основной акцент)
  - `--danger` (разрушительные действия)
- Radius:
  - `--radius-lg`: карточки/модалки
  - `--radius-md`: инпуты/кнопки
- Shadow:
  - `--shadow-elevated`

## Accessibility Rules
- Контраст текста не ниже WCAG AA.
- Видимый фокус для всех интерактивных элементов.
- Кнопки и поля с размером активной зоны не менее 40px по высоте.
