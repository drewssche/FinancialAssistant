# Cashflow And Operations Rework Plan

## Context

Цель: собрать в одном месте корректное отображение денежного потока пользователя и зафиксировать сопутствующие UX/bugfix задачи.

Исходная гипотеза:
- текущий раздел `Операции` показывает только `income/expense` из таблицы `operations`
- фактический денежный поток дополнительно размазан по доменам `debts` и `currency`
- из-за этого пользователь не видит всю картину движения денег в одном месте

## Requested Work

### Main Product Task
- продумать и доработать отображение кэшфлоу
- расширить раздел `Операции`, чтобы в одном месте были видны все денежные движения
- предложить лучшее решение по учету обычных операций, долгов и валюты

### Additional Fixes And Improvements
- починить кнопку `Простить долг`
  - не работает на дашборде
  - не работает в разделе `Долги`
- упростить UX `Простить долг`
  - по кнопке сразу прощать остаток долга без отдельной модалки
  - не использовать wording, похожий на удаление сущности
- в календаре учитывать долговые операции
  - `я дал в долг` -> минус деньги
  - `я отдал долг` -> минус деньги
  - `я взял в долг` -> плюс деньги
  - `мне отдали долг` -> плюс деньги
  - события должны быть как-то помечены
- продумать, как аналогично учитывать валюту в cashflow
- продумать сценарий оплаты обычной операции с валютной карты
  - операция должна оставаться обычной расходной операцией
  - одновременно должна уменьшаться валютная позиция
  - сумма в KPI/cashflow не должна считаться дважды
  - тот же сценарий нужно предусмотреть и для режима чека
- связать это с доработкой раздела `Операции`, чтобы корректно считался денежный поток
- доделать KPI-карточку `Профицит/Дефицит` на дашборде
  - профицит -> зеленый акцент
  - дефицит -> красный акцент
- пройтись по `Операции` и другим местам, где еще осталось слово/механика `Баланс`
  - привести к единому presentation pattern из дашборда (`Профицит/Дефицит`)

## Working Notes

### Known Product Constraints
- dashboard должен оставаться overview-first
- основной рабочий drill-down должен жить в `Операции`
- нельзя смешивать cashflow и valuation/PnL без явной маркировки

### Current Investigation Threads
- debt forgiveness wiring bug
- analytics calendar semantics for debt and FX events
- unified cashflow feed contract for `Операции`
- KPI presentation consistency (`Баланс` vs `Профицит/Дефицит`)
- one-click debt forgiveness for outstanding remainder
- FX-backed expense flow for operations and receipt mode without double counting

## Proposed Direction Draft

Черновая идея до детального исследования:
- не ломать текущие `operations` как доменную сущность
- добавить unified money-flow view поверх нескольких доменов:
  - `operation`
  - `debt_issuance`
  - `debt_repayment`
  - возможно `debt_forgiveness` как non-cash event в отдельном режиме
  - `fx_trade` как cash-side movement в базовой валюте
- в календаре считать минимум два слоя:
  - обычные операции
  - денежные события из долгов
- для валюты отделять:
  - cashflow базовой валюты
  - valuation/PnL

## Recommended Product Decision

### Unified Cashflow In Operations
- не подменять существующую таблицу `operations` напрямую новой доменной моделью
- добавить в разделе `Операции` отдельный режим `Все движения денег`
- в этом режиме собирать общую ленту из:
  - `operation`
  - `debt_issuance`
  - `debt_repayment`
  - `fx_trade`
- `debt_forgiveness` не включать в cashflow по умолчанию, потому что это non-cash событие
- валюту учитывать только как движение базовой валюты по quote-side сделки
- переоценку портфеля и realized/unrealized PnL не смешивать с cashflow

### Calendar Semantics
- календарь должен показывать не только `income/expense` по обычным операциям
- денежный результат периода должен уметь учитывать:
  - долговые выдачи и возвраты
  - cashflow FX-сделок
- при этом operation analytics и valuation-аналитику нужно хранить как отдельные слои, а не смешивать без маркировки

### Debt Forgiveness UX
- кнопка `Простить долг` должна прощать именно остаток долга, а не открывать отдельную форму
- лучший UX:
  - понятный confirm `Простить остаток N`
  - без отдельной модалки с ручным вводом суммы
  - `forgiven_date` по умолчанию = сегодня
  - note опционален и не должен блокировать действие
