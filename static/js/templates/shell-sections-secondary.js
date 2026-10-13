(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shellSectionsSecondary = `

        <section id="workSection" class="section-block hidden">
          <section class="panel">
            <div class="segmented work-view-tabs" id="workViewTabs" role="tablist" aria-label="Разделы работы">
              <button class="segmented-btn active" data-work-view="timesheet" type="button">Табель</button>
              <button class="segmented-btn" data-work-view="payments" type="button">Выплаты</button>
              <button class="segmented-btn" data-work-view="statistics" type="button">Статистика</button>
              <button class="segmented-btn" data-work-view="settings" type="button">Настройки</button>
              <button class="segmented-btn" data-work-view="companies" type="button">Компании</button>
              <button class="segmented-btn" data-work-view="contracts" type="button">История работы</button>
            </div>

            <div id="workStatisticsView" class="hidden">
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
                  <button id="workStatisticsCurrentBtn" class="btn btn-secondary btn-xs btn-icon" type="button" aria-label="Текущий период" title="Текущий период">${window.App.icons.svg("calendar")}</button>
                </div>
              </div>
              <form id="workStatisticsCustomForm" class="work-statistics-custom hidden">
                <label class="field"><span>С</span><div class="date-input-wrap"><input id="workStatisticsDateFrom" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workStatisticsDateFrom" aria-label="Открыть календарь"></button></div></label>
                <label class="field"><span>По</span><div class="date-input-wrap"><input id="workStatisticsDateTo" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workStatisticsDateTo" aria-label="Открыть календарь"></button></div></label>
                <button class="btn btn-primary btn-icon" type="submit" aria-label="Применить период" title="Применить период">${window.App.icons.svg("save")}</button>
              </form>
              <div id="workStatisticsKpi" class="analytics-kpi-grid section-kpi-grid"></div>
              <article class="work-statistics-progress-card">
                <div class="row between"><span>Выполнение плана часов</span><strong id="workStatisticsProgressLabel">0%</strong></div>
                <div class="work-statistics-progress"><i id="workStatisticsProgressBar"></i></div>
              </article>
              <div class="panel-head"><div><h3>Динамика по месяцам</h3><p class="subtitle">Рабочие часы и фактические выплаты</p></div></div>
              <div id="workStatisticsMonths" class="work-statistics-months"></div>
            </div>

            <div id="workTimesheetView" class="work-hero-panel">
            <div class="panel-head row between work-section-head">
              <div>
                <h3 id="workTimesheetPeriodTitle" class="sr-only">Табель</h3>
              </div>
              <div class="work-month-control">
                <button id="workPrevMonthBtn" class="period-step-btn" type="button" aria-label="Предыдущий месяц">‹</button>
                <button id="workMonthTrigger" class="btn btn-secondary analytics-grid-picker-trigger" type="button" aria-haspopup="dialog">Месяц</button>
                <div id="workMonthPopover" class="app-popover app-popover-floating period-control-popover analytics-grid-picker-popover hidden" role="dialog" aria-label="Выбор месяца табеля">
                  <div id="workYearOptions" class="settings-picker-options work-period-year-options"></div>
                  <div id="workMonthOptions" class="settings-picker-options work-period-month-options"></div>
                </div>
                <button id="workNextMonthBtn" class="period-step-btn" type="button" aria-label="Следующий месяц">›</button>
                <button id="workTodayBtn" class="btn btn-secondary btn-xs btn-icon" type="button" aria-label="Текущий период" title="Текущий период">${window.App.icons.svg("calendar")}</button>
              </div>
            </div>
<div class="work-timesheet-layout"><div class="work-calendar-main">
            <div id="workSummaryGrid" class="analytics-kpi-grid section-kpi-grid work-time-summary-grid" aria-live="polite"></div>

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
                  <button id="closeWorkDayEditorBtn" class="btn btn-ghost btn-xs btn-icon" type="button" aria-label="Закрыть" title="Закрыть">${window.App.icons.svg("close")}</button>
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
                  <button class="btn btn-primary btn-icon" type="submit" aria-label="Сохранить исключение" title="Сохранить исключение">${window.App.icons.svg("save")}</button>
                  <button id="resetWorkDayBtn" class="btn btn-secondary btn-icon" type="button" aria-label="Вернуть по графику" title="Вернуть по графику">${window.App.icons.svg("refresh")}</button>
                </div>
              </form>
              </div><aside class="work-payroll-sidebar" aria-label="Зарплата и оценка заработка">
            <section class="work-salary-cycle-card" aria-label="Зарплата за расчётный период">
              <div id="workMoneySummaryGrid" aria-live="polite"></div>
              <div id="workPaymentsGrid" class="work-salary-cycle-components"></div>
            </section>
                  <div id="workEarningsRates" class="work-earnings-rates"></div>
              </aside></div>
            </div>

            <form id="workSettingsForm" class="settings-form hidden">
              <section class="settings-block">
                <h3>График работы</h3>
                <div class="settings-grid-2">
                  <label class="field"><span>Компания</span><input id="workCompany" type="text" maxlength="160" autocomplete="off" placeholder="Битрикс" /></label>
                  <label class="field"><span>Должность</span><input id="workPosition" type="text" maxlength="160" /></label>
                  <label class="field"><span>Дата начала работы</span><div class="date-input-wrap"><input id="workStartDate" type="date" /><button class="date-input-trigger" type="button" data-date-picker-trigger="workStartDate" aria-label="Открыть календарь"></button></div></label>
                  <label class="field"><span>Часов в обычный день</span><input id="workStandardHours" type="number" min="0.25" max="24" step="0.25" value="8" /></label>
                  <label class="field"><span>Начало рабочего дня</span><input id="workDayStartTime" type="time" step="60" value="09:00" /></label>
                  <label class="field"><span>Конец рабочего дня</span><input id="workDayEndTime" type="time" step="60" value="18:00" /></label>
                  <label class="field"><span>Начало обеда</span><input id="workLunchStartTime" type="time" step="60" value="13:00" /></label>
                  <label class="field"><span>Конец обеда</span><input id="workLunchEndTime" type="time" step="60" value="14:00" /></label>
                </div>
                <p class="muted-small work-schedule-hint">Часы текущей смены обновляются автоматически, без обеда. Ручное исключение имеет приоритет.</p>
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
              <div class="settings-actions"><button class="btn btn-primary btn-icon" type="submit" aria-label="Сохранить настройки" title="Сохранить настройки">${window.App.icons.svg("save")}</button></div>
            </form>

            <div id="workCompaniesView" class="hidden">
              <div class="panel-head">
                <div><h3>Компании</h3><p class="subtitle">Фактический заработок по операциям категории «Зарплата» и периодам работы</p></div>
              </div>
              <div id="workCompaniesGrid" class="work-companies-grid"></div>
              <div id="workCompanyDetails" class="work-company-details"></div>
            </div>

            <div id="workPaymentsView" class="hidden">
              <section class="work-actual-payments-section">
                <div class="panel-head row between work-payment-history-head">
                  <div><h3>Фактические выплаты</h3><p class="subtitle">Полученные деньги из подтверждённых планов и операций, связанных вручную</p></div>
                  <button id="workPaymentLinkToggle" class="btn btn-secondary btn-icon" type="button" aria-expanded="false" aria-controls="workPaymentLinkPanel" aria-label="Связать операцию" title="Связать операцию">${window.App.icons.svg("link")}</button>
                </div>
                <section id="workPaymentLinkPanel" class="work-payment-link-panel hidden">
                  <div class="panel-head row between">
                    <div><h3>Связать доходную операцию</h3><p class="subtitle">Выберите выплату и укажите, чем она является</p></div>
                    <button id="workPaymentLinkClose" class="btn btn-ghost btn-xs btn-icon" type="button" aria-label="Закрыть" title="Закрыть">${window.App.icons.svg("close")}</button>
                  </div>
                  <div id="workPaymentLinkRole" class="segmented work-payment-link-role" role="group" aria-label="Роль выплаты">
                    <button class="segmented-btn active" data-work-payment-link-role="salary" type="button" aria-pressed="true">Основная часть</button>
                    <button class="segmented-btn" data-work-payment-link-role="advance" type="button" aria-pressed="false">Аванс</button>
                  </div>
                  <form id="workPaymentCandidateForm" class="work-payment-candidate-controls">
                    <label class="field"><span>С</span><div class="date-input-wrap"><input id="workPaymentCandidateDateFrom" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workPaymentCandidateDateFrom" aria-label="Открыть календарь"></button></div></label>
                    <label class="field"><span>По</span><div class="date-input-wrap"><input id="workPaymentCandidateDateTo" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workPaymentCandidateDateTo" aria-label="Открыть календарь"></button></div></label>
                    <label class="field work-payment-candidate-search"><span>Поиск</span><input id="workPaymentCandidateSearch" class="table-search-input" type="search" maxlength="100" placeholder="Комментарий или категория" /></label>
                    <button class="btn btn-secondary btn-icon" type="submit" aria-label="Найти выплаты" title="Найти выплаты">${window.App.icons.svg("search")}</button>
                  </form>
                  <div id="workPaymentCandidatesList" class="work-payment-candidates-list"></div>
                </section>
                <div id="workActualPaymentsList" class="work-actual-payments-list"></div>
              </section>
            </div>

            <div id="workContractsView" class="hidden">
              <form id="workContractForm" class="settings-form">
                <section class="settings-block">
                  <h3 id="workContractFormHeading">Новый период или смена работы</h3>
                  <p id="workContractFormSubtitle" class="muted-small">Новая текущая работа автоматически завершит предыдущий период этой же датой. Дата перехода будет относиться к новому периоду.</p>
                  <div class="settings-grid-2">
                    <label class="field"><span>Действует с</span><div class="date-input-wrap"><input id="workContractFrom" type="date" required /><button class="date-input-trigger" type="button" data-date-picker-trigger="workContractFrom" aria-label="Открыть календарь"></button></div></label>
                    <label class="field"><span>Действует до</span><div class="date-input-wrap"><input id="workContractTo" type="date" /><button class="date-input-trigger" type="button" data-date-picker-trigger="workContractTo" aria-label="Открыть календарь"></button></div></label>
                    <label class="field"><span>Компания</span><input id="workContractCompany" type="text" maxlength="160" autocomplete="off" /></label>
                    <label class="field"><span>Должность</span><input id="workContractPosition" type="text" maxlength="160" /></label>
                    <label class="field"><span>Оклад на руки</span><input id="workContractSalary" type="number" min="0" step="0.01" /></label>
                    <label class="field"><span>Валюта</span><select id="workContractCurrency"><option value="BYN">BYN</option><option value="USD">USD</option><option value="EUR">EUR</option></select></label>
                  </div>
                  <label class="field"><span>Комментарий</span><input id="workContractNote" type="text" maxlength="500" /></label>
                  <div class="settings-actions work-contract-form-actions">
                    <button id="workContractSubmitBtn" class="btn btn-primary btn-icon" type="submit" aria-label="Добавить период" title="Добавить период">${window.App.icons.svg("plus")}</button>
                    <button id="cancelWorkContractEditBtn" class="btn btn-secondary hidden btn-icon" type="button" aria-label="Отменить редактирование" title="Отменить редактирование">${window.App.icons.svg("close")}</button>
                  </div>
                </section>
              </form>
              <div id="workContractsList" class="plans-list work-contracts-list"></div>
            </div>
          </section>
        </section>

        <section id="plansSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Планы</h3>
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
                  <div class="plans-summary-item"><span class="muted-small">Результат операций</span><div id="plansFinancialValue" class="plans-financial-kpi-value">0,00&nbsp;\uE901</div></div>
                  <div class="plans-summary-item"><span class="muted-small">Активные планы</span><div id="plansFinancialDelta" class="plans-financial-kpi-delta">+0,00&nbsp;\uE901</div></div>
                </div>
                <div class="plans-summary-item"><span class="muted-small">После планов</span><div id="plansFinancialMeta" class="subtitle plans-financial-kpi-meta">0,00&nbsp;\uE901</div></div>
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
                <h3>Долги</h3>
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

              </div>
            </div>
            <div id="debtsSectionKpi" class="analytics-kpi-grid section-kpi-grid debts-section-kpi" aria-label="Итоги долгов"></div>
            <div id="debtsCards" class="debt-cards"></div>
            <div class="debt-list-maintenance"><button id="deleteAllDebtsBtn" class="btn btn-danger btn-icon" type="button" aria-label="Удалить все долги текущей выборки" title="Удалить все долги текущей выборки">${window.App.icons.svg("trash")}</button></div>
            <div id="debtsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>

        <section id="currencySection" class="section-block hidden">
          <div id="currencyWorkspaceTabs" class="segmented" role="tablist" aria-label="Разделы валюты"><button type="button" class="segmented-btn active" data-currency-view="portfolio">Портфель</button><button type="button" class="segmented-btn" data-currency-view="rates">Курсы и сделки</button></div>
          <section id="analyticsCurrencyPanel" class="panel analytics-tab-panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Курсы и сделки</h3>
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
                <div id="analyticsCurrencyPeriodPopover" class="app-popover app-popover-floating period-control-popover hidden" role="dialog" aria-label="Быстрый выбор периода валютной аналитики">
                  <div id="analyticsCurrencyPeriodOptions" class="settings-picker-options"></div>
                </div>
                <button id="analyticsSendCurrencyDigestBtn" class="btn-icon btn btn-secondary btn-xs" type="button" aria-label="Отправить дайджест" title="Отправить дайджест">${window.App.icons.svg("send")}</button>
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
            <section class="currency-chart-controls" aria-label="Настройки сравнения банковских курсов">
              <div class="currency-chart-controls-head">
                <div>
                  <strong>Сравнение курсов</strong>
                  <div id="analyticsCurrencyChartContext" class="muted-small">BYN за 1 единицу валюты</div>
                </div>
                <div class="toolbar">
                  <div id="analyticsCurrencyChartModeTabs" class="segmented compact-segmented" role="tablist" aria-label="Источник данных графика">
                    <button class="segmented-btn" data-analytics-currency-chart-mode="nbrb" type="button">НБРБ</button>
                    <button class="segmented-btn active" data-analytics-currency-chart-mode="banks" type="button">Банки</button>
                  </div>
                  <button id="analyticsCurrencyBackfillBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Подгрузить историю НБРБ" title="Подгрузить историю НБРБ">${window.App.icons.svg("history")}</button>
                </div>
              </div>
              <div id="analyticsCurrencyChartBankOptions" class="currency-chart-bank-options">
                <div class="currency-chart-control-groups">
                  <div class="currency-chart-control-group">
                    <span class="currency-chart-control-label">Валюта</span>
                    <div id="analyticsCurrencyChartCurrencyTabs" class="segmented compact-segmented" role="group" aria-label="Валюта для сравнения банков"></div>
                  </div>
                </div>
              </div>
              <div class="currency-chart-legend-block">
                <div class="currency-chart-legend-head">
                  <span class="currency-chart-control-label">Ряды графика</span>
                  <button id="analyticsCurrencyChartShowAllBtn" class="btn-icon btn btn-secondary hidden" type="button" aria-label="Показать все ряды" title="Показать все ряды">${window.App.icons.svg("expand")}</button>
                </div>
                <div id="analyticsCurrencyChartLegend" class="currency-chart-html-legend" role="group" aria-label="Управление рядами графика"></div>
              </div>
              <div id="analyticsCurrencyChartCoverage" class="currency-chart-coverage muted-small" aria-live="polite"></div>
            </section>
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
            <div id="analyticsCurrencyTradesInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
          <div id="currencyPortfolioView">
          <section class="panel">
            <div class="panel-head row between">
              <div></div>
              <div class="toolbar">
                <button id="currencyPortfolioActivityBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Журнал валюты" title="Журнал валюты">${window.App.icons.svg("history")}</button>
                <button id="openCurrencyTradePanelBtn" class="btn-icon btn btn-cta" type="button" aria-label="Новая сделка" title="Новая сделка">${window.App.icons.svg("plus")}</button>
                <button id="openCurrencyRatePanelBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Обновить курс" title="Обновить курс">${window.App.icons.svg("refresh")}</button>
                <button id="currencySendDigestBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Отправить дайджест" title="Отправить дайджест">${window.App.icons.svg("send")}</button>
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
            <div id="currencyBalancesRow" class="currency-balance-grid"></div>
            <div id="currencyPositionsList" class="plans-list"></div>
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
                  <button id="submitCurrencyRateBtn" class="btn-icon btn btn-secondary" type="submit" aria-label="Сохранить курс" title="Сохранить курс">${window.App.icons.svg("save")}</button>
                  <button id="closeCurrencyRatePanelBtn" class="btn-icon btn btn-secondary" type="button" aria-label="Закрыть" title="Закрыть">${window.App.icons.svg("close")}</button>
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
        </div>
        </section>

        <section id="itemCatalogSection" class="section-block hidden">
          <div id="itemCatalogViewTabs" class="segmented item-catalog-view-tabs" role="tablist" aria-label="Разделы каталога">
            <button class="segmented-btn active" data-item-catalog-view="products" type="button">Товары</button>
            <button class="segmented-btn" data-item-catalog-view="changes" type="button">Изменения цен</button>
            <button class="segmented-btn" data-item-catalog-view="purchases" type="button">Покупки</button>
            <button class="segmented-btn" data-item-catalog-view="discounts" type="button">Скидки</button>
            <button class="segmented-btn" data-item-catalog-view="sources" type="button">По источникам</button>
            <button class="segmented-btn" data-item-catalog-view="brands" type="button">Бренды</button>
          </div>
          <section id="analyticsCommercePanel" class="panel analytics-tab-panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Скидки по покупкам</h3>
                <p id="analyticsCommerceRangeLabel" class="subtitle">Нет периода</p>
              </div>
              <div class="toolbar analytics-commerce-toolbar">
                <div class="analytics-switch-group">
                  <span class="muted-small">Раздел</span>
                  <div id="analyticsCommerceModeTabs" class="segmented hidden" role="tablist" aria-label="Раздел ценовой аналитики">
                    <button class="segmented-btn active" data-analytics-commerce-mode="prices" type="button">Цены</button>
                    <button class="segmented-btn" data-analytics-commerce-mode="discounts" type="button">Скидки</button>
                  </div>
                </div>
                <div class="analytics-switch-group">
                  <span class="muted-small">Метрика</span>
                  <div id="analyticsCommerceMetricTabs" class="segmented" role="tablist" aria-label="Метрика ценовой аналитики"></div>
                </div>
              </div>
            </div>
            <div id="analyticsCommerceDiscountTypeTabs" class="segmented analytics-commerce-discount-types hidden" role="tablist" aria-label="Тип скидки">
              <button class="segmented-btn active" data-analytics-commerce-discount-type="all" type="button">Все</button>
              <button class="segmented-btn" data-analytics-commerce-discount-type="promo" type="button">Акции</button>
              <button class="segmented-btn" data-analytics-commerce-discount-type="coupon" type="button">Купоны</button>
              <button class="segmented-btn" data-analytics-commerce-discount-type="loyalty_points" type="button">Баллы</button>
            </div>
            <div id="analyticsCommerceSummary" class="analytics-kpi-secondary"></div>
            <div class="analytics-commerce-layout">
              <section class="analytics-commerce-ranking-block">
                <div class="analytics-position-ranking-head">
                  <div>
                    <h4 id="analyticsCommerceRankingTitle">Топ подорожаний</h4>
                    <span class="muted-small">Выберите позицию для просмотра деталей</span>
                  </div>
                  <button id="analyticsCommerceSortBtn" class="analytics-position-sort-btn" type="button" title="Сначала больше" aria-label="Сортировка: сначала больше">↓</button>
                </div>
                <div id="analyticsCommerceRanking" class="analytics-position-ranking-list"></div>
              </section>
              <section id="analyticsCommerceFocus" class="analytics-commerce-focus">
                <div class="muted-small">Выберите позицию в рейтинге</div>
              </section>
            </div>
            <div id="analyticsCommerceEmpty" class="muted-small hidden">За выбранный период данных нет</div>
          </section>
          <section id="analyticsPositionsPanel" class="panel analytics-tab-panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Покупки по позициям</h3>
                <p id="analyticsPositionsRangeLabel" class="subtitle">Нет периода</p>
              </div>
              <div class="toolbar analytics-positions-toolbar">
                <div class="analytics-switch-group">
                  <span class="muted-small">Период</span>
                  <div class="period-control" data-period-control="analytics-positions">
                    <button id="analyticsPositionsPrevBtn" class="period-step-btn" type="button" aria-label="Предыдущий период">‹</button>
                    <button id="analyticsPositionsPeriodTrigger" class="period-current-btn" type="button" aria-haspopup="dialog" aria-controls="analyticsPositionsPeriodPopover">
                      <span class="period-current-label">Период</span>
                      <strong id="analyticsPositionsPeriodControlLabel">Этот месяц</strong>
                    </button>
                    <button id="analyticsPositionsNextBtn" class="period-step-btn" type="button" aria-label="Следующий период">›</button>
                  </div>
                  <div id="analyticsPositionsPeriodPopover" class="app-popover app-popover-floating period-control-popover hidden" role="dialog" aria-label="Быстрый выбор периода позиций">
                    <div id="analyticsPositionsPeriodOptions" class="settings-picker-options"></div>
                  </div>
                </div>
                <div class="analytics-switch-group">
                  <span class="muted-small">Метрика</span>
                  <div class="segmented" id="analyticsPositionsMetricTabs" role="tablist" aria-label="Метрика позиций">
                    <button class="segmented-btn active" data-analytics-positions-metric="purchases" type="button">Покупки</button>
                    <button class="segmented-btn" data-analytics-positions-metric="pieces" type="button">Шт. товара</button>
                    <button class="segmented-btn" data-analytics-positions-metric="packs" type="button">Упаковки</button>
                    <button class="segmented-btn" data-analytics-positions-metric="mass_kg" type="button">Вес, кг</button>
                    <button class="segmented-btn" data-analytics-positions-metric="volume_l" type="button">Объём, л</button>
                    <button class="segmented-btn" data-analytics-positions-metric="content_pieces" type="button">Шт. внутри</button>
                    <button class="segmented-btn" data-analytics-positions-metric="amount" type="button">Сумма</button>
                  </div>
                </div>
              </div>
            </div>
            <div class="analytics-positions-filters">
              <label class="field hidden"><span>Валюта сумм</span><select id="analyticsPositionsCurrency" aria-label="Валюта сумм позиций"></select></label>
              <input id="analyticsPositionsSearch" type="search" placeholder="Поиск позиции" autocomplete="off" />
              <input id="analyticsPositionsSourceSearch" type="search" placeholder="Источник" autocomplete="off" />
              <div class="segmented" id="analyticsPositionsLimitTabs" role="tablist" aria-label="Количество позиций">
                <button class="segmented-btn active" data-analytics-positions-limit="top" type="button">Топ-10</button>
                <button class="segmented-btn" data-analytics-positions-limit="all" type="button">Все</button>
              </div>
            </div>
            <div id="analyticsPositionsSummary" class="analytics-kpi-secondary"></div>
            <div class="analytics-positions-overview">
              <section class="analytics-position-ranking-block">
                <div class="analytics-position-ranking-head">
                  <div>
                    <h4 id="analyticsPositionsRankingTitle">Чаще всего покупали</h4>
                    <span class="muted-small">Выберите позицию для просмотра динамики</span>
                  </div>
                  <button id="analyticsPositionsSortBtn" class="analytics-position-sort-btn" type="button" title="Сначала больше" aria-label="Сортировка: сначала больше">↓</button>
                </div>
                <div id="analyticsPositionsRanking" class="analytics-position-ranking-list"></div>
              </section>
              <section id="analyticsPositionsMobileFocus" class="analytics-positions-mobile-focus"></section>
            </div>
            <div id="analyticsPositionsMatrixWrap" class="table-wrap analytics-positions-matrix-wrap">
              <table class="table analytics-positions-matrix">
                <thead id="analyticsPositionsMatrixHead"></thead>
                <tbody id="analyticsPositionsMatrixBody"></tbody>
              </table>
            </div>
            <div id="analyticsPositionsEmpty" class="muted-small hidden">За выбранный период позиции не найдены</div>
          </section>
          <section id="catalogProductsView" class="panel catalog-products-view">
            <div class="catalog-products-heading">
              <div>
                <h3>Товары</h3>

              </div>
              <div class="row catalog-products-heading-actions">
                <button id="catalogProductsCandidatesBtn" class="btn btn-secondary btn-xs hidden" type="button">Возможные совпадения <span id="catalogProductsCandidatesCount"></span></button>
              </div>
            </div>
            <div class="table-search-row catalog-products-toolbar">
              <input id="catalogProductsSearchQ" class="table-search-input" type="search" placeholder="Товар, бренд, источник, штрихкод или артикул" />
              <div class="toolbar section-action-toolbar search-toolbar">
                <button id="catalogProductsCollapseAllBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Свернуть все" aria-label="Свернуть все">${window.App.icons.svg("collapse")}</button>
                <button id="catalogProductsExpandAllBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Развернуть все" aria-label="Развернуть все">${window.App.icons.svg("expand")}</button>
                <button id="refreshCatalogProductsBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Обновить товары" aria-label="Обновить товары">${window.App.icons.svg("refresh")}</button>
                <button id="resetCatalogProductWidthsBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Сбросить ширину колонок" aria-label="Сбросить ширину колонок">${window.App.icons.svg("width")}</button>
              </div>
            </div>
            <div id="catalogProductsKpiGrid" class="analytics-kpi-grid section-kpi-grid catalog-compact-kpis" aria-label="Итоги каталога товаров"></div>
            <div id="catalogProductsCandidatesPanel" class="catalog-product-candidates hidden" aria-live="polite"></div>
            <div id="catalogProductsBulkBar" class="bulk-bar hidden" aria-live="polite">
              <strong id="catalogProductsSelectedCount">Выбрано: 0</strong>
              <span class="muted-small">Выберите главную карточку при объединении</span>
              <button id="mergeCatalogProductsBtn" class="btn-icon btn btn-primary btn-xs" type="button" title="Объединить товары" aria-label="Объединить товары">${window.App.icons.svg("merge")}</button>
              <button id="clearSelectedCatalogProductsBtn" class="btn-icon btn btn-ghost btn-xs" type="button" title="Снять выбор" aria-label="Снять выбор">${window.App.icons.svg("close")}</button>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table catalog-products-table">
                <colgroup><col /><col /><col /><col /><col /><col /><col /><col /></colgroup>
                <thead>
                  <tr>
                    <th><input id="catalogProductsSelectAll" type="checkbox" aria-label="Выбрать все видимые товары" /></th>
                    <th>Товар</th>
                    <th>Бренд</th>
                    <th>Категория</th>
                    <th>Источники</th>
                    <th>Цена</th>
                    <th>Последняя покупка</th>
                    <th>Фасовка</th>
                  </tr>
                </thead>
                <tbody id="catalogProductsBody"></tbody>
              </table>
            </div>
          </section>
            <section id="catalogPriceChanges" class="panel catalog-price-changes hidden">
              <h3>Изменения цен</h3>
              <p class="muted-small">По покупкам · дата чека, а не изменения магазинной цены</p>
              <form id="catalogPriceChangesForm" class="catalog-price-changes-filters">
                <label class="field"><span>Товар или магазин</span><input name="q" type="search" maxlength="160" placeholder="Поиск в изменениях цен" /></label>
                <label class="field"><span>Сравнение</span><select name="comparison"><option value="period">От первой до последней покупки</option><option value="previous">Последняя с предыдущей</option></select></label>
                <label class="field"><span>Изменение</span><select name="direction"><option value="all">Все</option><option value="up">Подорожало</option><option value="down">Подешевело</option><option value="same">Цена вернулась / не изменилась</option></select></label>
                <button type="submit" class="btn btn-secondary btn-icon" title="Обновить сравнение" aria-label="Обновить сравнение">${window.App.icons.svg("refresh")}</button>
                <details class="catalog-price-changes-options"><summary class="btn btn-secondary btn-icon" title="Условия сравнения" aria-label="Условия сравнения">${window.App.icons.svg("filter")}</summary><div class="catalog-price-changes-advanced">
                <label class="field"><span>Цена</span><select name="price_kind"><option value="paid">Оплаченная</option><option value="regular">Обычная, если известна</option></select></label>
                <label class="field"><span>Единица сравнения</span><select name="basis"><option value="unit">За единицу продажи / упаковку</option><option value="normalized">За кг, литр или штуку содержимого</option></select></label>
                <label class="field"><span>С даты (необязательно)</span><input type="date" name="date_from" /></label>
                <label class="field"><span>По дату (необязательно)</span><input type="date" name="date_to" /></label>
                </div></details>
              </form>
              <p id="catalogPriceChangesStatus" class="muted-small" role="status"></p>
              <div id="catalogPriceChangesList" class="catalog-price-changes-list"></div>
              <button id="catalogPriceChangesMore" type="button" class="btn btn-secondary btn-icon" title="Показать ещё" aria-label="Показать ещё" hidden>${window.App.icons.svg("down")}</button>
            </section>
          <section id="itemCatalogPositionsView" class="panel hidden">
            <div class="table-search-row">
              <input id="itemCatalogSearchQ" class="table-search-input" type="search" placeholder="Поиск по источнику, бренду и позиции" />
              <div class="toolbar section-action-toolbar search-toolbar item-catalog-controls">
                <label class="item-catalog-brand-filter-field">
                  <span class="sr-only">Фильтр по бренду</span>
                  <select id="itemCatalogBrandFilter" aria-label="Фильтр позиций по бренду">
                    <option value="all">Все бренды</option>
                    <option value="unassigned">Без бренда</option>
                  </select>
                </label>
                <div class="segmented" id="itemCatalogSortTabs" role="tablist" aria-label="Сортировка каталога позиций">
                  <button class="segmented-btn active" data-item-sort="usage" type="button">Частота</button>
                  <button class="segmented-btn" data-item-sort="recent" type="button">Недавние</button>
                  <button class="segmented-btn" data-item-sort="name" type="button">Имя</button>
                </div>
                <button id="itemCatalogCollapseAllBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Свернуть все" aria-label="Свернуть все">${window.App.icons.svg("collapse")}</button>
                <button id="itemCatalogExpandAllBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Развернуть все" aria-label="Развернуть все">${window.App.icons.svg("expand")}</button>
                <button id="resetItemCatalogWidthsBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Сбросить ширину колонок" aria-label="Сбросить ширину колонок">${window.App.icons.svg("width")}</button>
                <button id="deleteAllItemTemplatesBtn" class="btn-icon btn btn-danger" type="button" title="Удалить все позиции" aria-label="Удалить все позиции">${window.App.icons.svg("trash")}</button>
              </div>
            </div>
            <div id="itemCatalogKpiGrid" class="analytics-kpi-grid section-kpi-grid catalog-compact-kpis" aria-label="Итоги каталога позиций"></div>
            <div id="itemCatalogBulkBar" class="bulk-bar item-catalog-brand-bulk-bar hidden" aria-live="polite">
              <strong id="itemCatalogSelectedCount">Выбрано: 0</strong>
              <label class="item-catalog-brand-bulk-field">
                <span>Назначить бренд</span>
                <select id="itemCatalogBulkBrand" aria-label="Бренд для выбранных позиций">
                  <option value="">Без бренда</option>
                </select>
              </label>
              <button id="assignSelectedItemBrandBtn" class="btn-icon btn btn-primary btn-xs" type="button" title="Назначить бренд" aria-label="Назначить бренд">${window.App.icons.svg("save")}</button>
              <button id="clearSelectedItemCatalogBtn" class="btn-icon btn btn-ghost btn-xs" type="button" title="Снять выбор" aria-label="Снять выбор">${window.App.icons.svg("close")}</button>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table item-catalog-table">
                <colgroup><col /><col /><col /><col /><col /><col /><col /></colgroup>
                <thead>
                  <tr>
                    <th><input id="itemCatalogSelectAll" type="checkbox" aria-label="Выбрать все видимые позиции" /></th>
                    <th>Источник</th>
                    <th>Бренд</th>
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
          <section id="itemBrandsView" class="panel hidden">
            <div class="item-brands-heading">
              <div>
                <h3>Бренды</h3>

              </div>
              <button id="addItemBrandBtn" class="btn-icon btn btn-primary" type="button" title="Добавить бренд" aria-label="Добавить бренд">${window.App.icons.svg("plus")}</button>
            </div>
            <div id="itemBrandsKpiGrid" class="analytics-kpi-grid section-kpi-grid catalog-compact-kpis" aria-label="Итоги по брендам"></div>
            <div class="item-brands-toolbar">
              <input id="itemBrandsSearchQ" class="table-search-input" type="search" placeholder="Поиск по бренду или позиции" />
              <div class="toolbar section-action-toolbar search-toolbar">
                <button id="refreshItemBrandsBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Обновить бренды" aria-label="Обновить бренды">${window.App.icons.svg("refresh")}</button>
                <button id="resetItemBrandWidthsBtn" class="btn-icon btn btn-secondary btn-xs" type="button" title="Сбросить ширину колонок" aria-label="Сбросить ширину колонок">${window.App.icons.svg("width")}</button>
              </div>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table item-brands-table">
                <colgroup><col /><col /><col /><col /><col /><col /></colgroup>
                <thead>
                  <tr>
                    <th>Бренд</th>
                    <th>Позиций</th>
                    <th>Покупок</th>
                    <th>Потрачено</th>
                    <th>Последняя покупка</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="itemBrandsBody"></tbody>
              </table>
            </div>
          </section>
        </section>

        <section id="settingsSection" class="section-block hidden">
          <section class="panel settings-workspace">
            <nav id="settingsViewTabs" class="segmented settings-navigation" aria-label="Разделы настроек">
              <button class="segmented-btn active" type="button" data-settings-view="general" aria-controls="settings-general" aria-pressed="true">Общие</button>
              <button class="segmented-btn" type="button" data-settings-view="dashboard" aria-controls="settings-dashboard" aria-pressed="false">Главная</button>
              <button class="segmented-btn" type="button" data-settings-view="currency" aria-controls="settings-currency" aria-pressed="false">Валюты и банки</button>
              <button class="segmented-btn" type="button" data-settings-view="notifications" aria-controls="settings-notifications" aria-pressed="false">Напоминания</button>
              <button class="segmented-btn" type="button" data-settings-view="alerts" aria-controls="settings-alerts" aria-pressed="false">Пороги курсов</button>
              <button class="segmented-btn" type="button" data-settings-view="data" aria-controls="settings-data" aria-pressed="false">Данные</button>
            </nav>
            <form id="settingsForm" class="settings-form">
              <div id="settings-general" data-settings-panel="general" class="settings-page">
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
<section class="settings-block"><h3>Отображение сумм</h3>
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
                </section>
                <section class="settings-block">
                  <h3>Интерфейс</h3>
                <div class="settings-scale-row">
                  <label class="field">
                    <span>Масштаб интерфейса: <strong id="uiScaleValue">100%</strong></span>
                    <input id="uiScaleRange" type="range" min="85" max="115" step="1" value="100" />
                  </label>
                  <button id="resetUiScaleBtn" class="btn btn-secondary btn-xs" type="button">Сбросить 100%</button>
                </div>
                </section>
              </div>
              <div id="settings-dashboard" data-settings-panel="dashboard" class="settings-page hidden">
                <section class="settings-block">
                  <h3>Блоки главной</h3>
                <label class="settings-switch-row">
                  <input id="showDashboardAnalyticsToggle" type="checkbox" checked />
                  <span>Структура расходов</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardOperationsToggle" type="checkbox" checked />
                  <span>Планы</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardDebtsToggle" type="checkbox" checked />
                  <span>Долги</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardCurrencyToggle" type="checkbox" checked />
                  <span>Валюта</span>
                </label>
                <label class="field">
                  <span>Планов на главной</span>
                  <div class="settings-picker-field">
                    <select id="dashboardOperationsLimitSelect">
                      <option value="5">5</option>
                      <option value="8">8</option>
                      <option value="12">12</option>
                    </select>
                    <button id="dashboardOperationsLimitPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                  </div>
                </label>
                </section>
              </div>
              <div id="settings-currency" data-settings-panel="currency" class="settings-page hidden">
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
                <section class="settings-block">
                  <h3>Банковские курсы</h3>
                  <p class="muted-small">Для сводки курсов и уведомлений.</p>
                  <div id="bankRateBanksWrap" class="settings-grid-2">
                    ${[
                      ["priorbank", "Приорбанк · онлайн"],
                      ["technobank", "Технобанк · наличные"],
                      ["bsb", "БСБ Банк · наличные"],
                      ["sber", "Сбер Банк · наличные"],
                    ].map(([code, label]) => `
                      <label class="settings-switch-row">
                        <input name="bankRateBank" type="checkbox" value="${code}" checked />
                        <span>${label}</span>
                      </label>
                    `).join("")}
                  </div>
                </section>
              </div>
              <div id="settings-notifications" data-settings-panel="notifications" class="settings-page hidden">
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
                  <span>Ежедневные курсы в Telegram</span>
                </label>
                <label class="field">
                  <span>Время уведомления по курсам</span>
                  <input id="currencyDigestTimeInput" type="time" value="10:00" />
                </label>
                <label class="settings-switch-row">
                  <input id="currencyDigestChartToggle" type="checkbox" checked />
                  <span>Добавлять график курсов за последние 7 дней</span>
                </label>
                </section>
              </div>
              <div id="settings-alerts" data-settings-panel="alerts" class="settings-page hidden">
                <section class="settings-block">
                  <h3>Пороги курсов</h3>
                <div class="field">
                  <span>Официальные курсы НБРБ</span>
                  <div id="currencyAlertsSettings" class="settings-alerts-grid">
                    ${["USD", "EUR", "RUB", "CNY", "PLN"].map((currency) => `
                      <div class="settings-alert-row" data-currency-alert-row="${currency}">
                        <div class="settings-alert-row-head">
                          <strong>${currency}</strong>
                          <span class="muted-small">${currency === "RUB" ? "за 100 RUB" : "за 1 единицу"}</span>
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
                <div class="field">
                  <div class="settings-alert-section-head">
                    <div>
                      <span>Курсы банков</span>
                      <p class="muted-small">Покупка — банк покупает у вас; продажа — продаёт вам.</p>
                    </div>
                    <button id="addBankCurrencyAlertBtn" class="btn btn-secondary btn-xs" type="button">Добавить алерт</button>
                  </div>
                  <div id="bankCurrencyAlertsList" class="settings-alerts-grid"></div>
                </div>
                </section>
              </div>
              <div class="settings-actions"><button id="saveSettingsBtn" class="btn btn-primary btn-icon" type="submit" aria-label="Сохранить настройки" title="Сохранить настройки">${window.App.icons.svg("save")}</button></div>
            </form>
              <div id="settings-data" data-settings-panel="data" class="settings-page hidden">
            <section class="panel danger-zone">
              <h3>Удаление аккаунта</h3>
              <p class="subtitle">Удаление аккаунта удалит все операции, долги, категории и настройки без возможности восстановления.</p>
              <div class="danger-zone-actions">
                <input id="deleteMePhrase" type="text" aria-label="Подтверждение удаления аккаунта" placeholder="Введите УДАЛИТЬ" />
                <button id="deleteMeBtn" class="btn btn-danger" type="button">Удалить аккаунт</button>
              </div>
            </section>
            </div>
          </section>
        </section>

        <section id="adminSection" class="section-block hidden">
          <nav id="adminViewTabs" class="segmented" aria-label="Разделы администрирования"><button class="segmented-btn active" type="button" data-admin-view="users" aria-controls="adminUsersPanel" aria-pressed="true">Доступ</button><button class="segmented-btn" type="button" data-admin-view="diagnostics" aria-controls="adminDiagnosticsPanel" aria-pressed="false">Диагностика курсов</button></nav>
          <section id="adminUsersPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Управление доступом</h3>
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
          <section id="adminDiagnosticsPanel" class="panel hidden">
            <div class="panel-head row between">
              <div>
                <h3>Диагностика курсов</h3>
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
                    <th>Рассылка</th>
                    <th>Пороги</th>
                    <th>Последний курс</th>
                    <th>Устарели</th>
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
