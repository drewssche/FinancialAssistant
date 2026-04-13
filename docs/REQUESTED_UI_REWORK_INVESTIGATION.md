# Requested UI Rework Investigation

Status:
- investigation complete
- implementation complete
- owner: Codex

## Current Implementation Progress

Implemented:
- Redis cache profile поднят на VPS через `docker compose --profile cache up --build -d`
- separate debt reminder preferences split:
  - `debts.reminders_enabled`
  - `debts.reminder_time`
- dashboard refresh stabilization:
  - secondary panel failures больше не должны валить целиком reload дашборда
- currency pagination contract:
  - backend `GET /api/v1/currency/trades?page=1&page_size=20&currency=USD`
  - frontend `Валюта` и `Аналитика -> Валюта` переведены на `20 + 20` with infinite scroll sentinel
- currency skeleton / inline refresh rollout:
  - cold-load skeletons added for standalone `Валюта` and `Аналитика -> Валюта`
  - repeat loads now keep visible content and use lightweight inline refresh
  - append pagination loads stay outside inline refresh overlay
- dashboard currency panel skeleton parity:
  - cold-load skeleton now matches the existing repeat-refresh inline state
- calendar period picker rework:
  - `Аналитика -> Календарь` month/year selection moved to click-triggered popovers
  - old direct month/year inputs kept only as hidden fallback wiring
  - reusable app-popover pattern is now proven for anchored period controls
- quick-period popovers shipped for:
  - dashboard analytics period
  - analytics global period
  - operations period
  - quick custom range entry points now route into the same improved flow
- period-controls cleanup for remaining lower-priority surfaces:
  - dashboard plans supports active-click popover with `текущий / предыдущий / все активные`
  - currency performance supports active-click popover with `текущее / предыдущее окно / все время`
  - analytics currency supports the same rolling-window quick chooser
- period popover layout fix:
  - all period/control popovers are mounted as floating overlays instead of expanding their parent toolbar/card
- calendar year/month presentation rework:
  - primary semantics moved to operations-only `Профицит / Дефицит`
  - unified `Денежный поток` kept as secondary context

Validated:
- `tests/services/test_preferences_service.py`
- `tests/services/test_debt_reminder_service.py`
- `tests/api/test_dashboard_api.py`
- `tests/api/test_currency_api.py`
- `tests/api/test_frontend_bootstrap_contract.py`
- `tests/e2e/test_currency_trades_pagination_e2e.py`

Closeout decisions:
- legacy `Настроить` kept in:
  - dashboard analytics
  - analytics global period
  - operations period
  - operations quick action `Настроить период`
- rationale:
  - quick-popovers now cover the common `current / previous` flows
  - visible `Настроить` remains a deliberate fallback for arbitrary custom ranges
  - removing it now would give low UX upside and reduce discoverability of manual date ranges
- no further implementation work is required for this request set unless we later choose to do a separate polish-only cleanup pass

## Scope From Request

Нужно подготовить карту изменений и зафиксировать план перед реализацией для таких задач:
- pagination `20 + 20` при скролле везде, где уместно, в первую очередь `Валюта` и `Аналитика -> Валюта`
- найти экраны без skeleton / inline refresh по образцу дашборда
- добавить отдельную настройку уведомлений по долгам
- переделать календарь в режимах `Год` и `Месяц` на presentation `Дефицит / Профицит`
- пересмотреть KPI/правую колонку месяца для консистентности
- найти все места с неудобным period-control pattern `Настроить`
- разобраться, почему периодически возникает `Не удалось обновить дашборд`

## Existing Product Contracts Already In Repo

- В [docs/PRODUCT_CONTEXT.md](/Users/bitriks24/Downloads/FinancialAssistant/docs/PRODUCT_CONTEXT.md) уже зафиксирован стандарт списков: initial `20`, далее `+20` on scroll.
- В [docs/SKELETON_LOADING_PROGRESS.md](/Users/bitriks24/Downloads/FinancialAssistant/docs/SKELETON_LOADING_PROGRESS.md) явно отмечено, что следующий приоритет по skeleton/inline refresh:
  - `Аналитика -> Валюта`
  - standalone `Валюта`
  - dashboard currency panel cold-load parity