- на backend это должно создавать обычный forgiveness event на outstanding amount, а не удалять долг
- в истории долга событие должно явно читаться как `Прощен остаток`

### FX-Backed Expense Flow
- в create operation и receipt mode нужен отдельный settlement block `Оплата с валютной карты`
- при сохранении лучше создавать два связанных события в одной транзакции:
  - обычную `operation` на сумму расхода в базовой валюте
  - linked FX settlement event, который уменьшает валютную позицию
- linked FX settlement event не должен повторно попадать в unified cashflow/KPI, иначе будет double count
- в валютном разделе такие события лучше маркировать отдельно, например `Оплата картой`, а не как обычную продажу валюты
- в режиме чека settlement block должен жить на уровне всего чека, а не отдельных строк

## Execution Log

- 2026-04-01: создан рабочий план-файл и зафиксированы новые пользовательские правки
- 2026-04-01: подтверждено, что bug `Простить долг` состоит из двух частей:
  - в `Долги` action не был проброшен в public actions facade
  - в repayment flow не был корректно доступен сценарий `простить остаток`
- 2026-04-01: выбран direction для cashflow:
  - долги входят в cashflow
  - FX входит только по движению базовой валюты
  - forgiveness остается вне cashflow по умолчанию
- 2026-04-01: выполнен первый проход правок:
  - debt forgiveness wiring исправлен
  - UI result-card presentation переведен на `Профицит/Дефицит/Ноль`
  - календарь начал использовать cashflow overlay по debt + FX поверх обычных операций
  - в календаре появились secondary chips по долгам и валюте
- 2026-04-01: выполнен следующий шаг по unified cashflow:
  - добавлен backend read-model `/api/v1/operations/money-flow`
  - добавлена summary-точка `/api/v1/operations/money-flow/summary`
  - в разделе `Операции` появился режим `Денежный поток`
  - в unified feed включены `operation + debt issuance + debt repayment + fx trade`
  - `debt_forgiveness` оставлен вне cashflow
  - dashboard-кнопка `Простить` убрана как лишний UI-риск
- 2026-04-01: выполнен follow-up по debt forgiveness UX:
  - отдельная forgiveness modal больше не нужна для основного сценария
  - `Простить долг` и `Простить остаток` теперь используют короткий confirm-flow
  - confirm-кнопки названы по смыслу, без delete-wording
- 2026-04-01: выполнен первый проход по linked FX-backed expense:
  - create operation и receipt mode получили toggle `Оплата с валютной карты`
  - backend создает linked FX trade типа `card_payment`
  - linked settlement уменьшает валютную позицию
  - linked settlement исключен из unified cashflow, календаря и dashboard FX cashflow overlays
  - в разделе `Валюта` linked settlement показывается как `Оплата картой` и не редактируется как обычная сделка
- 2026-04-01: edit-flow для linked FX-backed expense доведен до полного цикла:
  - edit modal умеет показать текущий settlement
  - settlement можно изменить или убрать без прямого редактирования trade в разделе `Валюта`
  - поведение закреплено API-тестами на create/update/remove linked settlement
- 2026-04-01: проверки:
  - `./.venv/bin/pytest -q tests/api/test_dashboard_api.py -k 'calendar and (week_rows_and_day_cells or debt_and_fx_cashflow or exposes_debt_and_fx_cashflow_overlay or year_returns_month_cells)'`
  - `./.venv/bin/pytest -q tests/api/test_frontend_bootstrap_contract.py`
  - `./.venv/bin/pytest -q tests/api/test_operations_api.py`
  - `./.venv/bin/pytest -q tests/api/test_debts_api.py`
  - `./.venv/bin/pytest -q tests/api/test_dashboard_api.py`
  - `./.venv/bin/pytest -q tests/api/test_currency_api.py tests/api/test_frontend_bootstrap_contract.py`
  - `./.venv/bin/pytest -q tests/api/test_operations_api.py tests/api/test_currency_api.py tests/api/test_dashboard_api.py`
  - `./.venv/bin/pytest -q tests/api/test_request_budgets_api.py`
  - `./.venv/bin/pytest -q tests/e2e/test_debts_flow_e2e.py -m e2e -k forgiveness_flow_closes_debt_with_forgiven_request tests/api/test_frontend_bootstrap_contract.py`
  - `node --check` для измененных JS-файлов
