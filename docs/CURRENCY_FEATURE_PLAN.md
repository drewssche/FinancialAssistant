# Currency Feature Contract

Status:
- mostly implemented
- owner: Codex
- scope: currency positions, FX trades, multi-currency records, dashboard, analytics, and Telegram currency notifications

This document is the compact current contract for the currency feature. Historical implementation plans and completed one-off TODOs should not be kept here.

## Implemented

- The currency workspace opens on `Курсы`. `Мои обмены` contains the editable exchange journal. Both tabs share `Записать обмен`.
- Shared create modal mode `Валюта` for `Покупка / Продажа`.
- Weighted-average position calculation from FX trade history.
- Realized, unrealized, and total currency result in backend summary and UI.
- Endpoint for currency performance history: `GET /api/v1/currency/performance/history`.
- Above the upcoming plans, each tracked currency shows its effective NBRB rate, the change from the previous official publication, and buy and sell quotes from the selected banks.
- Market history and personal exchange results are independently expandable and fetched on demand.
- Settings for tracked currencies, dashboard visibility, and currency digest preferences.
- Daily tracked-rate refresh and Telegram currency digest.
- Currency threshold alerts.
- Multi-currency operations, plans, and debts with base-currency conversion display.
- Debt forgiveness flow with dedicated action, API endpoint, closure reason, and UI chips.

## Согласованный план от 19 ноября 2026 года

1. Показывать курсы выбранных банков для одной валюты. «Я покупаю» использует цену продажи банка, «Я продаю» использует цену покупки банка. Указывать количество единиц, канал, дату и свежесть котировки. Обновление котировок и ручной ввод доступны отдельно.
2. Для обмена показывать дату, валюту, «Отдал» и «Получил». Две введённые суммы определяют фактический курс. Автоподстановка использует сохранённый курс на дату обмена. Более ранний курс можно применить явно.
3. Показывать обмены в одном журнале с фильтрами по валюте и дате. Применять фильтры к полному списку до подсчёта и разбивки на страницы.
4. Вынести график курсов и результат собственных обменов в раскрываемые блоки. При подсчёте результата учитывать также полностью проданную валюту. Расходы сохраняют сумму в валюте и эквивалент на дату операции. Настройки банков и дайджест Telegram остаются самостоятельными.
5. Над ближайшими планами показывать «Курсы валют». Для каждой валюты выводить курс НБРБ и таблицу выбранных банков с колонками «Я покупаю» и «Я продаю». Все цены указаны в BYN за одно и то же количество валюты, для RUB — за 100. Общую дату НБРБ указывать в заголовке, разные даты — в строках валют. Нажатие на валюту открывает подробные котировки. Скрытый в настройках блок пропускает загрузку курсов.

## Product Rules

- `BYN` remains the main base currency for totals, portfolio valuation, and result calculations.
- Currency deals use their own domain model and UI mode; do not flatten them into ordinary income/expense operations.
- FX contexts use `Покупка / Продажа`, not `Доход / Расход`.
- User-facing UI should prefer clear Russian labels over accounting jargon:
  - `Текущая оценка`
  - `Вложено`
  - `Нереализованный`
  - `Реализованный`
  - `Итог`
  - `Прибыль / убыток`
- Avoid exposing `PnL`, `realized`, or `unrealized` as primary UI wording unless space or technical context requires it.
- A tracked currency without an official publication shows «Нет курса» and still opens its bank quotes.

## Calculation Rules

- Current valuation: `current_value = quantity * current_rate`.
- Open-position book value uses weighted average cost.
- Unrealized result: `current_value - book_value` for open positions.
- Realized result: closed profit/loss from sales.
- Total result: `realized + unrealized`.
- Plans use live conversion by latest available rate; they do not freeze an exchange rate at creation time.
- Operations keep an accounting FX snapshot and may show a live secondary `≈ base currency` label where appropriate.
- Debts preserve source-currency principal/outstanding amount and show base-currency valuation as secondary information.

## Active Backlog

- Replace checkbox-only reminder UX with explicit scenario controls: `Вкл / Выкл`.
- Add a dedicated persisted enable flag for threshold alerts instead of treating filled thresholds as implicitly active.
- Keep digest/alert delivery gated by explicit user preferences.
- Expand e2e coverage for multi-currency operation, plan, and debt permutations where regressions recur.
- Optional: add richer currency widgets, such as sparkline or extended daily-change metadata.
- Optional: extend currency-scope filtering to other list views where it adds meaningful separation between base-currency cashflow and foreign-currency activity.

## Guardrails

- Do not mix currency portfolio valuation into period cashflow without explicit labeling.
- Keep dashboard currency widgets visually separate from period KPI.
- Preserve stored currencies when editing old records, even if current tracked-currency settings changed.
- Limit currency selectors to tracked currencies where current-rate autofill is expected, but never corrupt existing historical data.
- Keep currency-deal preview math tied to the same rate shown in the input field.

## Main Files

- Backend service: `app/services/currency_service.py`
- API: `app/api/v1/currency.py`
- Schemas: `app/schemas/currency.py`
- Dashboard rates endpoint: `GET /api/v1/dashboard/currency-rates`
- Currency UI: `static/js/app-features-currency.js`
- Currency analytics UI: `static/js/app-features-analytics-currency.js`
- Dashboard currency UI: `static/js/app-features-dashboard.js`
- Shared modal currency mode: `static/js/app-features-operation-modal.js`
