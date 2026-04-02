# Cashflow And Operations Worklog

## 2026-04-01

### Product Decisions
- unified cashflow в `Операциях` реализован как отдельный режим, а не как замена текущего CRUD-списка
- `Простить долг` оставлен в debt flow, без отдельной кнопки на dashboard
- forgiveness трактуется как non-cash event и не попадает в cashflow
- FX учитывается только по движению базовой валюты по quote-side сделки

### Implemented
- исправлен сценарий forgiveness в debt flow, с акцентом на `простить остаток`, а не весь долг целиком
- `Простить долг` переведен на one-click confirm без отдельной forgiveness modal
  - confirm-кнопки названы по смыслу, без `Удалить`
  - для списка долгов и repayment flow используется единый сценарий `простить остаток`
- календарь и dashboard analytics считают debt/FX cashflow поверх обычных операций
- KPI `Профицит/Дефицит` на dashboard и в analytics highlights переведен на unified cashflow:
  - `operations`
  - `debts`
  - `fx cash side`
- `Аналитика -> Тренды` переведена на unified cashflow:
  - линия результата
  - tooltip по бакетам
  - KPI внутри вкладки
  - dashboard analytics preview
- placeholder-лейблы `Результат/Баланс` в денежных KPI и легендах приведены к паттерну `Профицит / Дефицит`
- в валютной сделке live-calc теперь поддерживает все три пары ввода:
  - `курс + количество -> сумма`
  - `курс + сумма -> количество`
  - `количество + сумма -> курс`
- в create operation и receipt mode добавлен linked FX-backed expense flow:
  - toggle `Оплата с валютной карты`
  - создается обычная расходная `operation`
  - параллельно создается связанная FX-сделка типа `card_payment`
  - валютная позиция уменьшается, но cashflow/KPI/календарь не получают второй дубликат суммы
- edit operation теперь тоже поддерживает linked FX-backed expense:
  - связанный `card_payment` settlement можно создать, изменить или снять из edit modal
  - существующая связка сериализуется обратно в edit form без ручного перехода в раздел `Валюта`
- UI блока `Оплата с валютной карты` приведен к общему switch-паттерну:
  - вместо голого checkbox используется переключатель `Вкл / Выкл`
  - поля валютного списания собраны в компактную адаптивную строку с переносом на узких экранах
- вычисляемое поле в валютных сценариях теперь помечается как `AUTO`:
  - badge появляется у производного поля
  - активное auto-поле получает мягкий акцент рамкой
- связанные `card_payment` записи в разделе `Валюта` теперь помечаются явнее:
  - добавлен badge `Связано с операцией`
  - рядом есть компактное действие `Открыть`, которое ведет в связанную операцию
- в `Операциях` и `Денежном потоке` linked FX-backed expense теперь виден прямо в строке:
  - добавлен чип `Валютная карта`
  - если доступна валюта списания, она показывается прямо в чипе
- режим `Чек` теперь полноценно использует тот же валютный settlement:
  - сумма чека стала first-class источником для linked `card_payment`
  - валютный блок пересчитывается при изменении позиций чека и при `Подтянуть сумму из чека`
  - тексты и валидация различают `сумму операции` и `сумму чека`
- в разделе `Валюта` linked settlement показывается как `Оплата картой`
  - такие записи read-only и не редактируются как обычные валютные сделки
- presentation `Баланс` приведен к механике `Профицит/Дефицит`
- добавлены:
  - `GET /api/v1/operations/money-flow`
  - `GET /api/v1/operations/money-flow/summary`
- раздел `Операции` теперь умеет переключаться между:
  - `Операции`
  - `Денежный поток`
- в режиме `Денежный поток` добавлен source filter:
  - `Все`
  - `Операции`
  - `Долги`
  - `Валюта`
- добавлены short source-badges и цветовые акценты:
  - `OP`
  - `DEBT`
  - `FX`
  - отдельный accent для FX buy/sell
- linked FX settlements теперь исключаются из unified cashflow и по `linked_operation_id`, а не только по `trade_kind=card_payment`
  - это закрывает legacy-кейсы, где связанная валютная запись могла выглядеть как обычная FX trade
  - для `FX-backed expense` в `Денежном потоке` остается одна строка операции
- переключение периода в разделе `Операции` отвязано от обязательного refresh dashboard summary
  - при смене периода обновляется и сохраняется именно operations view
  - custom period в operations flow использует тот же scoped refresh

### Notes
- из строки unified feed:
  - debt event открывает историю конкретного долга
  - fx event открывает конкретную валютную сделку
- зафиксированы следующие новые product follow-ups:
  - при необходимости добавить стабильный браузерный e2e поверх текущего custom money-input shell
- поле `balance` сохранено в API как operations-only метрика для обратной совместимости
- `cashflow_total` добавлен как отдельная unified метрика для KPI и summary
- category filter и quick view остаются только в обычном режиме `Операции`
- dashboard summary test стабилизирован на `period=custom`, чтобы не зависеть от текущего календарного месяца
- toast `Ошибка сохранения периода` в operations раньше мог приходить из unrelated dashboard all-time summary reload, а не из самого period apply
- теперь эта связка для operations period controls убрана

### Validation
- добавлен e2e `tests/e2e/test_operations_money_flow_e2e.py`
- linked FX-backed expense закрыт API-тестами create/update/remove без double count
- подтверждено smoke/e2e:
  - `tests/api/test_frontend_bootstrap_contract.py`
  - `tests/api/test_operations_api.py`
  - `tests/api/test_dashboard_api.py`
  - `tests/api/test_currency_api.py`
  - `tests/services/test_cashflow_linked_trade_exclusion.py`
  - `tests/e2e/test_analytics_trend_cashflow_e2e.py -m e2e`
  - `tests/e2e/test_operations_money_flow_e2e.py -m e2e`
  - `tests/e2e/test_currency_trade_modal_e2e.py -m e2e`
  - `tests/e2e/test_currency_trade_modal_live_calc_e2e.py -m e2e`
  - `tests/e2e/test_debts_flow_e2e.py -m e2e -k forgiveness_flow_closes_debt_with_forgiven_request`
  - `tests/e2e/test_currency_trade_modal_e2e.py -m e2e -k keeps_preview_and_recalculates_both_fields`
