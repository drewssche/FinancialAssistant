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
                <button id="dashboardCurrencyActivityBtn" class="btn-icon btn btn-secondary btn-xs hidden" type="button" aria-label="Журнал валюты" title="Журнал валюты">${window.App.icons.svg("history")}</button>
                <button id="dashboardRefreshAllCurrencyRatesBtn" class="btn-icon btn btn-secondary btn-xs" type="button" aria-label="Обновить курсы" title="Обновить курсы">${window.App.icons.svg("refresh")}</button>
                <button id="dashboardSendCurrencyDigestBtn" class="btn-icon btn btn-secondary btn-xs" type="button" aria-label="Отправить дайджест" title="Отправить дайджест">${window.App.icons.svg("send")}</button>
                <button id="openCurrencyTabBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Открыть валюту" title="Открыть валюту">${window.App.icons.svg("forward")}</button>
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
                <h3>Итог периода</h3>
                <p id="dashboardAnalyticsPeriodLabel" class="subtitle">Показатели за выбранный период</p>
              </div>
              <div class="toolbar">
                <div class="period-control" data-period-control="dashboard-analytics">
                  <button class="period-step-btn" data-dashboard-analytics-period-step="-1" type="button" aria-label="Предыдущий период">‹</button>
                  <button id="dashboardAnalyticsPeriodTrigger" class="period-current-btn" type="button" aria-haspopup="dialog" aria-controls="dashboardAnalyticsPeriodPopover">
                    <span class="period-current-label">Период</span>
                    <strong id="dashboardAnalyticsPeriodControlLabel">Этот месяц</strong>
                  </button>
                  <button class="period-step-btn" data-dashboard-analytics-period-step="1" type="button" aria-label="Следующий период">›</button>
                </div>
                <div class="segmented hidden" id="dashboardAnalyticsPeriodTabs" role="tablist" aria-label="Период аналитики дашборда">
                  <button class="segmented-btn" data-dashboard-analytics-period="day" type="button">Сегодня</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn active" data-dashboard-analytics-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="year" type="button">Этот год</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="all_time" type="button">Все время</button>
                  <button class="segmented-btn" data-dashboard-analytics-period="custom" type="button">Настроить</button>
                </div>
                <div id="dashboardAnalyticsPeriodPopover" class="app-popover app-popover-floating period-control-popover hidden" role="dialog" aria-label="Быстрый выбор периода дашборда">
                  <div id="dashboardAnalyticsPeriodOptions" class="settings-picker-options"></div>
                </div>
              </div>
            </div>
            <div id="dashboardKpiPrimary" class="analytics-kpi-grid"></div>
            <div id="dashboardKpiSecondary" class="analytics-kpi-secondary"></div>
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
                <div id="dashboardPlansPeriodPopover" class="app-popover app-popover-floating period-control-popover hidden" role="dialog" aria-label="Быстрый выбор периода планов">
                  <div id="dashboardPlansPeriodOptions" class="settings-picker-options"></div>
                </div>
                <button id="openPlansTabBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Открыть планы" title="Открыть планы">${window.App.icons.svg("forward")}</button>
              </div>
            </div>
            <div id="dashboardPlansKpi" class="analytics-kpi-secondary dashboard-plans-kpi"></div>
            <div id="dashboardPlansList" class="plans-list dashboard-plans-list">
              <div class="muted-small">Планов пока нет</div>
            </div>
          </section>