- В [docs/ANALYTICS_STRUCTURE_AND_CALENDAR_PLAN.md](/Users/bitriks24/Downloads/FinancialAssistant/docs/ANALYTICS_STRUCTURE_AND_CALENDAR_PLAN.md) и [docs/CASHFLOW_OPERATIONS_REWORK_PLAN.md](/Users/bitriks24/Downloads/FinancialAssistant/docs/CASHFLOW_OPERATIONS_REWORK_PLAN.md) уже есть часть семантики по cashflow/calendar, но текущий UI еще не доведен до requested presentation.

## Requested Change Map

### 1. Pagination `20 + 20` For Currency Screens

Current state:
- `Валюта` грузит `/api/v1/currency/overview?trades_limit=100` и рендерит все сделки сразу.
- `Аналитика -> Валюта` делает то же самое.
- backend endpoint `/api/v1/currency/overview` принимает только `trades_limit`, без `page/page_size`.

Implementation status:
- done
- `overview` оставлен для summary/positions/rates
- список сделок вынесен в отдельный read-model `/api/v1/currency/trades`
- на фронте добавлены state slices, sentinels и `IntersectionObserver`

Frontend files:
- [static/js/app-features-currency.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-currency.js)
- [static/js/app-features-analytics-currency.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-analytics-currency.js)
- [static/js/templates/shell-sections-secondary.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/templates/shell-sections-secondary.js)
- [static/js/templates/shell-sections-primary.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/templates/shell-sections-primary.js)
- [static/js/app-core-elements.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-core-elements.js)

Backend files:
- [app/api/v1/currency.py](/Users/bitriks24/Downloads/FinancialAssistant/app/api/v1/currency.py)
- [app/services/currency_service.py](/Users/bitriks24/Downloads/FinancialAssistant/app/services/currency_service.py)
- [app/repositories/currency_repo.py](/Users/bitriks24/Downloads/FinancialAssistant/app/repositories/currency_repo.py)

Recommended direction:
- не делать через `trades_limit=20/40/60`, а ввести нормальный backend contract `page/page_size`
- сохранить `overview` для summary/positions/rates, но recent trades вынести в paginated sub-read-model, например:
  - `GET /api/v1/currency/trades?page=1&page_size=20&currency=USD`
- на фронте повторить pattern из `Операции`/`Долги`:
  - cache raw items
  - `IntersectionObserver`
  - sentinel
  - append unique rows
- если хотим менять меньше API, допустим и промежуточный вариант:
  - оставить `/overview`
  - добавить `trade_page/trade_page_size`
  - но это хуже по ясности и тестируемости

Priority candidates beyond currency:
- проверить все крупные списки на соответствие продуктному стандарту
- уже ок по pattern:
  - `Операции`
  - `Долги`
- отдельно проверить:
  - currency trades
  - analytics currency trades
  - возможно positions/item-catalog subsets, если объем реально большой

### 2. Missing Skeleton / Inline Refresh Rollout

Already implemented:
- dashboard
- debts
- plans
- analytics structure/calendar/trends
- operations
- standalone `Валюта`
- `Аналитика -> Валюта`
- dashboard currency panel

Still missing or incomplete:
- `Настройки` reminders/currency block only if latency is noticeable

Primary files:
- [static/js/app-loading-skeletons.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-loading-skeletons.js)
- [static/js/app-features-currency.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-currency.js)
- [static/js/app-features-analytics-currency.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-analytics-currency.js)
- [docs/SKELETON_LOADING_PROGRESS.md](/Users/bitriks24/Downloads/FinancialAssistant/docs/SKELETON_LOADING_PROGRESS.md)

Recommended direction:
- сперва закрыть currency screens, потому что они уже отмечены в docs как next phase
- если одновременно вводим infinite scroll, не показывать inline refresh overlay для append-loads
- в `Settings` не навязывать skeleton, если форма открывается быстро и без пустого data-backed блока

### 3. Separate Debt Reminder Toggle In Settings

Current state:
- в UI есть только:
  - reminders for plans
  - currency digest
  - currency thresholds
- отдельного toggle для debt reminders нет
- debt reminder service сейчас читает не собственные prefs, а `plans.reminders_enabled` и `plans.reminder_time`

Impacted files:
- [static/js/templates/shell-sections-secondary.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/templates/shell-sections-secondary.js)
- [static/js/app-core-elements.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-core-elements.js)
- [static/js/app-features-session-preferences.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-session-preferences.js)
- [app/repositories/preference_repo.py](/Users/bitriks24/Downloads/FinancialAssistant/app/repositories/preference_repo.py)
- [app/services/preferences_service.py](/Users/bitriks24/Downloads/FinancialAssistant/app/services/preferences_service.py)
- [app/services/debt_reminder_service.py](/Users/bitriks24/Downloads/FinancialAssistant/app/services/debt_reminder_service.py)
- [tests/services/test_preferences_service.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/services/test_preferences_service.py)
- [tests/services/test_debt_reminder_service.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/services/test_debt_reminder_service.py)

