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
- в календаре учитывать долговые операции
  - `я дал в долг` -> минус деньги
  - `я отдал долг` -> минус деньги
  - `я взял в долг` -> плюс деньги
  - `мне отдали долг` -> плюс деньги
  - события должны быть как-то помечены
- продумать, как аналогично учитывать валюту в cashflow
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
- 2026-04-01: проверки:
  - `./.venv/bin/pytest -q tests/api/test_dashboard_api.py -k 'calendar and (week_rows_and_day_cells or debt_and_fx_cashflow or exposes_debt_and_fx_cashflow_overlay or year_returns_month_cells)'`
  - `./.venv/bin/pytest -q tests/api/test_frontend_bootstrap_contract.py`
  - `./.venv/bin/pytest -q tests/api/test_operations_api.py`
  - `./.venv/bin/pytest -q tests/api/test_debts_api.py`
  - `./.venv/bin/pytest -q tests/api/test_dashboard_api.py`
  - `./.venv/bin/pytest -q tests/api/test_currency_api.py tests/api/test_frontend_bootstrap_contract.py`
  - `./.venv/bin/pytest -q tests/api/test_request_budgets_api.py`
  - `node --check` для измененных JS-файлов