<section id="dashboardDebtsPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Активные долги</h3>
                <p class="subtitle">Краткий список по контрагентам</p>
              </div>
              <button id="openDebtsTabBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Открыть долги" title="Открыть долги">${window.App.icons.svg("forward")}</button>
            </div>
            <div id="dashboardDebtKpiGrid" class="kpi-grid dashboard-debts-summary">
              <article id="dashboardDebtLendKpi" class="kpi-card dashboard-debt-kpi">
                <h3>Мне должны</h3>
                <p id="debtLendTotal">0.00</p>
              </article>
              <article id="dashboardDebtBorrowKpi" class="kpi-card dashboard-debt-kpi">
                <h3>Я должен</h3>
                <p id="debtBorrowTotal">0.00</p>
              </article>
              <article id="dashboardDebtNetKpi" class="kpi-card dashboard-debt-kpi">
                <h3>Чистая позиция по долгам</h3>
                <p id="debtNetTotal">0.00</p>
              </article>
            </div>
            <div id="dashboardDebtsList" class="debt-cards debt-cards-compact"></div>
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
                <button id="openAnalyticsTabBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Открыть аналитику" title="Открыть аналитику">${window.App.icons.svg("forward")}</button>
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
<section id="dashboardPositionsPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Чаще всего покупали</h3>
                <p id="dashboardPositionsPeriodLabel" class="subtitle">Топ по числу чеков за выбранный период</p>
              </div>
              <button id="openPositionsAnalyticsBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Покупки в каталоге" title="Покупки в каталоге">${window.App.icons.svg("forward")}</button>
            </div>
            <div id="dashboardPositionsRanking" class="analytics-position-ranking-list analytics-position-ranking-dashboard"></div>
            <div id="dashboardPositionsEmpty" class="muted-small hidden">За выбранный период покупок по позициям нет</div>
          </section>

        </section>

        <section id="analyticsSection" class="section-block hidden">
          <section class="panel">
            <div class="segmented" id="analyticsViewTabs" role="tablist" aria-label="Вкладки аналитики">
              <button class="segmented-btn" data-analytics-tab="calendar" type="button">Календарь</button>
              <button class="segmented-btn active" data-analytics-tab="structure" type="button">Структура</button>
            </div>
          </section>

          <section id="analyticsGlobalScopePanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Период аналитики</h3>
                <p id="analyticsGlobalRangeLabel" class="subtitle"></p>
              </div>
              <div class="toolbar">
                <div class="period-control" data-period-control="analytics-global">
                  <button class="period-step-btn" data-analytics-period-step="-1" type="button" aria-label="Предыдущий период">‹</button>
                  <button id="analyticsGlobalPeriodTrigger" class="period-current-btn" type="button" aria-haspopup="dialog" aria-controls="analyticsGlobalPeriodPopover">
                    <span class="period-current-label">Период</span>
                    <strong id="analyticsGlobalPeriodControlLabel">Этот месяц</strong>
                  </button>
                  <button class="period-step-btn" data-analytics-period-step="1" type="button" aria-label="Следующий период">›</button>
                </div>
                <div class="segmented hidden" id="analyticsGlobalPeriodTabs" role="tablist" aria-label="Глобальный период аналитики">
                  <button class="segmented-btn" data-analytics-global-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn active" data-analytics-global-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-analytics-global-period="year" type="button">Этот год</button>
                  <button class="segmented-btn" data-analytics-global-period="all_time" type="button">Все время</button>
                  <button class="segmented-btn" data-analytics-global-period="custom" type="button">Настроить</button>
                </div>
                <div id="analyticsGlobalPeriodPopover" class="app-popover app-popover-floating period-control-popover hidden" role="dialog" aria-label="Быстрый выбор периода аналитики">
                  <div id="analyticsGlobalPeriodOptions" class="settings-picker-options"></div>
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
                <button id="analyticsBreakdownShowAllBtn" class="btn btn-secondary btn-icon" type="button" aria-label="Показать все категории" title="Показать все категории">${window.App.icons.svg("eye")}</button>
                <div class="segmented" id="analyticsBreakdownLevelTabs" role="tablist" aria-label="Уровень структуры">
                  <button class="segmented-btn active" data-analytics-breakdown-level="category" type="button">Категории</button>
                  <button class="segmented-btn" data-analytics-breakdown-level="group" type="button">Группы</button>
                  <button class="segmented-btn" data-analytics-breakdown-level="brand" type="button">Бренды</button>
                </div>
                <div class="segmented" id="analyticsCategoryKindTabs" role="tablist" aria-label="Тип категорий">
                  <button class="segmented-btn active" data-analytics-category-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-analytics-category-kind="income" type="button">Доход</button>
                  <button class="segmented-btn" data-analytics-category-kind="all" type="button">Все</button>
                </div>
              </div>
            </div>
            <div id="analyticsBrandCoverage" class="analytics-brand-coverage hidden" aria-label="Покрытие расходов брендами"></div>
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
                    <button id="analyticsPrevGridBtn" class="btn btn-secondary" type="button">←</button>
                    <button id="analyticsGridMonthTrigger" class="btn btn-secondary analytics-grid-picker-trigger" type="button" aria-haspopup="dialog">Месяц</button>
                    <div id="analyticsGridMonthPopover" class="app-popover app-popover-floating period-control-popover analytics-grid-picker-popover hidden" role="dialog" aria-label="Выбор месяца сетки">
                      <div id="analyticsGridMonthOptions" class="settings-picker-options"></div>
                    </div>
                    <button id="analyticsGridYearTrigger" class="btn btn-secondary analytics-grid-picker-trigger hidden" type="button" aria-haspopup="dialog">Год</button>
                    <button id="analyticsNextGridBtn" class="btn btn-secondary" type="button">→</button><button id="analyticsTodayGridBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Текущий период" title="Текущий период">${window.App.icons.svg("calendar")}</button>
                    <div id="analyticsGridYearPopover" class="app-popover app-popover-floating period-control-popover analytics-grid-picker-popover hidden" role="dialog" aria-label="Выбор года сетки">
                      <div id="analyticsGridYearOptions" class="settings-picker-options"></div>
                    </div>
                    <div id="analyticsGridMonthPickerWrap" class="date-input-wrap compact-input hidden">
                      <input id="analyticsGridMonthPicker" class="input compact-input" type="month" aria-label="Выбор месяца сетки" />
                    </div>
                    <input id="analyticsGridYearPicker" class="input compact-input hidden" type="number" min="1970" max="2100" step="1" placeholder="Год" />
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
                      <th>Итог приток</th>
                      <th>Итог отток</th>
                      <th>События</th>
                      <th>Профицит / Дефицит</th>
                      <th>Денежный поток</th>
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
                <h3>Доходы и расходы</h3>
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
              <svg id="analyticsTrendChart" class="analytics-trend-chart" viewBox="0 0 980 280" preserveAspectRatio="none" aria-label="Тренд доходов, расходов и денежного потока"></svg>
            </div>
            <div class="analytics-trend-legend">
              <span><i class="legend-dot legend-income"></i>Доход</span>
              <span><i class="legend-dot legend-expense"></i>Расход</span>
              <span><i class="legend-dot legend-balance"></i>Денежный поток</span>
            </div>
            <div class="analytics-trend-kpis analytics-kpi-grid">
              <article class="analytics-kpi-card analytics-kpi-income">
                <div class="muted-small">Доход</div>
                <strong id="analyticsIncomeDelta">0&nbsp;\uE901</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
              <article class="analytics-kpi-card analytics-kpi-expense">
                <div class="muted-small">Расход</div>
                <strong id="analyticsExpenseDelta">0&nbsp;\uE901</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
              <article id="analyticsOperatingResultCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="analyticsOperatingResultLabel" class="muted-small">Операционный результат</div>
                <strong id="analyticsOperatingResultValue">0&nbsp;\uE901</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
              <article id="analyticsResultCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="analyticsResultLabel" class="muted-small">Денежный поток</div>
                <strong id="analyticsBalanceDelta">0&nbsp;\uE901</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Операции</div>
                <strong id="analyticsOpsDelta">0</strong>
                <span class="analytics-kpi-delta">За выбранный период</span>
              </article>
            </div>
          </section>


        </section>

        <section id="operationsSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <p id="operationsPeriodLabel" class="sr-only"></p>
                <div id="operationsActiveFilters" class="analytics-kpi-secondary hidden">
                  <button id="operationsKindFilterChip" class="operations-filter-chip hidden" data-clear-operations-filter="kind" type="button"></button>
                  <button id="operationsSourceFilterChip" class="operations-filter-chip hidden" data-clear-operations-filter="source" type="button"></button>
                  <button id="operationsQuickViewChip" class="operations-filter-chip hidden" data-clear-operations-filter="quick_view" type="button"></button>
                  <button id="operationsCurrencyScopeChip" class="operations-filter-chip hidden" data-clear-operations-filter="currency" type="button"></button>
                  <button id="operationsCategoryFilterChip" class="operations-filter-chip hidden" data-clear-operations-filter="category" type="button"></button>
                  <button id="operationsItemTemplateFilterChip" class="operations-filter-chip hidden" data-clear-operations-filter="position" type="button"></button>
                  <button id="operationsBrandFilterChip" class="operations-filter-chip hidden" data-clear-operations-filter="brand" type="button"></button>
                  <button id="clearOperationsCategoryFilterBtn" class="operations-filter-reset hidden" type="button" title="Сбросить все фильтры" aria-label="Сбросить все фильтры">×</button>
                </div>
              </div>
            </div>
            <div class="operations-controls-grid control-section-grid">
              <section class="control-section operations-period-section" aria-label="Период операций">
                <div class="period-control" data-period-control="operations">
                  <button class="period-step-btn" data-operations-period-step="-1" type="button" aria-label="Предыдущий период">‹</button>
                  <button id="operationsPeriodTrigger" class="period-current-btn" type="button" aria-haspopup="dialog" aria-controls="operationsPeriodPopover">
                    <strong id="operationsPeriodControlLabel">Сегодня</strong>
                  </button>
                  <button class="period-step-btn" data-operations-period-step="1" type="button" aria-label="Следующий период">›</button>
                </div>
                <div class="segmented hidden" data-period-tabs role="tablist" aria-label="Период операций">
                  <button class="segmented-btn active" data-period="day" type="button">Сегодня</button>
                  <button class="segmented-btn" data-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn" data-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-period="year" type="button">Этот год</button>
                  <button class="segmented-btn" data-period="all_time" type="button">Все время</button>
                  <button class="segmented-btn" data-period="custom" type="button">Настроить</button>
                </div>
                <div id="operationsPeriodPopover" class="app-popover app-popover-floating period-control-popover hidden" role="dialog" aria-label="Быстрый выбор периода операций">
                  <div id="operationsPeriodOptions" class="settings-picker-options"></div>
                </div>
              </section>
              <section class="control-section operations-filter-section" aria-label="Фильтры операций">
                <div class="control-section-body operations-filter-grid">
                  <div class="operations-control-card">
                    <div class="operations-control-head">
                      <span class="muted-small">Тип</span>
                    </div>
                    <div class="segmented" id="kindFilters" role="tablist" aria-label="Фильтр по типу">
                      <button class="segmented-btn active" data-kind="" type="button" id="operationsKindAllLabel">Все</button>
                      <button class="segmented-btn" data-kind="expense" type="button" id="operationsKindExpenseLabel">Расход</button>
                      <button class="segmented-btn" data-kind="income" type="button" id="operationsKindIncomeLabel">Доход</button>
                    </div>
                  </div>
                  <div id="operationsSourceCard" class="operations-control-card">
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
                </div>
              </section>
              <section class="control-section operations-sort-section" aria-label="Сортировка операций">
                <div class="operations-control-card operations-control-card-sort">
                  <div class="segmented" id="operationsSortTabs" role="tablist" aria-label="Сортировка операций">
                    <button class="segmented-btn active" data-op-sort="date" type="button">По дате</button>
                    <button class="segmented-btn" data-op-sort="amount" type="button">По сумме</button>
                  </div>
                </div>
                <button id="resetOperationsFiltersBtn" class="btn btn-secondary btn-icon" type="button" aria-label="Сбросить фильтры" title="Сбросить фильтры">${window.App.icons.svg("refresh")}</button>
              </section>
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
                <div id="operationsResultLabel" class="muted-small">Операционный результат по выборке</div>
                <strong id="operationsBalanceTotal">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div id="operationsTotalCountLabel" class="muted-small">Операций найдено</div>
                <strong id="operationsTotalCount">0</strong>
              </article>
            </div>
            <div class="table-search-row sticky-search operations-search-row">
              <input id="filterQ" class="table-search-input" type="text" placeholder="Поиск" />
            </div>

            <div class="table-wrap">
              <table class="table table-hover mobile-card-table operations-table">
                <thead>
                  <tr>
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
            </div>
            <div id="categoriesKpiGrid" class="analytics-kpi-grid section-kpi-grid" aria-label="Итоги категорий"></div>

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
            <div class="directory-list-footer"><button id="deleteAllCategoriesBtn" class="btn btn-danger" type="button">Удалить все</button></div>
          </section>
        </section>
`;
})();