Recommended direction:
- не перегружать `plans.*`
- ввести отдельный preference namespace, например:
  - `debts.reminders_enabled`
  - `debts.reminder_time`
- migration-level DB schema change не нужен, так как prefs лежат в JSON
- для backward compatibility:
  - если `debts.*` нет, fallback на старые `plans.*`
  - при первом save из UI уже писать новое поле явно

Suggested UX:
- в блоке `Напоминания` сделать три независимых переключателя:
  - планы
  - долги
  - курсы валют
- time input для долгов можно сначала шарить с планами, но лучше сразу дать отдельное время
- если хотим минимальный scope, можно сделать только toggle без отдельного времени и взять fallback из plan reminder time

### 4. Calendar Year Mode: Replace `Денежный поток` With `Дефицит / Профицит`

Current state:
- year cards показывают:
  - `Приток`
  - `Отток`
  - `Денежный поток`
- расчет делается через unified cashflow helper, то есть включает operations + debt + FX cashflow

Relevant files:
- [static/js/app-features-analytics-calendar.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-analytics-calendar.js)
- [app/services/dashboard_analytics_timeline.py](/Users/bitriks24/Downloads/FinancialAssistant/app/services/dashboard_analytics_timeline.py)
- [app/schemas/dashboard.py](/Users/bitriks24/Downloads/FinancialAssistant/app/schemas/dashboard.py)
- [tests/api/test_dashboard_api.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/api/test_dashboard_api.py)

Product nuance from request:
- для этой presentation пользователь хочет считать именно по операциям, без валюты
- формулировка: "хочу видеть траты по операциям"

Important implication:
- это расходится с текущей unified cashflow semantics
- тут нужно product decision, иначе можно смешать два разных смысла:
  - unified cashflow
  - operations-only result

Recommended direction:
- для year/month cells вывести именно `Профицит` / `Дефицит` по operations-only result
- если debt/fx остаются важны, оставить их в tooltip / secondary chips, но не в primary value
- backend лучше вернуть оба слоя явно:
  - `operation_result_total`
  - `cashflow_total`
- тогда UI не будет угадывать семантику из `balance` и `cashflow_total`

### 5. Calendar Month Mode: Replace `Опер. траты` And Rework Right Column

Current state:
- month day-cell показывает:
  - date
  - `+приток`
  - `-отток`
  - `Опер. траты`
  - events count
- right weekly columns показывают:
  - total inflow
  - total outflow
  - operations/events count
  - `Операционные траты`
  - chip `Денежный поток`

Relevant file:
- [static/js/app-features-analytics-calendar.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-analytics-calendar.js)

Recommended direction:
- в day cells:
  - заменить `Опер. траты` на `Профицит` / `Дефицит`
  - цвет строить по знаку operations-only result
- в правой weekly column:
  - заменить `Операционные траты` на `Профицит` / `Дефицит`
  - понять, нужен ли отдельный столбец `Операций` или достаточно `События`
- KPI consistency:
  - если primary story для month calendar становится operations-centric, то `Операционный результат` логичнее усилить, а `Денежный поток` увести во secondary chips
  - возможно убрать один из KPI, чтобы не было двух похожих карточек с разной семантикой

Suggested semantic split:
- primary:
  - Приток
  - Отток
  - Профицит / Дефицит по операциям
  - События
- secondary:
  - Денежный поток
  - Долги в потоке
  - Валюта в потоке

### 6. Period Controls Rework

Current state:
- глобальный pattern в приложении завязан на segmented buttons + `Настроить`
- custom period открывается общей modal `Настроить период`
- для analytics calendar отдельно есть month/year pickers, но они живут рядом с prev/next/today buttons

Implementation status:
- done for the requested scope
- active-click quick-popovers now cover:
  - dashboard analytics period
  - analytics global period
  - analytics calendar month/year anchors
  - operations period
  - dashboard plans period
  - currency performance period
  - analytics currency period
- legacy visible `Настроить` intentionally remains only where arbitrary manual ranges still need a clear entry point

Where the pattern is used:
- dashboard KPI period:
  - [static/js/templates/shell-sections-primary.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/templates/shell-sections-primary.js)
