(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shellSectionsPrimary = `

        <section id="dashboardSection" class="section-block">
          <section id="dashboardCurrencyPanel" class="panel dashboard-currency-panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Валютный портфель</h3>
                <p class="subtitle">Позиции и курсы по отслеживаемым валютам</p>
              </div>
              <div class="toolbar">
                <button id="dashboardRefreshAllCurrencyRatesBtn" class="btn btn-secondary btn-xs" type="button">Обновить курсы</button>
                <button id="openCurrencyTabBtn" class="btn btn-secondary" type="button">Открыть раздел Валюта</button>
              </div>
            </div>
            <div id="dashboardCurrencyKpiGrid" class="analytics-kpi-grid"></div>
            <div id="dashboardCurrencyBalances" class="currency-balance-grid"></div>
            <div id="dashboardCurrencyRates" class="dashboard-currency-rates-grid"></div>
            <div id="dashboardCurrencyPositions" class="analytics-kpi-secondary"></div>
          </section>

          <section id="dashboardAnalyticsPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>КПИ периода</h3>
                <p id="dashboardAnalyticsPeriodLabel" class="subtitle">Показатели за выбранный период</p>
              </div>
              <div class="toolbar">
                <div class="segmented" id="dashboardAnalyticsPeriodTabs" role="tablist" aria-label="Период аналитики дашборда">
                  <button class="segmented-btn" data-dashboard-analytics-period="day" type="button">Сегодня</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn active" data-dashboard-analytics-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="year" type="button">Этот год</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="all_time" type="button">Все время</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="custom" type="button">Настроить</button>
                </div>
              </div>
            </div>
            <div id="dashboardKpiPrimary" class="analytics-kpi-grid"></div>
            <div id="dashboardKpiSecondary" class="analytics-kpi-secondary"></div>
          </section>

          <section id="dashboardStructurePanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Структура периода</h3>
                <p id="dashboardStructurePeriodLabel" class="subtitle">Распределение расходов в выбранном периоде</p>
              </div>
              <div class="toolbar">
                <div class="segmented" id="dashboardBreakdownLevelTabs" role="tablist" aria-label="Уровень структуры дашборда">
                  <button class="segmented-btn active" data-dashboard-breakdown-level="category" type="button">Категории</button>
                  <button class="segmented-btn" data-dashboard-breakdown-level="group" type="button">Группы</button>
                </div>
                <div class="segmented" id="dashboardCategoryKindTabs" role="tablist" aria-label="Тип структуры дашборда">
                  <button class="segmented-btn active" data-dashboard-category-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-dashboard-category-kind="income" type="button">Доход</button>
                  <button class="segmented-btn" data-dashboard-category-kind="all" type="button">Все</button>
                </div>
                <button id="openAnalyticsTabBtn" class="btn btn-secondary" type="button">Открыть Аналитику</button>
              </div>
            </div>
            <div class="analytics-category-breakdown-grid dashboard-structure-grid">
              <div class="analytics-category-breakdown-chart-card">
                <div id="dashboardCategoryBreakdownChart" class="analytics-category-donut dashboard-category-donut">
                  <svg id="dashboardCategoryBreakdownSvg" class="analytics-category-donut-svg" viewBox="0 0 260 260"></svg>
                  <div class="analytics-category-donut-hole">
                    <span id="dashboardCategoryBreakdownChartTitle" class="analytics-category-donut-title muted-small">Итог периода</span>
                    <span id="dashboardCategoryBreakdownChartPeriod" class="analytics-category-donut-period muted-small">Нет периода</span>
                    <strong id="dashboardCategoryBreakdownChartValue">0</strong>
                    <span id="dashboardCategoryBreakdownChartMeta" class="muted-small">Нет данных</span>
                  </div>
                </div>
              </div>
              <div id="dashboardCategoryBreakdownList" class="analytics-insight-list"></div>
            </div>
          </section>

          <section id="dashboardDebtsPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Активные долги</h3>
                <p class="subtitle">Краткий список по контрагентам</p>
              </div>
              <button id="openDebtsTabBtn" class="btn btn-secondary" type="button">Открыть раздел Долги</button>
            </div>
            <div id="dashboardDebtKpiGrid" class="kpi-grid dashboard-debts-summary">
              <article class="kpi-card">
                <h3>Мне должны</h3>
                <p id="debtLendTotal">0.00</p>
              </article>
              <article class="kpi-card">
                <h3>Я должен</h3>
                <p id="debtBorrowTotal">0.00</p>
              </article>
              <article class="kpi-card">
                <h3>Чистая позиция по долгам</h3>
                <p id="debtNetTotal">0.00</p>
              </article>
            </div>
            <div id="dashboardDebtsList" class="debt-cards debt-cards-compact"></div>
          </section>

          <section id="dashboardPlansPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Ближайшие планы</h3>
                <p id="dashboardPlansPeriodLabel" class="subtitle">Планы за выбранный период</p>
              </div>
              <div class="panel-controls">
                <div class="segmented" id="dashboardPlansPeriodTabs" role="tablist" aria-label="Период планов на дашборде">
                  <button class="segmented-btn" data-dashboard-plans-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn active" data-dashboard-plans-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-dashboard-plans-period="all_time" type="button">Все время</button>
                </div>
                <button id="openPlansTabBtn" class="btn btn-secondary" type="button">Открыть раздел Планы</button>
              </div>
            </div>
            <div id="dashboardPlansKpi" class="analytics-kpi-secondary dashboard-plans-kpi"></div>
            <div id="dashboardPlansList" class="plans-list dashboard-plans-list">
              <div class="muted-small">Планов пока нет</div>
            </div>
          </section>
        </section>

        <section id="analyticsSection" class="section-block hidden">
          <section class="panel">
            <div class="segmented" id="analyticsViewTabs" role="tablist" aria-label="Вкладки аналитики">
              <button class="segmented-btn" data-analytics-tab="calendar" type="button">Календарь</button>
              <button class="segmented-btn active" data-analytics-tab="structure" type="button">Структура</button>
              <button class="segmented-btn" data-analytics-tab="trends" type="button">Тренды</button>
              <button class="segmented-btn" data-analytics-tab="currency" type="button">Валюта</button>
            </div>
          </section>

          <section id="analyticsGlobalScopePanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Период аналитики</h3>
                <p id="analyticsGlobalRangeLabel" class="subtitle"></p>
              </div>
              <div class="toolbar">
                <div class="segmented" id="analyticsGlobalPeriodTabs" role="tablist" aria-label="Глобальный период аналитики">
                  <button class="segmented-btn" data-analytics-global-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn active" data-analytics-global-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-analytics-global-period="year" type="button">Этот год</button>
                  <button class="segmented-btn" data-analytics-global-period="all_time" type="button">Все время</button>
                  <button class="segmented-btn" data-analytics-global-period="custom" type="button">Настроить</button>
                </div>
              </div>
            </div>
          </section>

          <section id="analyticsStructurePanel" class="panel analytics-tab-panel">
            <div class="panel-head row between">
              <div>
                <h3>Структура по категориям</h3>
                <p id="analyticsCategoryBreakdownLabel" class="subtitle">Распределение по суммам внутри выбранного периода</p>
              </div>
              <div class="toolbar">
                <button id="analyticsBreakdownShowAllBtn" class="btn btn-secondary" type="button">Показать все</button>
                <div class="segmented" id="analyticsBreakdownLevelTabs" role="tablist" aria-label="Уровень структуры">
                  <button class="segmented-btn active" data-analytics-breakdown-level="category" type="button">Категории</button>
                  <button class="segmented-btn" data-analytics-breakdown-level="group" type="button">Группы</button>
                </div>
                <div class="segmented" id="analyticsCategoryKindTabs" role="tablist" aria-label="Тип категорий">
                  <button class="segmented-btn active" data-analytics-category-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-analytics-category-kind="income" type="button">Доход</button>
                  <button class="segmented-btn" data-analytics-category-kind="all" type="button">Все</button>
                </div>
              </div>
            </div>
            <div class="analytics-category-breakdown-grid">
              <div class="analytics-category-breakdown-chart-card">
                <div id="analyticsCategoryBreakdownChart" class="analytics-category-donut">
                  <svg id="analyticsCategoryBreakdownSvg" class="analytics-category-donut-svg" viewBox="0 0 260 260"></svg>
                  <div class="analytics-category-donut-hole">
                    <span id="analyticsCategoryBreakdownChartTitle" class="analytics-category-donut-title muted-small">Итог периода</span>
                    <span id="analyticsCategoryBreakdownChartPeriod" class="analytics-category-donut-period muted-small">Нет периода</span>
                    <strong id="analyticsCategoryBreakdownChartValue">0</strong>
                    <span id="analyticsCategoryBreakdownChartMeta" class="muted-small">Нет данных</span>
                  </div>
                </div>
              </div>
              <div id="analyticsCategoryBreakdownList" class="analytics-insight-list"></div>
            </div>
          </section>

          <section id="analyticsCalendarPanel" class="panel analytics-tab-panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Календарная сетка</h3>
                <p id="analyticsMonthLabel" class="subtitle"></p>
              </div>
              <div class="toolbar">
                <div class="analytics-switch-group">
                  <span class="muted-small">Вид сетки</span>
                  <div class="segmented" id="analyticsCalendarViewTabs" role="tablist" aria-label="Вид календарной сетки">
                    <button class="segmented-btn active" data-analytics-calendar-view="month" type="button">Месяц</button>
                    <button class="segmented-btn" data-analytics-calendar-view="year" type="button">Год</button>
                  </div>
                </div>
                <div class="analytics-switch-group">
                  <span class="muted-small">Выбор периода сетки</span>
                  <div class="toolbar">
                    <div id="analyticsGridMonthPickerWrap" class="date-input-wrap compact-input">
                      <input id="analyticsGridMonthPicker" class="input compact-input" type="month" aria-label="Выбор месяца сетки" />
                      <button class="date-input-trigger" type="button" data-date-picker-trigger="analyticsGridMonthPicker" aria-label="Открыть выбор месяца"></button>
                    </div>
                    <input id="analyticsGridYearPicker" class="input compact-input hidden" type="number" min="1970" max="2100" step="1" placeholder="Год" />
                  </div>
                </div>
                <div class="analytics-switch-group">
                  <span class="muted-small">Листать сетку</span>
                  <div class="toolbar">
                    <button id="analyticsPrevGridBtn" class="btn btn-secondary" type="button">←</button>
                    <button id="analyticsTodayGridBtn" class="btn btn-secondary" type="button">Текущий</button>
                    <button id="analyticsNextGridBtn" class="btn btn-secondary" type="button">→</button>
                  </div>
                </div>
              </div>
            </div>
            <div class="panel-head row between">
              <div>
                <h3 id="analyticsCalendarTotalsTitle">Итоги сетки</h3>
                <p id="analyticsCalendarTotalsRangeLabel" class="subtitle"></p>
              </div>
            </div>
            <div id="analyticsCalendarTotals" class="analytics-kpi-grid"></div>
            <div id="analyticsCalendarTotalsSecondary" class="analytics-kpi-secondary"></div>
            <div id="analyticsCalendarScrollWrap" class="table-wrap analytics-calendar-scroll-wrap">
              <div id="analyticsMonthGridWrap">
                <table class="table table-hover analytics-calendar-table">
                  <thead>
                    <tr>
                      <th>Пн</th>
                      <th>Вт</th>
                      <th>Ср</th>
                      <th>Чт</th>
                      <th>Пт</th>
                      <th>Сб</th>
                      <th>Вс</th>
                      <th>Итог доход</th>
                      <th>Итог расход</th>
                      <th>Операций</th>
                      <th>Профицит / Дефицит</th>
                    </tr>
                  </thead>
                  <tbody id="analyticsCalendarBody"></tbody>
                </table>
              </div>
              <div id="analyticsYearGridWrap" class="hidden">
                <div id="analyticsYearGrid" class="analytics-year-grid"></div>
              </div>
            </div>
          </section>

          <section id="analyticsTrendsPanel" class="panel analytics-tab-panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Тренды доходов и расходов</h3>
                <p id="analyticsTrendRangeLabel" class="subtitle"></p>
              </div>
              <div class="toolbar">
                <div class="analytics-switch-group">
                  <span class="muted-small">Шаг</span>
                  <div class="segmented" id="analyticsGranularityTabs" role="tablist" aria-label="Шаг графика">
                    <button class="segmented-btn active" data-analytics-granularity="day" type="button">По дням</button>
                    <button class="segmented-btn" data-analytics-granularity="week" type="button">По неделям</button>
                    <button class="segmented-btn" data-analytics-granularity="month" type="button">По месяцам</button>
                  </div>
                </div>
              </div>
            </div>
            <div class="analytics-trend-chart-wrap">
              <svg id="analyticsTrendChart" class="analytics-trend-chart" viewBox="0 0 980 280" preserveAspectRatio="none" aria-label="Тренд доходов, расходов и профицита или дефицита"></svg>
            </div>
            <div class="analytics-trend-legend">
              <span><i class="legend-dot legend-income"></i>Доход</span>
              <span><i class="legend-dot legend-expense"></i>Расход</span>
              <span><i class="legend-dot legend-balance"></i>Профицит / Дефицит</span>
            </div>
            <div class="analytics-trend-kpis analytics-kpi-grid">
              <article class="analytics-kpi-card analytics-kpi-income">
                <div class="muted-small">Доход</div>
                <strong id="analyticsIncomeDelta">0 руб.</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
              <article class="analytics-kpi-card analytics-kpi-expense">
                <div class="muted-small">Расход</div>
                <strong id="analyticsExpenseDelta">0 руб.</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
              <article id="analyticsResultCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="analyticsResultLabel" class="muted-small">Профицит / Дефицит</div>
                <strong id="analyticsBalanceDelta">0 руб.</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Операции</div>
                <strong id="analyticsOpsDelta">0</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
            </div>
          </section>

          <section id="analyticsCurrencyPanel" class="panel analytics-tab-panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Валютная аналитика</h3>
                <p id="analyticsCurrencyRangeLabel" class="subtitle">Текущая позиция, курс и сделки по выбранной валюте</p>
              </div>
              <div class="toolbar">
                <div id="analyticsCurrencyTabs" class="segmented" role="tablist" aria-label="Фильтр валютной аналитики"></div>
                <div id="analyticsCurrencyPeriodTabs" class="segmented" role="tablist" aria-label="Период валютной аналитики">
                  <button class="segmented-btn" data-analytics-currency-period="7d" type="button">7 дней</button>
                  <button class="segmented-btn active" data-analytics-currency-period="30d" type="button">30 дней</button>
                  <button class="segmented-btn" data-analytics-currency-period="90d" type="button">3 месяца</button>
                  <button class="segmented-btn" data-analytics-currency-period="365d" type="button">12 месяцев</button>
                  <button class="segmented-btn" data-analytics-currency-period="all_time" type="button">Все время</button>
                </div>
              </div>
            </div>
            <div id="analyticsCurrencyKpiGrid" class="analytics-kpi-grid">
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Текущая оценка открытых позиций</div>
                <strong id="analyticsCurrencyCurrentValue">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Вложено в открытые позиции</div>
                <strong id="analyticsCurrencyBookValue">0</strong>
              </article>
              <article id="analyticsCurrencyResultCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="analyticsCurrencyResultLabel" class="muted-small">Нереализованный результат</div>
                <strong id="analyticsCurrencyResultValue">0</strong>
              </article>
              <article id="analyticsCurrencyRealizedCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="analyticsCurrencyRealizedLabel" class="muted-small">Реализованный результат</div>
                <strong id="analyticsCurrencyRealizedValue">0</strong>
              </article>
              <article id="analyticsCurrencyCombinedCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="analyticsCurrencyCombinedLabel" class="muted-small">Итоговый результат</div>
                <strong id="analyticsCurrencyCombinedValue">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Открытых позиций</div>
                <strong id="analyticsCurrencyActiveCount">0</strong>
              </article>
            </div>
            <div id="analyticsCurrencyBalancesRow" class="currency-balance-grid"></div>
            <div id="analyticsCurrencySecondary" class="analytics-kpi-secondary"></div>
            <div class="toolbar analytics-currency-chart-toolbar">
              <button id="analyticsCurrencyBackfillBtn" class="btn btn-secondary" type="button">Подгрузить историю для графика</button>
            </div>
            <div class="analytics-trend-chart-wrap">
              <svg id="analyticsCurrencyChart" class="analytics-trend-chart" viewBox="0 0 980 280" preserveAspectRatio="none" aria-label="История курса валюты"></svg>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Действие</th>
                    <th>Валюта</th>
                    <th>Количество</th>
                    <th>Курс</th>
                    <th>Комментарий</th>
                  </tr>
                </thead>
                <tbody id="analyticsCurrencyTradesBody"></tbody>
              </table>
            </div>
          </section>
        </section>

        <section id="operationsSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <p id="operationsPeriodLabel" class="subtitle"></p>
                <div id="operationsActiveFilters" class="analytics-kpi-secondary hidden">
                  <span id="operationsKindFilterChip" class="analytics-kpi-chip analytics-kpi-chip-neutral hidden"></span>
                  <span id="operationsSourceFilterChip" class="analytics-kpi-chip analytics-kpi-chip-neutral hidden"></span>
                  <span id="operationsQuickViewChip" class="analytics-kpi-chip analytics-kpi-chip-neutral hidden"></span>
                  <span id="operationsCurrencyScopeChip" class="analytics-kpi-chip analytics-kpi-chip-neutral hidden"></span>
                  <span id="operationsCategoryFilterChip" class="analytics-kpi-chip analytics-kpi-chip-neutral hidden"></span>
                  <button id="clearOperationsCategoryFilterBtn" class="btn btn-secondary hidden" type="button">Сбросить фильтр</button>
                </div>
              </div>
              <div class="toolbar">
                <div class="segmented" data-period-tabs role="tablist" aria-label="Период операций">
                  <button class="segmented-btn active" data-period="day" type="button">Сегодня</button>
                  <button class="segmented-btn" data-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn" data-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-period="year" type="button">Этот год</button>
                  <button class="segmented-btn" data-period="all_time" type="button">Все время</button>
                  <button class="segmented-btn" data-period="custom" type="button">Настроить</button>
                </div>
                <div class="segmented" id="kindFilters" role="tablist" aria-label="Фильтр по типу">
                  <button class="segmented-btn active" data-kind="" type="button" id="operationsKindAllLabel">Все</button>
                  <button class="segmented-btn" data-kind="expense" type="button" id="operationsKindExpenseLabel">Расход</button>
                  <button class="segmented-btn" data-kind="income" type="button" id="operationsKindIncomeLabel">Доход</button>
                </div>
              </div>
            </div>
            <div class="operations-controls-grid">
              <div class="operations-primary-controls">
                <div class="operations-control-card operations-control-card-mode">
                  <div class="segmented" id="operationsModeTabs" role="tablist" aria-label="Режим операций">
                    <button class="segmented-btn active" data-operations-mode="operations" type="button">Операции</button>
                    <button class="segmented-btn" data-operations-mode="money_flow" type="button">Денежный поток</button>
                  </div>
                </div>
                <div id="operationsSourceCard" class="operations-control-card hidden">
                  <div class="operations-control-head">
                    <span class="muted-small">Источник</span>
                  </div>
                  <div class="segmented" id="operationsSourceTabs" role="tablist" aria-label="Источник денежного потока">
                    <button class="segmented-btn active" data-operations-source="all" type="button">Все</button>
                    <button class="segmented-btn" data-operations-source="operation" type="button">Операции</button>
                    <button class="segmented-btn" data-operations-source="debt" type="button">Долги</button>
                    <button class="segmented-btn" data-operations-source="fx" type="button">Валюта</button>
                  </div>
                </div>
                <div class="operations-control-card">
                  <div class="operations-control-head">
                    <span class="muted-small">Валюта</span>
                  </div>
                  <div class="segmented" id="operationsCurrencyScopeTabs" role="tablist" aria-label="Фильтр по валюте операций">
                    <button class="segmented-btn active" data-operations-currency-scope="all" type="button">Все</button>
                    <button class="segmented-btn" data-operations-currency-scope="base" type="button" data-operations-base-currency-label>BYN</button>
                    <button class="segmented-btn" data-operations-currency-scope="foreign" type="button">Другая валюта</button>
                  </div>
                </div>
                <div class="operations-control-card operations-control-card-sort">
                  <div class="segmented" id="operationsSortTabs" role="tablist" aria-label="Сортировка операций">
                    <button class="segmented-btn active" data-op-sort="date" type="button">По дате</button>
                    <button class="segmented-btn" data-op-sort="amount" type="button">По сумме</button>
                  </div>
                </div>
              </div>
              <div class="operations-secondary-controls">
                <div id="operationsQuickViewCard" class="operations-control-card">
                <div class="operations-control-head">
                  <span class="muted-small">Быстрые срезы</span>
                </div>
                <div class="segmented" id="operationsQuickViewTabs" role="tablist" aria-label="Быстрые срезы операций">
                  <button class="segmented-btn active" data-operations-quick-view="all" type="button">Все</button>
                  <button class="segmented-btn" data-operations-quick-view="receipt" type="button">С чеком</button>
                  <button class="segmented-btn" data-operations-quick-view="large" type="button">Крупные</button>
                  <button class="segmented-btn" data-operations-quick-view="uncategorized" type="button">Без категории</button>
                </div>
              </div>
              <div class="operations-control-card operations-control-card-actions">
                <div class="operations-control-head">
                  <span class="muted-small">Быстрые действия</span>
                </div>
                <div class="toolbar section-action-toolbar operations-workflow-actions">
                  <button id="selectVisibleOperationsBtn" class="btn btn-secondary btn-xs" type="button">Выделить видимое</button>
                  <button id="clearVisibleOperationsSelectionBtn" class="btn btn-secondary btn-xs" type="button">Снять выделение</button>
                  <button id="quickFilterExpenseBtn" class="btn btn-secondary btn-xs" type="button">Только расходы</button>
                  <button id="quickFilterIncomeBtn" class="btn btn-secondary btn-xs" type="button">Только доходы</button>
                  <button id="quickCustomRangeBtn" class="btn btn-secondary btn-xs" type="button">Настроить период</button>
                </div>
              </div>
              </div>
            </div>
            <div id="operationsSummaryGrid" class="analytics-kpi-grid operations-summary-grid">
              <article class="analytics-kpi-card analytics-kpi-income">
                <div id="operationsIncomeLabel" class="muted-small">Доход по выборке</div>
                <strong id="operationsIncomeTotal">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-expense">
                <div id="operationsExpenseLabel" class="muted-small">Расход по выборке</div>
                <strong id="operationsExpenseTotal">0</strong>
              </article>
              <article id="operationsResultCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="operationsResultLabel" class="muted-small">Профицит / Дефицит по выборке</div>
                <strong id="operationsBalanceTotal">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div id="operationsTotalCountLabel" class="muted-small">Операций найдено</div>
                <strong id="operationsTotalCount">0</strong>
              </article>
            </div>
            <div id="operationsBulkBar" class="bulk-bar sticky-bar">
              <span id="operationsSelectedCount">Всего: 0</span>
              <button id="bulkEditOperationsBtn" class="btn btn-secondary bulk-action hidden-action" type="button">Редактировать выбранные</button>
              <button id="bulkDeleteOperationsBtn" class="btn btn-danger bulk-action hidden-action" type="button">Удалить выбранные</button>
            </div>
            <div class="table-search-row sticky-search">
              <input id="filterQ" class="table-search-input" type="text" placeholder="Поиск" />
              <div class="toolbar section-action-toolbar search-toolbar table-search-actions operations-search-actions">
                <button id="resetOperationsFiltersBtn" class="btn btn-secondary" type="button">Сбросить фильтры</button>
                <button id="deleteAllOperationsBtn" class="btn btn-danger" type="button">Удалить все</button>
              </div>
            </div>

            <div class="table-wrap">
              <table class="table table-hover mobile-card-table operations-table">
                <thead>
                  <tr>
                    <th class="select-col"><input id="operationsSelectAll" class="table-checkbox" type="checkbox" /></th>
                    <th>Дата</th>
                    <th id="operationsTypeHeader">Тип</th>
                    <th id="operationsCategoryHeader">Категория</th>
                    <th id="operationsReceiptHeader">Чек</th>
                    <th>Сумма</th>
                    <th>Комментарий</th>
                    <th id="operationsActionsHeader"></th>
                  </tr>
                </thead>
                <tbody id="operationsBody"></tbody>
              </table>
            </div>

            <div id="operationsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>

            <div class="pagination hidden" aria-hidden="true">
              <button id="prevPageBtn" class="btn btn-secondary" type="button">Назад</button>
              <span id="pageInfo">Показано 0 из 0</span>
              <button id="nextPageBtn" class="btn btn-secondary" type="button">Вперёд</button>
            </div>
          </section>
        </section>

        <section id="categoriesSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div></div>
              <div class="toolbar">
                <div class="segmented" id="categoryKindTabs">
                  <button class="segmented-btn active" data-cat-kind="all" type="button">Все</button>
                  <button class="segmented-btn" data-cat-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-cat-kind="income" type="button">Доход</button>
                </div>
              </div>
            </div>

            <div class="table-search-row sticky-search categories-search-row">
              <input id="categorySearchQ" class="table-search-input" type="text" placeholder="Поиск" />
              <div class="toolbar section-action-toolbar search-toolbar category-group-controls">
                <button id="categoriesCollapseAllBtn" class="btn btn-secondary btn-xs" type="button">Свернуть все</button>
                <button id="categoriesExpandAllBtn" class="btn btn-secondary btn-xs" type="button">Развернуть все</button>
              </div>
              <button id="deleteAllCategoriesBtn" class="btn btn-danger" type="button">Удалить все</button>
            </div>

            <div class="table-wrap">
              <table class="table table-hover mobile-card-table categories-table">
                <thead>
                  <tr>
                    <th>Группа</th>
                    <th>Название</th>
                    <th>Тип</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="categoriesBody"></tbody>
              </table>
            </div>
            <div id="categoriesInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>
`;
})();
