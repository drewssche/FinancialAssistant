(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shellSectionsSecondary = `

        <section id="workSection" class="section-block hidden">
          <section class="panel work-hero-panel">
            <div class="panel-head row between work-section-head">
              <div>
                <h3>Табель</h3>
                <p class="subtitle">Обычные рабочие дни считаются автоматически — отмечайте только исключения</p>
              </div>
              <div class="work-month-control">
                <button id="workPrevMonthBtn" class="period-step-btn" type="button" aria-label="Предыдущий месяц">‹</button>
                <button id="workMonthTrigger" class="btn btn-secondary analytics-grid-picker-trigger" type="button" aria-haspopup="dialog">Месяц</button>
                <div id="workMonthPopover" class="app-popover app-popover-floating period-control-popover analytics-grid-picker-popover hidden" role="dialog" aria-label="Выбор месяца табеля">
                  <div id="workYearOptions" class="settings-picker-options work-period-year-options"></div>
                  <div id="workMonthOptions" class="settings-picker-options work-period-month-options"></div>
                </div>
                <button id="workNextMonthBtn" class="period-step-btn" type="button" aria-label="Следующий месяц">›</button>
                <button id="workTodayBtn" class="btn btn-secondary btn-xs" type="button">Текущий</button>
              </div>
            </div>
            <div id="workSummaryGrid" class="analytics-kpi-grid section-kpi-grid"></div>
            <div id="workPaymentsGrid" class="work-payments-grid"></div>
          </section>

          <section class="panel">
            <div class="segmented work-view-tabs" id="workViewTabs" role="tablist" aria-label="Разделы работы">
              <button class="segmented-btn active" data-work-view="statistics" type="button">Статистика</button>
              <button class="segmented-btn" data-work-view="timesheet" type="button">Табель</button>
              <button class="segmented-btn" data-work-view="settings" type="button">Настройки и планы</button>
              <button class="segmented-btn" data-work-view="contracts" type="button">История работы</button>
            </div>

            <div id="workStatisticsView">
              <div class="work-statistics-toolbar">
                <div id="workStatisticsPeriodTabs" class="segmented" role="tablist" aria-label="Период рабочей статистики">
                  <button class="segmented-btn active" data-work-stat-period="month" type="button">Месяц</button>
                  <button class="segmented-btn" data-work-stat-period="year" type="button">Год</button>
                  <button class="segmented-btn" data-work-stat-period="all_time" type="button">Всё время</button>
                  <button class="segmented-btn" data-work-stat-period="custom" type="button">Период</button>
                </div>
                <div class="work-month-control">
                  <button id="workStatisticsPrevBtn" class="period-step-btn" type="button" aria-label="Предыдущий период">‹</button>
                  <strong id="workStatisticsPeriodLabel">Текущий месяц</strong>
                  <button id="workStatisticsNextBtn" class="period-step-btn" type="button" aria-label="Следующий период">›</button>
                  <button id="workStatisticsCurrentBtn" class="btn btn-secondary btn-xs" type="button">Текущий</button>
                </div>
              </div>
              <form id="workStatisticsCustomForm" class="work-statistics-custom hidden">
                <label class="field"><span>С</span><div class="date-input-wrap"><input id="workStatisticsDateFrom" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workStatisticsDateFrom" aria-label="Открыть календарь"></button></div></label>
                <label class="field"><span>По</span><div class="date-input-wrap"><input id="workStatisticsDateTo" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workStatisticsDateTo" aria-label="Открыть календарь"></button></div></label>
                <button class="btn btn-primary" type="submit">Применить</button>
              </form>
              <div id="workStatisticsKpi" class="analytics-kpi-grid section-kpi-grid"></div>
              <article class="work-statistics-progress-card">
                <div class="row between"><span>Выполнение плана часов</span><strong id="workStatisticsProgressLabel">0%</strong></div>
                <div class="work-statistics-progress"><i id="workStatisticsProgressBar"></i></div>
              </article>
              <div class="panel-head"><div><h3>Динамика по месяцам</h3><p class="subtitle">План, факт и оплачиваемые часы</p></div></div>
              <div id="workStatisticsMonths" class="work-statistics-months"></div>
            </div>

            <div id="workTimesheetView" class="hidden">
              <div class="work-calendar-weekdays" aria-hidden="true">
                <span>Пн</span><span>Вт</span><span>Ср</span><span>Чт</span><span>Пт</span><span>Сб</span><span>Вс</span>
              </div>
              <div id="workCalendarGrid" class="work-calendar-grid"></div>
              <div class="work-calendar-legend muted-small">
                <span><i class="work-legend-dot work-legend-completed"></i> отработано</span>
                <span><i class="work-legend-dot work-legend-forecast"></i> рабочий прогноз</span>
                <span><i class="work-legend-dot work-legend-today"></i> сегодня</span>
                <span><i class="work-legend-dot work-legend-manual"></i> изменено вручную</span>
                <span><i class="work-legend-dot work-legend-payment"></i> выплата</span>
              </div>
              <form id="workDayForm" class="work-day-editor hidden">
                <div class="panel-head row between">
                  <div><h3 id="workDayEditorTitle">День</h3><p class="subtitle">Ручная настройка имеет приоритет над календарём</p></div>
                  <button id="closeWorkDayEditorBtn" class="btn btn-ghost btn-xs" type="button">Закрыть</button>
                </div>
                <input id="workDayDate" type="hidden" />
                <div class="work-day-editor-grid">
                  <label class="field"><span>Статус</span><select id="workDayStatus">
                    <option value="workday">Рабочий день</option>
                    <option value="vacation">Отпуск</option>
                    <option value="sick_paid">Сикдей с оплатой</option>
                    <option value="sick_unpaid">Больничный / сикдей без оплаты</option>
                    <option value="company_day_off">Выходной за счёт компании</option>
                    <option value="day_off">Отгул</option>
                    <option value="unpaid_leave">Без сохранения зарплаты</option>
                    <option value="transferred_workday">Перенесённый рабочий день</option>
                    <option value="overtime">Сверхурочная работа</option>
                    <option value="holiday">Праздник</option>
                    <option value="weekend">Выходной</option>
                  </select></label>
                  <label class="field"><span>Применить по дату</span><div class="date-input-wrap"><input id="workDayDateTo" type="date" /><button class="date-input-trigger" type="button" data-date-picker-trigger="workDayDateTo" aria-label="Открыть календарь"></button></div></label>
                  <label class="field"><span>План, ч</span><input id="workDayPlanned" type="number" min="0" max="24" step="0.25" /></label>
                  <label class="field"><span>Факт, ч</span><input id="workDayActual" type="number" min="0" max="24" step="0.25" /></label>
                  <label class="field"><span>Оплачивается, ч</span><input id="workDayCredited" type="number" min="0" max="24" step="0.25" /></label>
                </div>
                <label class="field"><span>Комментарий</span><input id="workDayNote" type="text" maxlength="500" placeholder="Причина или пояснение" /></label>
                <div class="settings-actions work-day-editor-actions">
                  <button class="btn btn-primary" type="submit">Сохранить исключение</button>
                  <button id="resetWorkDayBtn" class="btn btn-secondary" type="button">Вернуть по графику</button>
                </div>
              </form>
            </div>

            <form id="workSettingsForm" class="settings-form hidden">
              <section class="settings-block">
                <h3>График работы</h3>
                <div class="settings-grid-2">
                  <label class="field"><span>Компания</span><input id="workCompany" type="text" maxlength="160" placeholder="Битрикс" /></label>
                  <label class="field"><span>Должность</span><input id="workPosition" type="text" maxlength="160" /></label>
                  <label class="field"><span>Дата начала работы</span><div class="date-input-wrap"><input id="workStartDate" type="date" /><button class="date-input-trigger" type="button" data-date-picker-trigger="workStartDate" aria-label="Открыть календарь"></button></div></label>
                  <label class="field"><span>Часов в обычный день</span><input id="workStandardHours" type="number" min="0.25" max="24" step="0.25" value="8" /></label>
                </div>
                <div class="work-weekday-picker" id="workWeekdayPicker">
                  <label><input type="checkbox" value="0" checked /> Пн</label><label><input type="checkbox" value="1" checked /> Вт</label>
                  <label><input type="checkbox" value="2" checked /> Ср</label><label><input type="checkbox" value="3" checked /> Чт</label>
                  <label><input type="checkbox" value="4" checked /> Пт</label><label><input type="checkbox" value="5" /> Сб</label>
                  <label><input type="checkbox" value="6" /> Вс</label>
                </div>
              </section>
              <section class="settings-block">
                <h3>Связь с финансовыми планами</h3>
                <p class="muted-small">Номинальные даты сохраняются. Если они нерабочие, выплата переносится только назад до первого рабочего дня.</p>
                <div class="settings-grid-2">
                  <label class="field"><span>План основной части</span><select id="workSalaryPlan"><option value="">Не связан</option></select></label>
                  <label class="field"><span>Номинальный день</span><input id="workSalaryDay" type="number" min="1" max="31" value="5" /></label>
                  <label class="field"><span>План аванса</span><select id="workAdvancePlan"><option value="">Не связан</option></select></label>
                  <label class="field"><span>Номинальный день</span><input id="workAdvanceDay" type="number" min="1" max="31" value="20" /></label>
                </div>
              </section>
              <div class="settings-actions"><button class="btn btn-primary" type="submit">Сохранить настройки</button></div>
            </form>

            <div id="workContractsView" class="hidden">
              <form id="workContractForm" class="settings-form">
                <section class="settings-block">
                  <h3 id="workContractFormHeading">Новый период или смена работы</h3>
                  <p id="workContractFormSubtitle" class="muted-small">Новая текущая работа автоматически завершит предыдущий период днём раньше. История компании, должности и оклада сохранится.</p>
                  <div class="settings-grid-2">
                    <label class="field"><span>Действует с</span><div class="date-input-wrap"><input id="workContractFrom" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workContractFrom" aria-label="Открыть календарь"></button></div></label>
                    <label class="field"><span>Действует до</span><div class="date-input-wrap"><input id="workContractTo" type="date" /><button class="date-input-trigger" type="button" data-date-picker-trigger="workContractTo" aria-label="Открыть календарь"></button></div></label>
                    <label class="field"><span>Компания</span><input id="workContractCompany" type="text" maxlength="160" /></label>
                    <label class="field"><span>Должность</span><input id="workContractPosition" type="text" maxlength="160" /></label>
                    <label class="field"><span>Оклад на руки</span><input id="workContractSalary" type="number" min="0" step="0.01" /></label>
                    <label class="field"><span>Валюта</span><select id="workContractCurrency"><option value="BYN">BYN</option><option value="USD">USD</option><option value="EUR">EUR</option></select></label>
                  </div>
                  <label class="field"><span>Комментарий</span><input id="workContractNote" type="text" maxlength="500" /></label>
                  <div class="settings-actions work-contract-form-actions">
                    <button id="workContractSubmitBtn" class="btn btn-primary" type="submit">Добавить период</button>
                    <button id="cancelWorkContractEditBtn" class="btn btn-secondary hidden" type="button">Отменить редактирование</button>
                  </div>
                </section>
              </form>
              <div id="workContractsList" class="plans-list"></div>
            </div>
          </section>
        </section>

        <section id="plansSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Плановые операции</h3>
              </div>
            </div>
            <div id="plansKpiGrid" class="plans-kpi-shell">
              <article class="kpi-card plans-financial-kpi-card">
                <div class="plans-financial-kpi-head">
                  <div id="plansStatusChips" class="analytics-kpi-secondary plans-status-chips">
                    <span id="plansDueChip" class="analytics-kpi-chip analytics-kpi-chip-neutral">Активных: 0</span>
                    <span id="plansTodayChip" class="analytics-kpi-chip analytics-kpi-chip-neutral">Сегодня: 0</span>
                    <span id="plansOverdueChip" class="analytics-kpi-chip analytics-kpi-chip-negative">Просрочено: 0</span>
                  </div>
                </div>
                <div class="plans-financial-kpi-line">
                  <div id="plansFinancialValue" class="plans-financial-kpi-value">0,00&nbsp;\uE901</div>
                  <div id="plansFinancialDelta" class="plans-financial-kpi-delta">+0,00&nbsp;\uE901</div>
                </div>
                <div id="plansFinancialMeta" class="subtitle plans-financial-kpi-meta">0,00&nbsp;\uE901</div>
              </article>
            </div>
            <div class="plans-controls-row">
              <div class="toolbar section-action-toolbar search-toolbar plans-toolbar">
                <div class="segmented" id="plansTabTabs" role="tablist" aria-label="Вкладки планов">
                  <button class="segmented-btn active" data-plan-tab="due" type="button">К подтверждению</button>
                  <button class="segmented-btn" data-plan-tab="oneoff" type="button">Разовые</button>
                  <button class="segmented-btn" data-plan-tab="recurring" type="button">Регулярные</button>
                  <button class="segmented-btn" data-plan-tab="history" type="button">История</button>
                </div>
                <div class="segmented" id="plansKindTabs" role="tablist" aria-label="Тип планов">
                  <button class="segmented-btn active" data-plan-kind="all" type="button">Все</button>
                  <button class="segmented-btn" data-plan-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-plan-kind="income" type="button">Доход</button>
                </div>
                <div class="segmented" id="plansStatusTabs" role="tablist" aria-label="Статус сроков планов">
                  <button class="segmented-btn active" data-plan-status="all" type="button">Все сроки</button>
                  <button class="segmented-btn" data-plan-status="overdue" type="button">Просрочено</button>
                  <button class="segmented-btn" data-plan-status="due" type="button">Сегодня</button>
                  <button class="segmented-btn" data-plan-status="upcoming" type="button">Впереди</button>
                </div>
                <div class="segmented hidden" id="plansHistoryEventTabs" role="tablist" aria-label="Тип событий истории планов">
                  <button class="segmented-btn active" data-plan-history-event="all" type="button">Все события</button>
                  <button class="segmented-btn" data-plan-history-event="confirmed" type="button">Подтверждения</button>
                  <button class="segmented-btn" data-plan-history-event="skipped" type="button">Пропуски</button>
                  <button class="segmented-btn" data-plan-history-event="reminded" type="button">Напоминания</button>
                </div>
              </div>
            </div>
            <div class="table-search-row plans-search-row">
              <input id="plansSearchQ" class="table-search-input plans-search-input" type="text" placeholder="Поиск по категории/комментарию" />
            </div>
            <div id="plansList" class="plans-list"></div>
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
              <div class="toolbar section-action-toolbar debt-toolbar">
                <input id="debtSearchQ" class="table-search-input debt-toolbar-search" type="text" placeholder="Поиск по контрагенту/комментарию" />
                <div class="segmented debt-toolbar-status" id="debtStatusTabs" role="tablist" aria-label="Статус долгов">
                  <button class="segmented-btn active" data-debt-status="active" type="button">Активные</button>
                  <button class="segmented-btn" data-debt-status="all" type="button">Все</button>
                  <button class="segmented-btn" data-debt-status="closed" type="button">Закрытые</button>
                </div>
                <div class="segmented debt-toolbar-sort" id="debtSortTabs" role="tablist" aria-label="Сортировка долгов">
                  <button class="segmented-btn active" data-debt-sort="priority" type="button">Приоритет</button>
                  <button class="segmented-btn" data-debt-sort="amount" type="button">По сумме</button>
                  <button class="segmented-btn" data-debt-sort="name" type="button">По имени</button>
                </div>
                <button id="deleteAllDebtsBtn" class="btn btn-danger debt-toolbar-danger" type="button">Удалить все</button>
              </div>
            </div>
            <div id="debtsSectionKpi" class="analytics-kpi-grid section-kpi-grid debts-section-kpi" aria-label="Итоги долгов"></div>
            <div id="debtsCards" class="debt-cards"></div>
            <div id="debtsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>

        <section id="currencySection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div></div>
              <div class="toolbar">
                <button id="currencyPortfolioActivityBtn" class="btn btn-secondary" type="button">Журнал</button>
                <button id="openCurrencyTradePanelBtn" class="btn btn-cta" type="button">+ Сделка</button>
                <button id="openCurrencyRatePanelBtn" class="btn btn-secondary" type="button">Обновить курс</button>
              </div>
            </div>
            <div class="table-search-row">
              <div id="currencyFilterTabs" class="segmented" role="tablist" aria-label="Фильтр валют"></div>
            </div>
            <div id="currencySummaryGrid" class="analytics-kpi-grid">
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Текущая оценка открытых позиций</div>
                <strong id="currencySummaryCurrentValue">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Вложено в открытые позиции</div>
                <strong id="currencySummaryBookValue">0</strong>
              </article>
              <article id="currencySummaryResultCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="currencySummaryResultLabel" class="muted-small">Нереализованный результат</div>
                <strong id="currencySummaryResultValue">0</strong>
              </article>
              <article id="currencySummaryRealizedCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="currencySummaryRealizedLabel" class="muted-small">Реализованный результат</div>
                <strong id="currencySummaryRealizedValue">0</strong>
              </article>
              <article id="currencySummaryCombinedCard" class="analytics-kpi-card analytics-kpi-neutral">
                <div id="currencySummaryCombinedLabel" class="muted-small">Итоговый результат</div>
                <strong id="currencySummaryCombinedValue">0</strong>
              </article>
              <article class="analytics-kpi-card analytics-kpi-neutral">
                <div class="muted-small">Открытых позиций</div>
                <strong id="currencySummaryActiveCount">0</strong>
              </article>
            </div>
            <div class="toolbar analytics-currency-chart-toolbar">
              <div id="currencyPerformancePeriodTabs" class="segmented" role="tablist" aria-label="Период графика валютного результата">
                <button class="segmented-btn" data-currency-performance-period="30d" type="button">30 дней</button>
                <button class="segmented-btn active" data-currency-performance-period="90d" type="button">3 месяца</button>
                <button class="segmented-btn" data-currency-performance-period="365d" type="button">12 месяцев</button>
                <button class="segmented-btn" data-currency-performance-period="all_time" type="button">Все время</button>
              </div>
              <div id="currencyPerformancePeriodPopover" class="app-popover app-popover-floating period-control-popover hidden" role="dialog" aria-label="Быстрый выбор периода графика валют">
                <div id="currencyPerformancePeriodOptions" class="settings-picker-options"></div>
              </div>
              <div id="currencyPerformanceRangeLabel" class="subtitle"></div>
            </div>
            <div class="analytics-trend-chart-wrap">
              <svg id="currencyPerformanceChart" class="analytics-trend-chart" viewBox="0 0 980 280" preserveAspectRatio="none" aria-label="История валютного результата"></svg>
            </div>
            <div id="currencyBalancesRow" class="currency-balance-grid"></div>
            <div id="currencyPositionsList" class="plans-list"></div>
            <div id="currencyRatePanel" class="panel hidden">
              <form id="currencyRateForm" class="category-modal-form">
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Валюта</span>
                    <select id="currencyRateAsset">
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="RUB">RUB (₽)</option>
                      <option value="CNY">CNY (¥)</option>
                      <option value="PLN">PLN (zł)</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>Курс к BYN</span>
                    <input id="currencyRateValue" type="number" min="0" step="0.000001" placeholder="3.270000" />
                  </label>
                </div>
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Дата курса</span>
                    <input id="currencyRateDate" type="date" />
                  </label>
                  <label class="field">
                    <span>Источник</span>
                    <input id="currencyRateSource" type="text" maxlength="20" value="manual" />
                  </label>
                </div>
                <div class="settings-actions">
                  <button id="submitCurrencyRateBtn" class="btn btn-secondary" type="submit">Обновить курс</button>
                  <button id="closeCurrencyRatePanelBtn" class="btn btn-secondary" type="button">Скрыть</button>
                </div>
              </form>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table operations-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Действие</th>
                    <th>Валюта</th>
                    <th>Количество</th>
                    <th>Курс</th>
                    <th>Комментарий</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="currencyTradesBody"></tbody>
              </table>
            </div>
            <div id="currencyTradesInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>

        <section id="itemCatalogSection" class="section-block hidden">
          <div id="itemCatalogViewTabs" class="segmented item-catalog-view-tabs" role="tablist" aria-label="Режим каталога позиций">
            <button class="segmented-btn active" data-item-catalog-view="positions" type="button">Позиции</button>
            <button class="segmented-btn" data-item-catalog-view="recommendations" type="button">Рекомендации</button>
          </div>
          <section id="itemCatalogPositionsView" class="panel">
            <div class="table-search-row">
              <input id="itemCatalogSearchQ" class="table-search-input" type="text" placeholder="Поиск по источнику и позиции" />
              <div class="toolbar section-action-toolbar search-toolbar item-catalog-controls">
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
            <div id="itemCatalogKpiGrid" class="analytics-kpi-grid section-kpi-grid" aria-label="Итоги каталога позиций"></div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table item-catalog-table">
                <thead>
                  <tr>
                    <th>Источник</th>
                    <th>Позиция</th>
                    <th>Категория</th>
                    <th>Последняя цена</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="itemCatalogBody"></tbody>
              </table>
            </div>
          </section>
          <section id="itemRecommendationsView" class="panel hidden">
            <div class="item-recommendations-heading">
              <div>
                <h3>Управление рекомендациями</h3>
                <p class="muted">Настройте повторные покупки сразу для нескольких позиций. Ничего не включается автоматически.</p>
              </div>
              <button id="refreshItemRecommendationsBtn" class="btn btn-secondary btn-xs" type="button">Обновить</button>
            </div>
            <div id="itemRecommendationsKpiGrid" class="analytics-kpi-grid section-kpi-grid" aria-label="Итоги рекомендаций"></div>
            <div class="item-recommendations-toolbar">
              <input id="itemRecommendationsSearchQ" class="table-search-input" type="text" placeholder="Поиск по позиции и источнику" />
              <div id="itemRecommendationStatusTabs" class="segmented" role="tablist" aria-label="Фильтр рекомендаций">
                <button class="segmented-btn active" data-recommendation-status="all" type="button">Все</button>
                <button class="segmented-btn" data-recommendation-status="due" type="button">Пора</button>
                <button class="segmented-btn" data-recommendation-status="upcoming" type="button">Скоро</button>
                <button class="segmented-btn" data-recommendation-status="configured" type="button">Настроены</button>
                <button class="segmented-btn" data-recommendation-status="unconfigured" type="button">Не настроены</button>
                <button class="segmented-btn" data-recommendation-status="candidates" type="button">Кандидаты</button>
              </div>
            </div>
            <div id="itemRecommendationBulkBar" class="bulk-bar item-recommendation-bulk-bar hidden">
              <strong id="itemRecommendationSelectedCount">Выбрано: 0</strong>
              <label class="item-recommendation-bulk-field">
                <span>Запас</span>
                <input id="itemRecommendationBulkInterval" type="number" min="1" max="3650" step="1" value="30" />
                <span>дн.</span>
              </label>
              <label class="item-recommendation-bulk-field">
                <span>На количество</span>
                <input id="itemRecommendationBulkQuantity" type="number" min="0.001" max="100000" step="0.001" value="1" />
              </label>
              <button id="enableSelectedRecommendationsBtn" class="btn btn-primary btn-xs" type="button">Включить и применить</button>
              <button id="snoozeSelectedRecommendationsBtn" class="btn btn-secondary btn-xs" type="button">Отложить на 7 дней</button>
              <button id="disableSelectedRecommendationsBtn" class="btn btn-danger btn-xs" type="button">Отключить</button>
              <button id="clearSelectedRecommendationsBtn" class="btn btn-ghost btn-xs" type="button">Снять выбор</button>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table item-recommendations-table">
                <thead>
                  <tr>
                    <th><input id="itemRecommendationsSelectAll" type="checkbox" aria-label="Выбрать все видимые рекомендации" /></th>
                    <th>Позиция</th>
                    <th>Последняя покупка</th>
                    <th>Настройка</th>
                    <th>Следующая дата</th>
                    <th>Статус</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="itemRecommendationsBody"></tbody>
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
                  <div class="settings-picker-field">
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
                    <button id="timezonePickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                  </div>
                </label>
              </section>
              <section class="settings-block">
                <h3>Интерфейс</h3>
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Валюта</span>
                    <div class="settings-picker-field">
                      <select id="currencySelect">
                        <option value="BYN">BYN (\uE901)</option>
                        <option value="RUB">RUB (₽)</option>
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                      </select>
                      <button id="currencyPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                    </div>
                  </label>
                  <label class="field">
                    <span>Позиция символа</span>
                    <div class="settings-picker-field">
                      <select id="currencyPositionSelect">
                        <option value="suffix">Справа</option>
                        <option value="prefix">Слева</option>
                      </select>
                      <button id="currencyPositionPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                    </div>
                  </label>
                </div>
                <div id="currencyPreview" class="settings-preview">Пример: 1 234,56&nbsp;\uE901</div>
                <label class="settings-switch-row">
                  <input id="showDashboardAnalyticsToggle" type="checkbox" checked />
                  <span>Показывать блок аналитики на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardOperationsToggle" type="checkbox" checked />
                  <span>Показывать блок планов на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardDebtsToggle" type="checkbox" checked />
                  <span>Показывать карточки долгов на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardCurrencyToggle" type="checkbox" checked />
                  <span>Показывать валютный блок на дашборде</span>
                </label>
                <section class="settings-block">
                  <h3>Отслеживаемые валюты</h3>
                  <div id="trackedCurrenciesWrap" class="settings-grid-2">
                    <label class="settings-switch-row">
                      <input name="trackedCurrency" type="checkbox" value="USD" checked />
                      <span>USD</span>
                    </label>
                    <label class="settings-switch-row">
                      <input name="trackedCurrency" type="checkbox" value="EUR" checked />
                      <span>EUR</span>
                    </label>
                    <label class="settings-switch-row">
                      <input name="trackedCurrency" type="checkbox" value="RUB" />
                      <span>RUB</span>
                    </label>
                    <label class="settings-switch-row">
                      <input name="trackedCurrency" type="checkbox" value="CNY" />
                      <span>CNY</span>
                    </label>
                    <label class="settings-switch-row">
                      <input name="trackedCurrency" type="checkbox" value="PLN" />
                      <span>PLN</span>
                    </label>
                  </div>
                </section>
                <label class="field">
                  <span>Строк планов на дашборде</span>
                  <div class="settings-picker-field">
                    <select id="dashboardOperationsLimitSelect">
                      <option value="5">5</option>
                      <option value="8">8</option>
                      <option value="12">12</option>
                    </select>
                    <button id="dashboardOperationsLimitPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                  </div>
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
                <h3>Напоминания</h3>
                <label class="settings-switch-row">
                  <input id="plansRemindersToggle" type="checkbox" checked />
                  <span>Напоминать о планах в Telegram</span>
                </label>
                <label class="field">
                  <span>Время уведомления по планам</span>
                  <input id="plansReminderTimeInput" type="time" value="09:00" />
                </label>
                <label class="settings-switch-row">
                  <input id="debtsRemindersToggle" type="checkbox" checked />
                  <span>Напоминать о долгах в Telegram</span>
                </label>
                <label class="field">
                  <span>Время уведомления по долгам</span>
                  <input id="debtsReminderTimeInput" type="time" value="09:00" />
                </label>
                <label class="settings-switch-row">
                  <input id="currencyDigestToggle" type="checkbox" />
                  <span>Присылать раз в день курсы отслеживаемых валют в Telegram</span>
                </label>
                <label class="field">
                  <span>Время уведомления по курсам</span>
                  <input id="currencyDigestTimeInput" type="time" value="10:00" />
                </label>
                <div class="field">
                  <span>Алерты по курсам</span>
                  <div id="currencyAlertsSettings" class="settings-alerts-grid">
                    ${["USD", "EUR", "RUB", "CNY", "PLN"].map((currency) => `
                      <div class="settings-alert-row" data-currency-alert-row="${currency}">
                        <div class="settings-alert-row-head">
                          <strong>${currency}</strong>
                          <span class="muted-small">Telegram при достижении порога</span>
                        </div>
                        <div class="settings-alert-row-fields">
                          <label class="field">
                            <span>Выше курса</span>
                            <input
                              type="number"
                              inputmode="decimal"
                              step="0.0001"
                              min="0"
                              placeholder="Например 3.5000"
                              data-currency-alert="${currency}"
                              data-currency-alert-kind="above"
                            />
                          </label>
                          <label class="field">
                            <span>Ниже курса</span>
                            <input
                              type="number"
                              inputmode="decimal"
                              step="0.0001"
                              min="0"
                              placeholder="Например 3.1000"
                              data-currency-alert="${currency}"
                              data-currency-alert-kind="below"
                            />
                          </label>
                        </div>
                      </div>
                    `).join("")}
                  </div>
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
                <input id="deleteMePhrase" type="text" placeholder="Введите УДАЛИТЬ" />
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
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Диагностика валюты</h3>
                <p class="subtitle">Freshness курсов, digest и alerts по tracked currencies</p>
              </div>
              <button id="refreshAdminCurrencyDiagnosticsBtn" class="btn btn-secondary btn-xs" type="button">Обновить</button>
            </div>
            <div id="adminCurrencyDiagnosticsKpi" class="kpi-grid"></div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table admin-users-table">
                <thead>
                  <tr>
                    <th>Валюта</th>
                    <th>Пользователей</th>
                    <th>Digest</th>
                    <th>Alerts</th>
                    <th>Последний курс</th>
                    <th>Stale</th>
                    <th>Нет курса</th>
                  </tr>
                </thead>
                <tbody id="adminCurrencyDiagnosticsBody"></tbody>
              </table>
            </div>
          </section>
        </section>
`;
})();