- analytics global period:
  - [static/js/templates/shell-sections-primary.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/templates/shell-sections-primary.js)
- operations period:
  - [static/js/templates/shell-sections-primary.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/templates/shell-sections-primary.js)
- plans dashboard period
- currency performance period
- analytics currency period
- analytics calendar month/year anchor controls

Control logic files:
- [static/js/app-init-features.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-init-features.js)
- [static/js/app-init-features-analytics.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-init-features-analytics.js)
- [static/js/app-features-session-preferences.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-features-session-preferences.js)

Recommended direction:
- не переписывать все одинаково в один проход
- выделить 3 control families:
  - relative periods: today/week/month/year/all time/custom
  - anchored periods: month picker / year picker
  - rolling performance windows: 30d/90d/365d/all_time
- для dashboard analytics и analytics global:
  - вместо жесткого `Настроить` дать click on active month/year control with popover chooser
  - custom range оставить как secondary action внутри popover
- для calendar:
  - month label should open month picker popover
  - year label should open year picker popover
- для week mode, если оно позже появится как anchored choice:
  - выбирать неделю в контексте уже выбранного месяца

Implementation note:
- в проекте уже есть reusable popover utilities:
  - [static/js/app-picker-utils.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-picker-utils.js)
- это лучше использовать, чем писать новый modal-only flow

### 7. Dashboard Refresh Failure Investigation

Observed symptom:
- пользователь после навигации по разделам иногда снова нажимает `Дашборд`
- появляется `Не удалось обновить дашборд`

Where the error is raised:
- [static/js/app-section-ui.js](/Users/bitriks24/Downloads/FinancialAssistant/static/js/app-section-ui.js)

Current behavior:
- при входе в dashboard запускается `Promise.allSettled` для jobs:
  - critical: `dashboardFeature.loadDashboard()`
  - optional: `analyticsFeature.loadDashboardAnalyticsPreview()`
- статус `Не удалось обновить дашборд` показывается только если critical job rejected

What can reject inside `loadDashboard()`:
- summary request
- currency overview for rates
- plans dashboard loading
- debt preview loading

Why this is likely flaky:
- `loadDashboard()` сейчас агрегирует слишком много подсценариев в один critical promise
- failure любого вложенного блока валит весь dashboard reload, даже если summary/KPI загрузились бы нормально
- особенно подозрителен `await getPlansFeature().loadPlans?.()` внутри dashboard loader: это тяжелый cross-section call, не dashboard-local read model

Recommended direction:
- разделить dashboard reload на independent jobs:
  - summary + currency panel
  - plans panel
  - debts panel
- critical should be only summary/KPI core
- debts/plans/currency-rates лучше пометить optional или panel-scoped with own error/status
- добавить explicit logging around rejected dashboard jobs on frontend
- если есть abort/race при повторной навигации, в dashboard loader ввести request sequencing как уже сделано в debts/operations

First implementation target:
- не менять UX сразу глубоко
- сперва декомпозировать `loadDashboard()` so one panel failure does not bubble as fatal dashboard failure

## Existing Test Safety Net

Already present:
- [tests/api/test_dashboard_api.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/api/test_dashboard_api.py)
- [tests/api/test_currency_api.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/api/test_currency_api.py)
- [tests/api/test_frontend_bootstrap_contract.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/api/test_frontend_bootstrap_contract.py)
- [tests/e2e/test_analytics_mobile_e2e.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/e2e/test_analytics_mobile_e2e.py)
- [tests/e2e/test_currency_trade_modal_e2e.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/e2e/test_currency_trade_modal_e2e.py)
- [tests/e2e/test_currency_trade_modal_live_calc_e2e.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/e2e/test_currency_trade_modal_live_calc_e2e.py)
- [tests/services/test_preferences_service.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/services/test_preferences_service.py)
- [tests/services/test_debt_reminder_service.py](/Users/bitriks24/Downloads/FinancialAssistant/tests/services/test_debt_reminder_service.py)

Verified during this investigation:
- `./.venv/bin/pytest -q tests/api/test_dashboard_api.py`
- `./.venv/bin/pytest -q tests/api/test_currency_api.py`
- `./.venv/bin/pytest -q tests/api/test_frontend_bootstrap_contract.py`

Result:
- all passed in current state

## Operational Note: Redis Advisory On Small VPS

User context:
- приложение фактически single-user
- runtime на VPS
- Telegram admin advisory периодически советует включить Redis

