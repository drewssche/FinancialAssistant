(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shell = `

    <div id="appShell" class="app-shell hidden">
      <div id="mobileNavOverlay" class="mobile-nav-overlay hidden"></div>
      <aside class="sidebar" id="sidebarNav">
        <div class="sidebar-head">
          <div class="brand">FA</div>
          <button id="mobileNavCloseBtn" class="mobile-nav-close" type="button" aria-label="Закрыть меню">×</button>
        </div>
        <div class="sidebar-today">
          <div id="todayWeekday" class="today-weekday">Сегодня</div>
          <div id="todayDate" class="today-date">--</div>
        </div>

        <nav class="nav" id="mainNav">
          <div class="nav-group-title">Обзор</div>
          <button class="nav-btn active" data-section="dashboard">Дашборд</button>
          <button class="nav-btn" data-section="analytics">Аналитика</button>
          <div class="nav-group-title">Учет</div>
          <button class="nav-btn" data-section="operations">Операции</button>
          <button class="nav-btn" data-section="debts">Долги</button>
          <button class="nav-btn" data-section="categories">Категории</button>
          <button class="nav-btn" data-section="item_catalog">Каталог позиций</button>
          <div class="nav-group-title">Система</div>
          <button id="adminNavBtn" class="nav-btn hidden" data-section="admin">Админ</button>
          <button class="nav-btn" data-section="settings">Настройки</button>
        </nav>

        <div class="user-area">
          <div class="user-block user-block-static">
            <div class="avatar" id="userAvatar">П</div>
            <div class="meta">
              <div id="userName">Пользователь</div>
              <div id="userHandle">Telegram</div>
            </div>
            <button id="sidebarLogoutBtn" class="user-logout-icon-btn" type="button" title="Выйти" aria-label="Выйти">⎋</button>
          </div>
        </div>
      </aside>

      <main class="main">
        <header class="topbar">
          <div class="topbar-title-block">
            <button id="mobileNavToggleBtn" class="mobile-nav-toggle" type="button" aria-label="Открыть меню" aria-expanded="false">☰</button>
            <button id="sectionBackBtn" class="section-back-btn hidden" type="button" aria-label="Назад" title="Назад">
              <span class="section-back-btn-icon" aria-hidden="true">←</span>
              <span id="sectionBackLabel" class="section-back-btn-label">Назад</span>
            </button>
            <div>
            <h2 id="sectionTitle">Дашборд</h2>
            <p class="subtitle" id="sectionSubtitle">Доходы, расходы и быстрый контроль баланса</p>
            </div>
          </div>
          <div class="top-actions">
            <div class="cta-row">
              <button id="addOperationCta" class="btn btn-cta" type="button">+ Добавить операцию</button>
              <button id="batchOperationCta" class="btn btn-secondary" type="button">+ Массовое добавление</button>
              <button id="addDebtCta" class="btn btn-cta hidden" type="button">+ Новый долг</button>
              <button id="addCategoryCta" class="btn btn-cta hidden" type="button">+ Создать категорию</button>
              <button id="addGroupCta" class="btn btn-secondary hidden" type="button">+ Создать группу</button>
              <button id="batchCategoryCta" class="btn btn-secondary hidden" type="button">+ Массовое добавление</button>
              <button id="addItemTemplateCta" class="btn btn-cta hidden" type="button">+ Создать позицию</button>
              <button id="addItemSourceCta" class="btn btn-secondary hidden" type="button">+ Создать источник</button>
              <button id="batchItemCatalogCta" class="btn btn-secondary hidden" type="button">+ Массовое добавление</button>
            </div>
          </div>
        </header>

        <section id="dashboardSection" class="section-block">
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
                    <strong id="dashboardCategoryBreakdownChartValue">0</strong>
                    <span id="dashboardCategoryBreakdownChartMeta" class="muted-small">Нет данных</span>
                  </div>
                </div>
              </div>
              <div id="dashboardCategoryBreakdownList" class="analytics-insight-list"></div>
            </div>
          </section>

          <section id="dashboardDebtKpiGrid" class="kpi-grid">
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
          </section>

          <section id="dashboardDebtsPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Активные долги</h3>
                <p class="subtitle">Краткий список по контрагентам</p>
              </div>
              <button id="openDebtsTabBtn" class="btn btn-secondary" type="button">Открыть раздел Долги</button>
            </div>
            <div id="dashboardDebtsList" class="debt-cards debt-cards-compact"></div>
          </section>

          <section id="dashboardOperationsPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Операции за период</h3>
                <p id="dashboardPeriodLabel" class="subtitle"></p>
              </div>
              <div class="panel-controls">
                <div class="segmented" data-period-tabs role="tablist" aria-label="Период списка операций на дашборде">
                  <button class="segmented-btn active" data-period="day" type="button">Сегодня</button>
                  <button class="segmented-btn" data-period="week" type="button">Эта неделя</button>
                  <button class="segmented-btn" data-period="month" type="button">Этот месяц</button>
                  <button class="segmented-btn" data-period="year" type="button">Этот год</button>
                  <button class="segmented-btn" data-period="all_time" type="button">Все время</button>
                  <button class="segmented-btn" data-period="custom" type="button">Настроить</button>
                </div>
                <button id="openOperationsTabBtn" class="btn btn-secondary" type="button">Открыть раздел Операции</button>
              </div>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table dashboard-operations-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Тип</th>
                    <th>Категория</th>
                    <th>Сумма</th>
                    <th>Комментарий</th>
                  </tr>
                </thead>
                <tbody id="dashboardOperationsBody"></tbody>
              </table>
            </div>
          </section>
        </section>

        <section id="analyticsSection" class="section-block hidden">
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

          <section class="panel">
            <div class="segmented" id="analyticsViewTabs" role="tablist" aria-label="Вкладки аналитики">
              <button class="segmented-btn" data-analytics-tab="calendar" type="button">Календарь</button>
              <button class="segmented-btn active" data-analytics-tab="structure" type="button">Структура</button>
              <button class="segmented-btn" data-analytics-tab="trends" type="button">Тренды</button>
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
                      <th>Результат</th>
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
              <svg id="analyticsTrendChart" class="analytics-trend-chart" viewBox="0 0 980 280" preserveAspectRatio="none" aria-label="Тренд доходов расходов баланса"></svg>
            </div>
            <div class="analytics-trend-legend">
              <span><i class="legend-dot legend-income"></i>Доход</span>
              <span><i class="legend-dot legend-expense"></i>Расход</span>
              <span><i class="legend-dot legend-balance"></i>Баланс</span>
            </div>
            <div class="analytics-trend-kpis analytics-kpi-grid">
              <article class="analytics-kpi-card analytics-kpi-income">
                <div class="muted-small">Доход</div>
                <strong id="analyticsIncomeDelta">0%</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-expense">
                <div class="muted-small">Расход</div>
                <strong id="analyticsExpenseDelta">0%</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-balance">
                <div class="muted-small">Баланс</div>
                <strong id="analyticsBalanceDelta">0%</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Операции</div>
                <strong id="analyticsOpsDelta">0%</strong>
              </article>
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
                  <span id="operationsQuickViewChip" class="analytics-kpi-chip analytics-kpi-chip-neutral hidden"></span>
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
                  <button class="segmented-btn active" data-kind="" type="button">Все</button>
                  <button class="segmented-btn" data-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-kind="income" type="button">Доход</button>
                </div>
                <div class="segmented" id="operationsSortTabs" role="tablist" aria-label="Сортировка операций">
                  <button class="segmented-btn active" data-op-sort="date" type="button">По дате</button>
                  <button class="segmented-btn" data-op-sort="amount" type="button">По сумме</button>
                  <button class="segmented-btn" data-op-sort="risk" type="button">Риск</button>
                </div>
              </div>
            </div>
            <div class="table-search-row operations-quickviews-row">
              <div class="analytics-switch-group operations-quickviews-group">
                <span class="muted-small">Быстрые срезы</span>
                <div class="segmented" id="operationsQuickViewTabs" role="tablist" aria-label="Быстрые срезы операций">
                  <button class="segmented-btn active" data-operations-quick-view="all" type="button">Все</button>
                  <button class="segmented-btn" data-operations-quick-view="receipt" type="button">С чеком</button>
                  <button class="segmented-btn" data-operations-quick-view="large" type="button">Крупные</button>
                  <button class="segmented-btn" data-operations-quick-view="uncategorized" type="button">Без категории</button>
                </div>
              </div>
            </div>
            <div class="table-search-row operations-workflow-row">
              <div class="analytics-switch-group operations-quickviews-group">
                <span class="muted-small">Быстрые действия</span>
                <div class="toolbar operations-workflow-actions">
                  <button id="selectVisibleOperationsBtn" class="btn btn-secondary" type="button">Выделить видимое</button>
                  <button id="clearVisibleOperationsSelectionBtn" class="btn btn-secondary" type="button">Снять выделение</button>
                  <button id="quickFilterExpenseBtn" class="btn btn-secondary" type="button">Только расходы</button>
                  <button id="quickFilterIncomeBtn" class="btn btn-secondary" type="button">Только доходы</button>
                  <button id="quickCustomRangeBtn" class="btn btn-secondary" type="button">Настроить период</button>
                </div>
              </div>
            </div>
            <div id="operationsSummaryGrid" class="analytics-kpi-grid operations-summary-grid">
              <article class="analytics-kpi-card analytics-kpi-income">
                <div class="muted-small">Доход по выборке</div>
                <strong id="operationsIncomeTotal">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-expense">
                <div class="muted-small">Расход по выборке</div>
                <strong id="operationsExpenseTotal">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-balance">
                <div class="muted-small">Баланс по выборке</div>
                <strong id="operationsBalanceTotal">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Операций найдено</div>
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
              <div class="toolbar table-search-actions operations-search-actions">
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
                    <th>Тип</th>
                    <th>Категория</th>
                    <th>Сумма</th>
                    <th>Комментарий</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="operationsBody"></tbody>
              </table>
            </div>

            <div id="operationsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>

            <div class="pagination hidden" aria-hidden="true">
              <button id="prevPageBtn" class="btn btn-secondary" type="button">Назад</button>
              <span id="pageInfo">Страница 1</span>
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
              <div class="toolbar category-group-controls">
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

        <section id="debtsSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Карточки долгов</h3>
                <p class="subtitle">Активные долги по контрагентам</p>
              </div>
            </div>
            <div class="table-search-row">
              <input id="debtSearchQ" class="table-search-input" type="text" placeholder="Поиск по контрагенту/комментарию" />
              <div class="toolbar debt-toolbar">
                <div class="segmented" id="debtStatusTabs" role="tablist" aria-label="Статус долгов">
                  <button class="segmented-btn active" data-debt-status="active" type="button">Активные</button>
                  <button class="segmented-btn" data-debt-status="all" type="button">Все</button>
                  <button class="segmented-btn" data-debt-status="closed" type="button">Закрытые</button>
                </div>
                <div class="segmented" id="debtSortTabs" role="tablist" aria-label="Сортировка долгов">
                  <button class="segmented-btn active" data-debt-sort="priority" type="button">Приоритет</button>
                  <button class="segmented-btn" data-debt-sort="amount" type="button">По сумме</button>
                  <button class="segmented-btn" data-debt-sort="name" type="button">По имени</button>
                </div>
                <button id="deleteAllDebtsBtn" class="btn btn-danger" type="button">Удалить все</button>
              </div>
            </div>
            <div id="debtsCards" class="debt-cards"></div>
            <div id="debtsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>

        <section id="itemCatalogSection" class="section-block hidden">
          <section class="panel">
            <div class="table-search-row">
              <input id="itemCatalogSearchQ" class="table-search-input" type="text" placeholder="Поиск по источнику и позиции" />
              <div class="toolbar item-catalog-controls">
                <div class="segmented" id="itemCatalogSortTabs" role="tablist" aria-label="Сортировка каталога позиций">
                  <button class="segmented-btn active" data-item-sort="usage" type="button">Частота</button>
                  <button class="segmented-btn" data-item-sort="recent" type="button">Недавние</button>
                  <button class="segmented-btn" data-item-sort="name" type="button">Имя</button>
                </div>
                <button id="itemCatalogCollapseAllBtn" class="btn btn-secondary btn-xs" type="button">Свернуть все</button>
                <button id="itemCatalogExpandAllBtn" class="btn btn-secondary btn-xs" type="button">Развернуть все</button>
                <button id="deleteAllItemTemplatesBtn" class="btn btn-danger" type="button">Удалить все</button>
              </div>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table item-catalog-table">
                <thead>
                  <tr>
                    <th>Источник</th>
                    <th>Позиция</th>
                    <th>Последняя цена</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="itemCatalogBody"></tbody>
              </table>
            </div>
          </section>
        </section>

        <section id="settingsSection" class="section-block hidden">
          <section class="panel">
            <form id="settingsForm" class="settings-form">
              <section class="settings-block">
                <h3>Регион</h3>
                <label class="field">
                  <span>Таймзона</span>
                  <select id="timezoneSelect">
                    <option value="auto">Авто (из браузера)</option>
                    <option value="Europe/Moscow">Europe/Moscow</option>
                    <option value="Europe/Kaliningrad">Europe/Kaliningrad</option>
                    <option value="Europe/Samara">Europe/Samara</option>
                    <option value="Asia/Yekaterinburg">Asia/Yekaterinburg</option>
                    <option value="Asia/Omsk">Asia/Omsk</option>
                    <option value="Asia/Krasnoyarsk">Asia/Krasnoyarsk</option>
                    <option value="Asia/Irkutsk">Asia/Irkutsk</option>
                    <option value="Asia/Yakutsk">Asia/Yakutsk</option>
                    <option value="Asia/Vladivostok">Asia/Vladivostok</option>
                    <option value="Asia/Magadan">Asia/Magadan</option>
                    <option value="Asia/Kamchatka">Asia/Kamchatka</option>
                    <option value="UTC">UTC</option>
                  </select>
                </label>
              </section>
              <section class="settings-block">
                <h3>Интерфейс</h3>
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Валюта</span>
                    <select id="currencySelect">
                      <option value="BYN">BYN</option>
                      <option value="RUB">RUB (₽)</option>
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="GBP">GBP (£)</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>Позиция символа</span>
                    <select id="currencyPositionSelect">
                      <option value="suffix">Справа</option>
                      <option value="prefix">Слева</option>
                    </select>
                  </label>
                </div>
                <div id="currencyPreview" class="settings-preview">Пример: 1 234,56 руб.</div>
                <label class="settings-switch-row">
                  <input id="showDashboardAnalyticsToggle" type="checkbox" checked />
                  <span>Показывать блок аналитики на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardOperationsToggle" type="checkbox" checked />
                  <span>Показывать блок операций на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardDebtsToggle" type="checkbox" checked />
                  <span>Показывать карточки долгов на дашборде</span>
                </label>
                <label class="field">
                  <span>Строк операций на дашборде</span>
                  <select id="dashboardOperationsLimitSelect">
                    <option value="5">5</option>
                    <option value="8">8</option>
                    <option value="12">12</option>
                  </select>
                </label>
                <div class="settings-scale-row">
                  <label class="field">
                    <span>Масштаб интерфейса: <strong id="uiScaleValue">100%</strong></span>
                    <input id="uiScaleRange" type="range" min="85" max="115" step="1" value="100" />
                  </label>
                  <button id="resetUiScaleBtn" class="btn btn-secondary btn-xs" type="button">Сбросить 100%</button>
                </div>
              </section>
              <section class="settings-block">
                <h3>Аналитика</h3>
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Топ операций</span>
                    <select id="analyticsTopOperationsLimitSelect">
                      <option value="3">3</option>
                      <option value="5">5</option>
                      <option value="10">10</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>Топ позиций</span>
                    <select id="analyticsTopPositionsLimitSelect">
                      <option value="5">5</option>
                      <option value="10">10</option>
                      <option value="20">20</option>
                    </select>
                  </label>
                </div>
              </section>
              <div class="settings-actions">
                <button id="saveSettingsBtn" class="btn btn-primary" type="submit">Сохранить настройки</button>
              </div>
            </form>
            <section class="panel danger-zone">
              <h3>Danger Zone</h3>
              <p class="subtitle">Удаление аккаунта удалит все операции, долги, категории и настройки без возможности восстановления.</p>
              <div class="danger-zone-actions">
                <input id="deleteMePhrase" type="text" placeholder="Введите УДАЛИТЬ для подтверждения" />
                <button id="deleteMeBtn" class="btn btn-danger" type="button">Удалить меня</button>
              </div>
            </section>
          </section>
        </section>

        <section id="adminSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Управление доступом</h3>
                <p class="subtitle">Апрув, отклонение и удаление пользователей</p>
              </div>
            </div>
            <div class="segmented" id="adminUserStatusTabs" role="tablist" aria-label="Статус пользователей">
              <button class="segmented-btn active" data-admin-user-status="pending" type="button">Ожидают</button>
              <button class="segmented-btn" data-admin-user-status="approved" type="button">Одобрены</button>
              <button class="segmented-btn" data-admin-user-status="rejected" type="button">Отклонены</button>
              <button class="segmented-btn" data-admin-user-status="all" type="button">Все</button>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table admin-users-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Пользователь</th>
                    <th>Telegram</th>
                    <th>Статус</th>
                    <th>Создан</th>
                    <th>Последний вход</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody id="adminUsersBody"></tbody>
              </table>
            </div>
          </section>
        </section>

      </main>
    </div>
`;
})();