Relevant files:
- [app/services/redis_runtime_advisory_service.py](/Users/bitriks24/Downloads/FinancialAssistant/app/services/redis_runtime_advisory_service.py)
- [app/services/dashboard_service.py](/Users/bitriks24/Downloads/FinancialAssistant/app/services/dashboard_service.py)
- [app/core/cache.py](/Users/bitriks24/Downloads/FinancialAssistant/app/core/cache.py)
- [app/core/metrics.py](/Users/bitriks24/Downloads/FinancialAssistant/app/core/metrics.py)
- [docker-compose.yml](/Users/bitriks24/Downloads/FinancialAssistant/docker-compose.yml)
- [docs/ENGINEERING_PRINCIPLES.md](/Users/bitriks24/Downloads/FinancialAssistant/docs/ENGINEERING_PRINCIPLES.md)

Important implementation detail:
- advisory сейчас отправляется не по любому превышению counters
- `local fallback reads/writes` задуманы как supporting signal only
- реальный триггер для advisory:
  - `local_cache_entries >= 25`
  - или `dashboard_summary p95 > 250ms` при `samples >= 5`

Implication for the reported message:
- если advisory пришел при `entries = 8`, то решающий breach у тебя не counters `55/29`, а `dashboard summary p95 = 3486.8 ms`
- то есть это уже не ложный positive из-за single-user lifetime counters
- система фактически говорит: hot path `dashboard summary` слишком дорогой даже для одного пользователя

Current Redis footprint in compose:
- optional profile `cache`
- redis maxmemory `32mb`
- container mem_limit `64m`
- cpu limit `0.10`

Recommendation for single-user VPS:
- Redis не обязателен как постоянная доктрина “на одного юзера”
- но при текущем `p95 ~ 3.5s` включить Redis разумно как cheap mitigation:
  - маленький overhead
  - low-risk rollout
  - immediate benefit for repeated dashboard aggregate reads
- при этом Redis не лечит root cause полностью
- root cause still needs work in:
  - dashboard summary aggregation cost
  - frontend dashboard reload fan-out
  - repeated dashboard invalidations / over-refresh

Pragmatic sequence:
1. На VPS включить Redis profile.
2. После включения замерить `GET /api/v1/dashboard/summary/metrics` повторно.
3. Если p95 остается высоким, переходить к hot-path fixes:
   - dashboard refresh stabilization
   - optional panel isolation
   - request fan-out reduction
4. Только если после этого advisory останется noisy despite healthy p95, обсуждать threshold tuning.

Threshold change recommendation:
- сейчас пороги менять не стоит
- для твоего конкретного кейса advisory выглядит обоснованным из-за `p95`, а не из-за мелких counter breaches
- если позже захотим уменьшить noise, безопаснее не поднимать `p95` threshold, а:
  - оставить `250ms`
  - но, например, увеличить sample floor или добавить rolling-window reset semantics for counters
- повышать `p95` threshold до “удобного” значения сейчас было бы просто маскировкой проблемы

## Test Gaps To Add During Implementation

- API:
  - currency paginated trades contract
  - debt reminder preference fallback/new fields
  - calendar API exposes operations-only result separately from unified cashflow if we adopt that contract
- frontend/e2e:
  - currency section infinite scroll appends next 20 rows
  - analytics currency infinite scroll appends next 20 rows
  - settings save/load for debt reminder toggle
  - dashboard reload survives optional panel failure
  - calendar year/month renders `Профицит/Дефицит` with correct tones
- smoke:
  - frontend bootstrap contract after new controls/sentinels/elements
  - node syntax checks for edited JS modules

## Proposed Execution Order

1. Debt reminders preferences split
- lowest UI risk
- unlocks clean settings model

2. Dashboard reload stabilization
- removes flaky blocker before broader UI refactors

3. Currency pagination foundation
- API + shared infinite scroll pattern

4. Currency skeleton rollout
- attach to new pagination-aware loading states

5. Calendar semantics + presentation rework
- after agreeing on operations-only vs unified cashflow contract

6. Period controls rework
- after inventory is complete and shared popover pattern is chosen

## Open Product Decisions Before Implementation

- `Дефицит / Профицит` в календаре считаем:
  - только по операциям
  - или по unified cashflow
- у долговых reminder settings:
  - только toggle
  - или toggle + отдельное время
- period control rework:
  - делаем сначала только dashboard/analytics
  - или сразу везде, где есть `Настроить`
