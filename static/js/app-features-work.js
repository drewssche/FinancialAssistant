(() => {
  const { core } = window.App;
  const nodes = {};
  let anchor = new Date();
  anchor = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  let snapshot = null;
  let statistics = null;
  let statisticsPeriod = "month";
  let statisticsAnchor = new Date(anchor);
  let workPickerYear = anchor.getFullYear();
  let contracts = [];
  let companies = [];
  let paymentHistory = [];
  let paymentCandidates = [];
  let paymentCandidateRole = "salary";
  let paymentCandidatesRequestId = 0;
  let paymentCandidatesSearchTimer = null;
  let selectedCompanyIndex = 0;
  let editingContractId = null;
  let liveTimerId = null;
  let liveBaseline = null;
  let lastLiveMinute = null;
  let selectedPaymentOperationId = null;
  let activityRefreshTimer = null;
  let observedLocalDate = localTodayIso();
  let midnightReloadPending = false;
  let workLoadPromise = null;
  let activeWorkLoadKey = "";
  let queuedWorkLoad = null;
  let bound = false;

  const monthFormatter = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" });
  const dayFormatter = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric", weekday: "long" });
  const PAID_ABSENCE_STATUSES = new Set(["vacation", "sick_paid", "company_day_off"]);

  function byId(id) { return document.getElementById(id); }
  function escape(value) { return core.escapeHtml ? core.escapeHtml(String(value ?? "")) : String(value ?? ""); }
  function authOptions(extra = {}) { return { ...extra, headers: { ...core.authHeaders(), ...(extra.headers || {}) } }; }
  function formatHours(value) { return Number(value || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 }); }
  function formatMoney(value, currency = "BYN") {
    if (value == null || value === "") return "";
    return core.formatMoney
      ? core.formatMoney(Number(value), { currency: String(currency || "BYN").toUpperCase() })
      : `${Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ${String(currency || "BYN").toUpperCase()}`;
  }
  function formatDate(iso) {
    const [year, month, day] = String(iso).split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString("ru-RU");
  }
  function localTodayIso() {
    return localDateIso(new Date());
  }
  function localDateIso(now) {
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  }
  function getPickerUtils() { return window.App.getRuntimeModule?.("picker-utils") || window.App.pickerUtils || {}; }
  function monthValue(value) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`; }
  function formatMonthLabel(value) { return monthFormatter.format(value).replace(/^./, (char) => char.toUpperCase()); }
  function paymentForecastAmount(item) { return item?.forecast_amount ?? item?.planned_amount ?? item?.amount ?? null; }
  function paymentForecastCurrency(item) { return item?.forecast_currency || item?.currency || item?.base_currency || "BYN"; }
  function paymentForecastBaseAmount(item) { return item?.forecast_base_amount ?? paymentForecastAmount(item); }
  function paymentForecastBaseCurrency(item) {
    return item?.forecast_base_amount != null
      ? item?.forecast_base_currency || paymentForecastCurrency(item)
      : paymentForecastCurrency(item);
  }
  function paymentForecastVisible(item) { return item?.forecast_visible === true; }
  function paymentOperationId(item) { return Number(item?.operation_id || 0); }
  function paymentOperationDate(item) { return item?.operation_date || item?.effective_date || item?.date || null; }
  function paymentOperationAmount(item) { return item?.amount ?? item?.original_amount ?? item?.base_amount ?? null; }
  function paymentOperationCurrency(item) { return item?.currency || item?.base_currency || "BYN"; }
  function paymentOperationBaseAmount(item) { return item?.base_amount ?? paymentOperationAmount(item); }
  function paymentOperationBaseCurrency(item) { return item?.base_currency || paymentOperationCurrency(item); }
  function paymentRoleLabel(role) { return role === "advance" ? "Аванс" : "Основная часть"; }
  function formatOperationCount(value) {
    const count = Math.max(0, Number(value || 0));
    const mod100 = count % 100;
    const mod10 = count % 10;
    const suffix = mod100 >= 11 && mod100 <= 14
      ? "операций"
      : mod10 === 1
        ? "операция"
        : mod10 >= 2 && mod10 <= 4
          ? "операции"
          : "операций";
    return `${count} ${suffix}`;
  }
  function paymentSourceLabel(source) {
    if (source === "manual") return "Связано вручную";
    if (source === "category_match") return "Определено по категории";
    return "Из подтверждения плана";
  }
  function embeddedPaymentOperations(item) {
    const rows = Array.isArray(item?.actual_operations)
      ? item.actual_operations
      : Array.isArray(item?.operations)
        ? item.operations
        : item?.actual_operation
          ? [item.actual_operation]
          : [];
    return rows.map((row) => ({ ...row, role: row.role || item.role, label: row.label || item.label, plan_id: row.plan_id || item.plan_id }));
  }
  function exactDatePayrollOperations(item) {
    const effectiveDate = String(item?.effective_date || "");
    if (!effectiveDate) return [];
    const seen = new Set();
    return (Array.isArray(snapshot?.payroll_operations) ? snapshot.payroll_operations : []).filter((row) => {
      const operationId = paymentOperationId(row);
      if (row.is_deleted || !(operationId > 0) || paymentOperationDate(row) !== effectiveDate || seen.has(operationId)) return false;
      seen.add(operationId);
      return true;
    });
  }
  function hasUniquePaymentEffectiveDate(item) {
    const effectiveDate = String(item?.effective_date || "");
    return Boolean(effectiveDate) && (snapshot?.payments || []).filter((row) => row.effective_date === effectiveDate).length === 1;
  }
  function categoryPaymentHeadline(rows) {
    const currencies = [...new Set(rows.map(paymentOperationCurrency))];
    if (currencies.length !== 1) return `Получено по категории · ${formatOperationCount(rows.length)}`;
    const total = rows.reduce((sum, row) => sum + Number(paymentOperationAmount(row) || 0), 0);
    return `Получено по категории · ${formatMoney(total, currencies[0])} · ${formatOperationCount(rows.length)}`;
  }
  function allActualPayments() {
    const rows = [
      ...paymentHistory,
      ...(snapshot?.payments || []).flatMap(embeddedPaymentOperations),
      ...(Array.isArray(snapshot?.payroll_operations) ? snapshot.payroll_operations : []),
    ];
    const seen = new Set();
    return rows.filter((row) => {
      const operationId = paymentOperationId(row);
      const linkId = Number(row.link_id || 0);
      const key = operationId > 0
        ? `operation:${operationId}`
        : linkId > 0
          ? `link:${linkId}`
          : `${row.role || "payment"}:${paymentOperationDate(row) || ""}:${paymentOperationAmount(row) || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  function parseClockMinutes(value, fallback) {
    const match = /^(\d{1,2}):(\d{2})/.exec(String(value || fallback || ""));
    if (!match) return 0;
    return Math.min(24 * 60, Math.max(0, Number(match[1]) * 60 + Number(match[2])));
  }
  function liveHoursForDay(day, now = new Date()) {
    const profile = snapshot?.profile || {};
    const start = parseClockMinutes(profile.workday_start_time, "09:00");
    const end = parseClockMinutes(profile.workday_end_time, "18:00");
    const lunchStart = parseClockMinutes(profile.lunch_start_time, "13:00");
    const lunchEnd = parseClockMinutes(profile.lunch_end_time, "14:00");
    const current = now.getHours() * 60 + now.getMinutes();
    const elapsed = Math.max(0, Math.min(current, end) - start);
    const breakOverlap = lunchEnd > lunchStart
      ? Math.max(0, Math.min(current, end, lunchEnd) - Math.max(start, lunchStart))
      : 0;
    const planned = Math.max(0, Number(day?.planned_hours || profile.standard_hours_per_day || 0));
    return Math.min(planned, Math.max(0, elapsed - breakOverlap) / 60);
  }
  function formatLiveHours(value) {
    const minutes = Math.max(0, Math.round(Number(value || 0) * 60));
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    return rest ? `${hours} ч ${rest} мин` : `${hours} ч`;
  }
  function sameHours(left, right) { return Math.abs(Number(left || 0) - Number(right || 0)) < 0.005; }
  function workHoursChip(kind, label, value) {
    return `<span class="work-hours-chip work-hours-chip-${kind}">${label} · ${formatHours(value)} ч</span>`;
  }
  function renderDayHourChips(item, isToday) {
    const plannedHours = Number(item.planned_hours || 0);
    const actualHours = Number(item.actual_hours || 0);
    const creditedHours = Number(item.credited_hours || 0);

    if (PAID_ABSENCE_STATUSES.has(String(item.status || ""))) {
      let hours = "";
      if (actualHours > 0) {
        hours += workHoursChip("fact", "Факт", actualHours);
      }
      if (actualHours <= 0 || !sameHours(actualHours, creditedHours)) {
        hours += workHoursChip("credited", item.is_future ? "К оплате" : "Зачтено", creditedHours);
      }
      if (plannedHours > 0 && !sameHours(plannedHours, creditedHours) && !sameHours(plannedHours, actualHours)) {
        hours += workHoursChip("plan", "План", plannedHours);
      }
      return hours;
    }
    if (item.is_live && plannedHours > 0) {
      let hours = `<span class="work-hours-chip work-hours-chip-live">Сейчас · ${escape(formatLiveHours(actualHours))}</span>`;
      if (actualHours < plannedHours) hours += workHoursChip("plan", "План", plannedHours);
      return hours;
    }
    if (isToday && !item.is_completed && actualHours <= 0 && plannedHours > 0) {
      return workHoursChip("plan", "План", plannedHours);
    }
    if (item.is_future && plannedHours > 0) {
      return workHoursChip("forecast", "Прогноз", plannedHours);
    }
    if (!item.is_future && (plannedHours > 0 || actualHours > 0)) {
      const plan = !sameHours(plannedHours, actualHours)
        ? workHoursChip("plan", "План", plannedHours)
        : "";
      return `${workHoursChip("fact", "Факт", actualHours)}${plan}`;
    }
    return "";
  }
  function isoMonth(value) { return String(value || "").slice(0, 7); }

  function collectNodes() {
    [
      "workMonthTrigger", "workMonthPopover", "workYearOptions", "workMonthOptions",
      "workPrevMonthBtn", "workNextMonthBtn", "workTodayBtn", "workSummaryGrid",
      "workMoneySummaryGrid", "workPaymentsGrid", "workCalendarGrid", "workViewTabs", "workTimesheetView", "workSettingsForm",
      "workCompaniesView", "workCompaniesGrid", "workCompanyDetails", "workContractsView",
      "workDayForm", "workDayEditorTitle", "workDayDate", "workDayStatus",
      "workDayDateTo",
      "workDayPlanned", "workDayActual", "workDayCredited", "workDayNote", "closeWorkDayEditorBtn",
      "resetWorkDayBtn", "workCompany", "workPosition", "workStartDate", "workStandardHours",
      "workCompanyOptions",
      "workWeekdayPicker", "workSalaryPlan", "workSalaryDay", "workAdvancePlan", "workAdvanceDay",
      "workContractForm", "workContractFrom", "workContractTo", "workContractCompany",
      "workContractPosition", "workContractSalary", "workContractCurrency", "workContractNote",
      "workContractFormHeading", "workContractFormSubtitle", "workContractSubmitBtn",
      "cancelWorkContractEditBtn", "workContractsList",
      "workStatisticsView", "workStatisticsPeriodTabs", "workStatisticsPrevBtn", "workStatisticsNextBtn",
      "workStatisticsCurrentBtn", "workStatisticsPeriodLabel", "workStatisticsCustomForm",
      "workStatisticsDateFrom", "workStatisticsDateTo", "workStatisticsKpi", "workStatisticsProgressLabel",
      "workStatisticsProgressBar", "workStatisticsMonths",
      "workDayStartTime", "workDayEndTime", "workLunchStartTime", "workLunchEndTime",
      "workActualPaymentsList",
      "workPaymentLinkToggle", "workPaymentLinkPanel", "workPaymentLinkRole",
      "workPaymentCandidateDateFrom", "workPaymentCandidateDateTo", "workPaymentCandidateSearch",
      "workPaymentCandidateForm", "workPaymentCandidatesList", "workPaymentLinkClose",
      "workSection",
    ].forEach((id) => { nodes[id] = byId(id); });
  }

  function renderSummary() {
    const summary = snapshot?.summary || {};
    const cards = [
      ["План месяца", `${formatHours(summary.planned_hours)} ч`, `${summary.planned_days || 0} раб. дн.`],
      ["Отработано", `${formatHours(summary.actual_hours)} ч`, `${summary.completed_days || 0} дней`],
      ["К оплате", `${formatHours(summary.credited_hours)} ч`, "зачтённые часы"],
      ["Исключения", String(summary.override_days || 0), `отпуск: ${summary.vacation_days || 0} · сикдей: ${summary.sick_days || 0}`],
    ];
    nodes.workSummaryGrid.innerHTML = cards.map(([label, value, meta]) => `
      <article class="analytics-kpi-card analytics-kpi-neutral">
        <div class="muted-small">${escape(label)}</div><strong>${escape(value)}</strong><div class="muted-small">${escape(meta)}</div>
      </article>`).join("");
  }

  function monthSnapshotPaymentOperations() {
    const month = `${Number(snapshot?.year || anchor.getFullYear())}-${String(Number(snapshot?.month || anchor.getMonth() + 1)).padStart(2, "0")}`;
    const rows = [
      ...(snapshot?.payments || []).flatMap(embeddedPaymentOperations),
      ...(Array.isArray(snapshot?.payroll_operations) ? snapshot.payroll_operations : []),
    ];
    const seenOperationIds = new Set();
    const seenLinkIds = new Set();
    return rows.filter((row) => {
      if (row.is_deleted || isoMonth(paymentOperationDate(row)) !== month) return false;
      const operationId = paymentOperationId(row);
      const linkId = Number(row.link_id || 0);
      if (!(operationId > 0) && !(linkId > 0)) return false;
      if ((operationId > 0 && seenOperationIds.has(operationId)) || (linkId > 0 && seenLinkIds.has(linkId))) return false;
      if (operationId > 0) seenOperationIds.add(operationId);
      if (linkId > 0) seenLinkIds.add(linkId);
      return true;
    });
  }

  function monthVisibleForecasts() {
    const month = `${Number(snapshot?.year || anchor.getFullYear())}-${String(Number(snapshot?.month || anchor.getMonth() + 1)).padStart(2, "0")}`;
    const seen = new Set();
    return (snapshot?.payments || []).filter((item) => {
      if (!paymentForecastVisible(item) || isoMonth(item.effective_date) !== month) return false;
      const key = `${Number(item.plan_id || 0)}:${item.role || "payment"}:${item.effective_date || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function groupedMoney(rows, amountOf, currencyOf) {
    const totals = new Map();
    rows.forEach((row) => {
      const rawAmount = amountOf(row);
      if (rawAmount == null || rawAmount === "") return;
      const amount = Number(rawAmount);
      if (!Number.isFinite(amount)) return;
      const currency = String(currencyOf(row) || "BYN").toUpperCase();
      totals.set(currency, (totals.get(currency) || 0) + amount);
    });
    return totals;
  }

  function renderMoneyValues(group) {
    const entries = [...group.entries()].sort(([left], [right]) => {
      if (left === "BYN") return -1;
      if (right === "BYN") return 1;
      return left.localeCompare(right);
    });
    if (!entries.length) return '<strong class="work-money-empty">—</strong>';
    return entries.map(([currency, amount]) => `<strong>${escape(formatMoney(amount, currency))}</strong>`).join("");
  }

  function moneyGroupFromTotals(rows, amountKey = "amount", { includeZero = true } = {}) {
    const totals = new Map();
    (Array.isArray(rows) ? rows : []).forEach((row) => {
      const amount = Number(row?.[amountKey]);
      if (!Number.isFinite(amount) || (!includeZero && Math.abs(amount) < 0.005)) return;
      const currency = String(row?.currency || "BYN").toUpperCase();
      totals.set(currency, (totals.get(currency) || 0) + amount);
    });
    return totals;
  }

  function inlineMoneyValues(group) {
    const entries = [...group.entries()].sort(([left], [right]) => {
      if (left === "BYN") return -1;
      if (right === "BYN") return 1;
      return left.localeCompare(right);
    });
    if (!entries.length) return "—";
    return entries.map(([currency, amount]) => escape(formatMoney(amount, currency))).join(" · ");
  }

  function salaryCycleComponentActuals(component) {
    const explicit = moneyGroupFromTotals(component?.actual_totals);
    return explicit.size
      ? explicit
      : groupedMoney(activeSalaryCycleOperations(component), paymentOperationBaseAmount, paymentOperationBaseCurrency);
  }

  function activeSalaryCycleOperations(component) {
    return (Array.isArray(component?.actual_operations) ? component.actual_operations : []).filter((row) => !row?.is_deleted);
  }

  function salaryCycleComponentForecast(component) {
    const amount = component?.forecast_base_amount ?? component?.forecast_amount;
    if (amount == null || amount === "") return new Map();
    const hasBaseAmount = component?.forecast_base_amount != null;
    return groupedMoney(
      [component],
      (row) => row.forecast_base_amount ?? row.forecast_amount,
      (row) => hasBaseAmount
        ? row.forecast_base_currency || row.forecast_currency || "BYN"
        : row.forecast_currency || "BYN",
    );
  }

  function renderSalaryCycleComponent(component) {
    const role = String(component?.role || "extras");
    const label = component?.label || (role === "advance" ? "Аванс" : role === "salary" ? "Основная часть" : "Доплаты");
    const activeOperations = activeSalaryCycleOperations(component);
    const actuals = role === "extras"
      ? groupedMoney(activeOperations, paymentOperationBaseAmount, paymentOperationBaseCurrency)
      : salaryCycleComponentActuals(component);
    const forecast = role === "extras" ? new Map() : salaryCycleComponentForecast(component);
    const date = component?.effective_date ? formatDate(component.effective_date) : "";
    const nominalDate = component?.nominal_date ? formatDate(component.nominal_date) : "";
    const dateLabel = date
      ? component?.shifted && nominalDate
        ? `${date} · перенесено с ${nominalDate}`
        : date
      : "";
    const operationDates = [...new Set(activeOperations.map(paymentOperationDate).filter(Boolean))];
    const actualDateLabel = role !== "extras" && operationDates.length === 1 && operationDates[0] !== component?.effective_date
      ? ` · факт ${formatDate(operationDates[0])}`
      : "";
    const states = [];
    if (actuals.size) {
      const operationCount = activeOperations.length ? ` · ${escape(formatOperationCount(activeOperations.length))}` : "";
      states.push(`<span class="work-salary-cycle-state is-actual">Получено${escape(actualDateLabel)} · ${inlineMoneyValues(actuals)}${operationCount}</span>`);
    }
    if (forecast.size) {
      states.push(`<span class="work-salary-cycle-state is-forecast">Прогноз · ${inlineMoneyValues(forecast)}</span>`);
    }
    if (!states.length) {
      states.push(`<span class="work-salary-cycle-state is-missing">${role === "extras" ? "Доплат нет" : "Выплата не найдена"}</span>`);
    }
    return `
      <div class="work-salary-cycle-component work-salary-cycle-component-${escape(role)}">
        <div class="work-salary-cycle-component-head">
          <strong>${escape(label)}</strong>
          ${dateLabel ? `<span>${escape(dateLabel)}</span>` : ""}
        </div>
        <div class="work-salary-cycle-component-values">${states.join("")}</div>
      </div>`;
  }

  function renderSalaryCycleCard() {
    const cycle = snapshot?.salary_cycle;
    if (!cycle || !Array.isArray(cycle.totals)) return "";
    const actual = moneyGroupFromTotals(cycle.totals, "actual_amount", { includeZero: false });
    const forecast = moneyGroupFromTotals(cycle.totals, "forecast_amount", { includeZero: false });
    const expected = moneyGroupFromTotals(cycle.totals, "expected_amount");
    const componentsByRole = new Map((cycle.components || []).map((component) => [component.role, component]));
    const components = [
      componentsByRole.get("advance") || { role: "advance", label: "Аванс" },
      componentsByRole.get("salary") || { role: "salary", label: "Основная часть" },
      { role: "extras", label: "Доплаты", actual_operations: cycle.extras || [] },
    ];
    const windowLabel = cycle.window_from_exclusive && cycle.window_to_inclusive
      ? `Выплаты после ${formatDate(cycle.window_from_exclusive)} и по ${formatDate(cycle.window_to_inclusive)} включительно`
      : "Аванс прошлого месяца и основная часть текущего";
    const explanation = "В цикл входят выплаты после основной части прошлого месяца и до основной части текущего месяца включительно.";
    const summary = [];
    if (actual.size) summary.push(`<span class="work-salary-cycle-summary-value is-actual">Получено · ${inlineMoneyValues(actual)}</span>`);
    if (forecast.size) summary.push(`<span class="work-salary-cycle-summary-value is-forecast">Ещё ожидается · ${inlineMoneyValues(forecast)}</span>`);
    return `
      <article class="analytics-kpi-card work-money-kpi-card work-salary-cycle-card" title="${escape(explanation)}">
        <div class="work-salary-cycle-head">
          <div class="work-salary-cycle-title">
            <span class="muted-small">Зарплатный цикл</span>
            <strong>${escape(cycle.label || "Зарплата за предыдущий месяц")}</strong>
            <span class="muted-small">${escape(windowLabel)}</span>
          </div>
          <div class="work-salary-cycle-total">
            <span class="muted-small">Итого цикла</span>
            <div class="work-money-kpi-values">${renderMoneyValues(expected)}</div>
          </div>
        </div>
        ${summary.length ? `<div class="work-salary-cycle-summary">${summary.join("")}</div>` : ""}
        <div class="work-salary-cycle-components">${components.map(renderSalaryCycleComponent).join("")}</div>
      </article>`;
  }

  function formatPlanPaymentCount(value) {
    const count = Math.max(0, Number(value || 0));
    const mod100 = count % 100;
    const mod10 = count % 10;
    const paymentWord = mod100 >= 11 && mod100 <= 14 ? "выплат" : mod10 === 1 ? "выплата" : mod10 >= 2 && mod10 <= 4 ? "выплаты" : "выплат";
    return `${count} ${paymentWord} по ${count === 1 ? "плану" : "планам"}`;
  }

  function renderMoneySummary() {
    if (!nodes.workMoneySummaryGrid) return;
    const actuals = monthSnapshotPaymentOperations();
    const forecasts = monthVisibleForecasts();
    const actualMoney = groupedMoney(actuals, paymentOperationBaseAmount, paymentOperationBaseCurrency);
    const forecastMoney = groupedMoney(forecasts, paymentForecastBaseAmount, paymentForecastBaseCurrency);
    const cards = [
      ["Получено за месяц", actualMoney, formatOperationCount(actuals.length), "analytics-kpi-positive work-money-kpi-actual"],
      ["Ещё ожидается", forecastMoney, formatPlanPaymentCount(forecasts.length), "analytics-kpi-neutral work-money-kpi-forecast"],
    ];
    nodes.workMoneySummaryGrid.innerHTML = cards.map(([label, values, meta, className]) => `
      <article class="analytics-kpi-card work-money-kpi-card ${className}">
        <div class="muted-small">${escape(label)}</div>
        <div class="work-money-kpi-values">${renderMoneyValues(values)}</div>
        <div class="muted-small">${escape(meta)}</div>
      </article>`).join("") + renderSalaryCycleCard();
  }

  function renderWorkPeriodPicker() {
    nodes.workMonthTrigger.textContent = formatMonthLabel(anchor);
    const currentYear = new Date().getFullYear();
    const years = Array.from(new Set([
      currentYear,
      ...Array.from({ length: 9 }, (_, index) => workPickerYear - 4 + index),
    ])).sort((left, right) => right - left);
    nodes.workYearOptions.innerHTML = years.map((year) => `
      <button class="btn btn-secondary settings-picker-option ${workPickerYear === year ? "active" : ""}" type="button" data-work-picker-year="${year}">
        ${year === currentYear ? `Текущий · ${year}` : year}
      </button>
    `).join("");
    nodes.workMonthOptions.innerHTML = Array.from({ length: 12 }, (_, monthIndex) => {
      const value = new Date(workPickerYear, monthIndex, 1);
      const selected = anchor.getFullYear() === workPickerYear && anchor.getMonth() === monthIndex;
      const label = value.toLocaleDateString("ru-RU", { month: "long" }).replace(/^./, (char) => char.toUpperCase());
      return `<button class="btn btn-secondary settings-picker-option ${selected ? "active" : ""}" type="button" data-work-picker-month="${monthValue(value)}">${escape(label)}</button>`;
    }).join("");
  }

  function setWorkMonthPopoverOpen(open) {
    const pickerUtils = getPickerUtils();
    if (pickerUtils.setPopoverOpen) {
      pickerUtils.setPopoverOpen(nodes.workMonthPopover, open, { owners: [nodes.workMonthTrigger] });
    } else {
      nodes.workMonthPopover.classList.toggle("hidden", !open);
    }
    nodes.workMonthTrigger.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function renderPayments() {
    nodes.workPaymentsGrid.innerHTML = (snapshot?.payments || []).map((item) => {
      const forecastAmount = paymentForecastAmount(item);
      const actuals = embeddedPaymentOperations(item);
      const activeActuals = actuals.filter((row) => !row.is_deleted && paymentOperationId(row) > 0);
      const categoryActuals = activeActuals.length || !hasUniquePaymentEffectiveDate(item) ? [] : exactDatePayrollOperations(item);
      const displayedActuals = activeActuals.length ? actuals : categoryActuals.length ? categoryActuals : actuals;
      const hasActual = activeActuals.length > 0 || categoryActuals.length > 0;
      const showForecast = paymentForecastVisible(item);
      let headline = "Фактическая выплата не найдена";
      if (activeActuals.length === 1) {
        headline = `Факт · ${formatMoney(paymentOperationAmount(activeActuals[0]), paymentOperationCurrency(activeActuals[0]))}`;
      } else if (activeActuals.length > 1) {
        headline = `Факт · ${formatOperationCount(activeActuals.length)}`;
      } else if (categoryActuals.length) {
        headline = categoryPaymentHeadline(categoryActuals);
      } else if (showForecast) {
        headline = forecastAmount == null
          ? "Сумма прогноза не указана"
          : `Прогноз · ${formatMoney(forecastAmount, paymentForecastCurrency(item))}`;
      } else if (actuals.some((row) => row.is_deleted)) {
        headline = "Фактическая операция удалена";
      }
      return `
      <article class="work-payment-card ${item.shifted ? "is-shifted" : ""} ${hasActual ? "has-actual" : ""} ${!showForecast && !displayedActuals.length ? "is-missing" : ""}">
        <div class="work-payment-primary">
          <span class="muted-small">${escape(item.label)}</span>
          <strong>${escape(headline)}</strong>
          <span class="work-payment-date">${formatDate(item.effective_date)}</span>
        </div>
        <div class="work-payment-meta">
          ${item.shifted ? `<span>перенесено назад с ${formatDate(item.nominal_date)}</span>` : "<span>по номинальной дате</span>"}
          ${displayedActuals.map((row) => {
            const operationId = paymentOperationId(row);
            const actualMoney = formatMoney(paymentOperationAmount(row), paymentOperationCurrency(row));
            const isCategoryMatch = row.source === "category_match";
            const operationLabel = isCategoryMatch
              ? `${row.category_name || row.label || "Выплата"} · ${actualMoney} · ${formatDate(paymentOperationDate(row))}`
              : `Получено · ${actualMoney} · ${formatDate(paymentOperationDate(row))}`;
            const note = String(row.note || "").trim();
            const operationTitle = isCategoryMatch
              ? `${paymentSourceLabel(row.source)}${note ? ` · ${note}` : ""} · открыть операцию`
              : "Открыть фактическую операцию";
            return operationId > 0 && !row.is_deleted
              ? `<button class="work-payment-actual-link" type="button" data-work-operation-id="${operationId}" title="${escape(operationTitle)}">${escape(operationLabel)}</button>`
              : `<span class="work-payment-actual-deleted">Фактическая операция удалена</span>`;
          }).join("")}
          <button class="work-payment-plan-link" type="button" data-work-open-plan-picker="${escape(item.role)}">
            ${item.plan_id ? `План #${Number(item.plan_id)} · изменить` : "Выбрать план вручную"}
          </button>
        </div>
      </article>`;
    }).join("");
    restorePaymentOperationContext();
  }

  function renderCalendar() {
    const days = snapshot?.days || [];
    const paymentsByDate = new Map();
    (snapshot?.payments || []).forEach((item) => {
      if (!paymentForecastVisible(item)) return;
      const rows = paymentsByDate.get(item.effective_date) || [];
      rows.push(item);
      paymentsByDate.set(item.effective_date, rows);
    });
    const actualsByDate = new Map();
    allActualPayments().forEach((item) => {
      const operationDate = paymentOperationDate(item);
      if (!operationDate) return;
      const rows = actualsByDate.get(operationDate) || [];
      rows.push(item);
      actualsByDate.set(operationDate, rows);
    });
    const firstOffset = days.length ? Number(days[0].weekday || 0) : 0;
    const placeholders = Array.from({ length: firstOffset }, () => '<div class="work-day-cell work-day-empty"></div>').join("");
    nodes.workCalendarGrid.innerHTML = placeholders + days.map((item) => {
      const payments = paymentsByDate.get(item.date) || [];
      const actuals = actualsByDate.get(item.date) || [];
      const classes = ["work-day-cell", `status-${item.status}`];
      if (item.is_manual) classes.push("is-manual");
      if (item.is_future) classes.push("is-future");
      if (item.is_completed) classes.push("is-completed");
      if (item.is_future && Number(item.planned_hours || 0) > 0) classes.push("is-forecast");
      if (payments.length || actuals.length) classes.push("has-payment");
      const isToday = item.date === localTodayIso();
      if (isToday) classes.push("is-today");
      const hours = renderDayHourChips(item, isToday);
      const note = item.note
        ? `<span class="work-day-note" title="${escape(item.note)}">${escape(item.note)}</span>`
        : "";
      const forecastMarkup = payments.map((payment) => {
        const amount = paymentForecastAmount(payment);
        const money = amount == null ? "" : ` · ${formatMoney(amount, paymentForecastCurrency(payment))}`;
        return `<span class="work-day-payment work-day-payment-forecast">${escape(payment.label)} · прогноз${escape(money)}</span>`;
      }).join("");
      const actualMarkup = actuals.map((payment) => {
        const operationId = paymentOperationId(payment);
        const money = formatMoney(paymentOperationAmount(payment), paymentOperationCurrency(payment));
        const note = String(payment.note || "").trim();
        const label = `${payment.label || payment.category_name || "Выплата"} · получено${money ? ` ${money}` : ""}${note ? ` · ${note}` : ""}`;
        const source = paymentSourceLabel(payment.source);
        const title = `${source}${note ? ` · ${note}` : ""} · открыть фактическую операцию`;
        return operationId > 0 && !payment.is_deleted
          ? `<button class="work-day-payment work-day-payment-actual" type="button" data-work-operation-id="${operationId}" title="${escape(title)}">${escape(label)}</button>`
          : `<span class="work-day-payment work-day-payment-deleted">${escape(label)} · операция удалена</span>`;
      }).join("");
      return `<article class="${classes.join(" ")}" tabindex="0" data-work-date="${item.date}"${isToday ? ' aria-current="date"' : ""}>
        <span class="work-day-number">${Number(String(item.date).slice(-2))}</span>
        ${isToday ? '<span class="work-day-today-label">Сегодня</span>' : ""}
        <span class="work-day-hours">${hours}</span>
        <span class="work-day-status">${escape(item.status_label)}</span>
        ${note}
        ${(forecastMarkup || actualMarkup) ? `<span class="work-day-payments">${forecastMarkup}${actualMarkup}</span>` : ""}
        ${item.is_manual ? '<span class="work-day-manual-mark" title="Изменено вручную">●</span>' : ""}
      </article>`;
    }).join("");
    restorePaymentOperationContext();
  }

  function renderActualPayments() {
    if (!nodes.workActualPaymentsList) return;
    const rows = [...paymentHistory].sort((left, right) => (
      String(paymentOperationDate(right) || "").localeCompare(String(paymentOperationDate(left) || ""))
      || paymentOperationId(right) - paymentOperationId(left)
    ));
    nodes.workActualPaymentsList.innerHTML = rows.length ? rows.map((item) => {
      const operationId = paymentOperationId(item);
      const deleted = Boolean(item.is_deleted) || !(operationId > 0);
      const money = formatMoney(paymentOperationAmount(item), paymentOperationCurrency(item));
      const category = item.category_name ? `<span class="meta-chip meta-chip-neutral">${escape(item.category_name)}</span>` : "";
      const source = `<span class="meta-chip ${item.source === "manual" ? "meta-chip-info" : "meta-chip-neutral"}">${escape(paymentSourceLabel(item.source))}</span>`;
      const mainTag = operationId > 0 && !deleted ? "button" : "div";
      const mainAttributes = operationId > 0 && !deleted ? `type="button" data-work-operation-id="${operationId}" title="Открыть операцию"` : "";
      return `<article class="work-actual-payment-card ${deleted ? "is-deleted" : ""} ${operationId > 0 ? "is-openable" : ""}">
        <${mainTag} class="work-actual-payment-main work-actual-payment-open" ${mainAttributes}>
          <div class="work-actual-payment-title"><strong>${escape(item.label || paymentRoleLabel(item.role))}</strong>${category}${source}</div>
          <span>${paymentOperationDate(item) ? formatDate(paymentOperationDate(item)) : "Дата не указана"}${item.note ? ` · ${escape(item.note)}` : ""}</span>
        </${mainTag}>
        <div class="work-actual-payment-side">
          <strong>${escape(money || "Сумма не указана")}</strong>
          <span>${deleted ? "Операция удалена" : `Операция #${operationId}`}</span>
          ${item.link_id && !deleted ? `<button class="btn btn-secondary btn-xs work-payment-unlink-btn" type="button" data-work-unlink-payment="${Number(item.link_id)}">Отвязать</button>` : ""}
        </div>
      </article>`;
    }).join("") : '<div class="muted-small">Фактических выплат пока нет</div>';
    restorePaymentOperationContext();
  }

  function renderPaymentCandidates({ loading = false } = {}) {
    if (!nodes.workPaymentCandidatesList) return;
    if (loading) {
      nodes.workPaymentCandidatesList.innerHTML = '<div class="muted-small">Ищем доходные операции…</div>';
      return;
    }
    nodes.workPaymentCandidatesList.innerHTML = paymentCandidates.length ? paymentCandidates.map((item) => {
      const operationId = paymentOperationId(item);
      const linked = Boolean(item.is_linked);
      const category = item.category_name ? `<span class="meta-chip meta-chip-neutral">${escape(item.category_name)}</span>` : '<span class="muted-small">Без категории</span>';
      const baseMoney = item.base_currency && item.base_currency !== item.currency
        ? `<span class="muted-small">≈ ${escape(formatMoney(item.base_amount, item.base_currency))}</span>`
        : "";
      return `<article class="work-payment-candidate ${linked ? "is-linked" : ""}">
        <button class="work-payment-candidate-main" type="button" data-work-operation-id="${operationId}" title="Открыть операцию">
          <span class="work-payment-candidate-title"><strong>${escape(formatMoney(item.amount, item.currency))}</strong>${category}</span>
          <span class="muted-small">${formatDate(item.operation_date)}${item.note ? ` · ${escape(item.note)}` : ""}</span>
          ${baseMoney}
        </button>
        <div class="work-payment-candidate-actions">
          ${linked
            ? `<span class="work-payment-linked-chip">Связано · ${escape(paymentRoleLabel(item.linked_role))}</span>`
            : `<button class="btn btn-primary btn-xs" type="button" data-work-link-operation="${operationId}">Связать</button>`}
        </div>
      </article>`;
    }).join("") : '<div class="muted-small">За выбранный период подходящих доходных операций нет</div>';
  }

  function initializePaymentCandidateRange() {
    if (nodes.workPaymentCandidateDateFrom.value && nodes.workPaymentCandidateDateTo.value) return;
    const year = Number(snapshot?.year || anchor.getFullYear());
    const month = Number(snapshot?.month || anchor.getMonth() + 1);
    const lastDay = new Date(year, month, 0).getDate();
    nodes.workPaymentCandidateDateFrom.value = `${year}-${String(month).padStart(2, "0")}-01`;
    nodes.workPaymentCandidateDateTo.value = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
  }

  function syncPaymentLinkRole() {
    core.syncSegmentedActive?.(nodes.workPaymentLinkRole, "work-payment-link-role", paymentCandidateRole);
    nodes.workPaymentLinkRole.querySelectorAll("[data-work-payment-link-role]").forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.workPaymentLinkRole === paymentCandidateRole ? "true" : "false");
    });
  }

  function setPaymentLinkPanelOpen(open) {
    nodes.workPaymentLinkPanel.classList.toggle("hidden", !open);
    nodes.workPaymentLinkToggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (!open) {
      nodes.workPaymentLinkToggle.focus();
      return;
    }
    initializePaymentCandidateRange();
    syncPaymentLinkRole();
    loadPaymentCandidates().catch(handleError);
  }

  async function loadPaymentCandidates() {
    initializePaymentCandidateRange();
    const requestId = ++paymentCandidatesRequestId;
    renderPaymentCandidates({ loading: true });
    const params = new URLSearchParams({
      date_from: nodes.workPaymentCandidateDateFrom.value,
      date_to: nodes.workPaymentCandidateDateTo.value,
      limit: "100",
    });
    const query = nodes.workPaymentCandidateSearch.value.trim();
    if (query) params.set("q", query);
    const data = await core.requestJson(`/api/v1/work/payments/candidates?${params}`, authOptions());
    if (requestId !== paymentCandidatesRequestId) return;
    paymentCandidates = Array.isArray(data?.items) ? data.items : [];
    renderPaymentCandidates();
  }

  async function refreshPayrollAfterLinkMutation() {
    await loadWorkSection({ refresh: true });
    if (!nodes.workPaymentLinkPanel.classList.contains("hidden")) await loadPaymentCandidates();
  }

  async function linkPaymentOperation(operationId, button) {
    const resolvedId = Number(operationId || 0);
    if (!(resolvedId > 0)) return;
    button.disabled = true;
    const previousText = button.textContent;
    button.textContent = "Связываю…";
    try {
      selectedPaymentOperationId = resolvedId;
      await core.requestJson("/api/v1/work/payments/links", authOptions({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operation_id: resolvedId, role: paymentCandidateRole }),
      }));
      core.notify?.(`Операция связана как «${paymentRoleLabel(paymentCandidateRole)}»`, { type: "success" });
      await refreshPayrollAfterLinkMutation();
    } finally {
      if (button.isConnected) {
        button.disabled = false;
        button.textContent = previousText;
      }
    }
  }

  async function unlinkPayment(linkId, button) {
    const resolvedId = Number(linkId || 0);
    if (!(resolvedId > 0)) return;
    button.disabled = true;
    const previousText = button.textContent;
    button.textContent = "Отвязываю…";
    try {
      await core.requestJson(`/api/v1/work/payments/links/${resolvedId}`, authOptions({ method: "DELETE" }));
      core.notify?.("Связь удалена, сама операция сохранена", { type: "success" });
      await refreshPayrollAfterLinkMutation();
    } finally {
      if (button.isConnected) {
        button.disabled = false;
        button.textContent = previousText;
      }
    }
  }

  function restorePaymentOperationContext() {
    if (!(Number(selectedPaymentOperationId) > 0)) return;
    document.querySelectorAll(`[data-work-operation-id="${Number(selectedPaymentOperationId)}"]`).forEach((node) => {
      node.closest(".work-day-cell, .work-actual-payment-card, .work-payment-card")?.classList.add("work-payment-context-selected");
    });
  }

  function fillProfileForm() {
    const profile = snapshot?.profile || {};
    nodes.workCompany.value = profile.company || "";
    nodes.workPosition.value = profile.position || "";
    nodes.workStartDate.value = profile.employment_start_date || "";
    nodes.workStandardHours.value = Number(profile.standard_hours_per_day || 8);
    const selectedDays = new Set(profile.workweek_days || [0, 1, 2, 3, 4]);
    nodes.workWeekdayPicker.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      input.checked = selectedDays.has(Number(input.value));
    });
    nodes.workSalaryDay.value = Number(profile.salary_nominal_day || 5);
    nodes.workAdvanceDay.value = Number(profile.advance_nominal_day || 20);
    nodes.workSalaryPlan.value = profile.salary_plan_id || "";
    nodes.workAdvancePlan.value = profile.advance_plan_id || "";
    nodes.workDayStartTime.value = profile.workday_start_time || "09:00";
    nodes.workDayEndTime.value = profile.workday_end_time || "18:00";
    nodes.workLunchStartTime.value = profile.lunch_start_time || "13:00";
    nodes.workLunchEndTime.value = profile.lunch_end_time || "14:00";
  }

  function resetLiveBaseline() {
    const today = localTodayIso();
    const day = (snapshot?.days || []).find((item) => item.date === today);
    const canStartLater = Boolean(
      day
      && day.date === today
      && day.is_workday
      && day.hours_state === "forecast"
      && !day.is_completed,
    );
    if (!day || (!day.is_live && !canStartLater) || !day.is_workday || Number(day.planned_hours || 0) <= 0) {
      liveBaseline = null;
      return;
    }
    liveBaseline = {
      date: today,
      actualHours: Number(day.actual_hours || 0),
      creditedHours: Number(day.credited_hours || 0),
      completed: day.is_completed ? 1 : 0,
      summaryActualHours: Number(snapshot?.summary?.actual_hours || 0),
      summaryCreditedHours: Number(snapshot?.summary?.credited_hours || 0),
      summaryCompletedDays: Number(snapshot?.summary?.completed_days || 0),
    };
    lastLiveMinute = null;
  }

  function handleLocalDateRollover(now) {
    const currentDate = localDateIso(now);
    const previousDate = observedLocalDate;
    const didRollOver = Boolean(previousDate && currentDate !== previousDate);
    if (didRollOver) {
      observedLocalDate = currentDate;
      liveBaseline = null;
      lastLiveMinute = null;
      const snapshotMonth = snapshot
        ? `${Number(snapshot.year)}-${String(Number(snapshot.month)).padStart(2, "0")}`
        : "";
      if (snapshotMonth === isoMonth(previousDate)) {
        anchor = new Date(now.getFullYear(), now.getMonth(), 1);
        midnightReloadPending = true;
      }
    }
    if (!midnightReloadPending) return didRollOver;
    if (nodes.workSection?.classList.contains("hidden")) return true;
    loadWorkSection().catch(handleError);
    return true;
  }

  function updateLiveWorkday(now = new Date(), { force = false } = {}) {
    if (handleLocalDateRollover(now)) return;
    if (!liveBaseline || !snapshot?.summary) return;
    const minuteKey = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}-${now.getHours()}-${now.getMinutes()}`;
    if (!force && minuteKey === lastLiveMinute) return;
    lastLiveMinute = minuteKey;
    const day = (snapshot.days || []).find((item) => item.date === liveBaseline.date);
    if (!day || !day.is_workday) return;
    const actualHours = liveHoursForDay(day, now);
    const shiftStart = parseClockMinutes(snapshot?.profile?.workday_start_time, "09:00");
    const shiftEnd = parseClockMinutes(snapshot?.profile?.workday_end_time, "18:00");
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    day.is_live = currentMinutes >= shiftStart && currentMinutes < shiftEnd;
    day.is_completed = !day.is_live && actualHours > 0;
    day.hours_state = day.is_live ? "live" : "actual";
    day.actual_hours = actualHours.toFixed(2);
    day.credited_hours = actualHours.toFixed(2);
    snapshot.summary.actual_hours = Math.max(0, liveBaseline.summaryActualHours - liveBaseline.actualHours + actualHours);
    snapshot.summary.credited_hours = Math.max(0, liveBaseline.summaryCreditedHours - liveBaseline.creditedHours + actualHours);
    snapshot.summary.completed_days = Math.max(
      0,
      liveBaseline.summaryCompletedDays - liveBaseline.completed + (day.is_completed ? 1 : 0),
    );
    renderSummary();
    renderCalendar();
  }

  function startLiveTimer() {
    if (liveTimerId) window.clearInterval(liveTimerId);
    updateLiveWorkday(new Date(), { force: true });
    liveTimerId = window.setInterval(() => updateLiveWorkday(new Date()), 60000);
  }

  async function loadPlanOptions() {
    const data = await core.requestJson("/api/v1/plans?kind=income", authOptions());
    const plans = Array.isArray(data.items) ? data.items : [];
    const optionHtml = plans.map((item) => {
      const note = item.note || item.category_name || `План #${item.id}`;
      return `<option value="${Number(item.id)}">${escape(note)} · ${escape(item.amount)} ${escape(item.currency)}</option>`;
    }).join("");
    [nodes.workSalaryPlan, nodes.workAdvancePlan].forEach((select) => {
      const previous = select.value;
      select.innerHTML = `<option value="">Не связан</option>${optionHtml}`;
      select.value = previous;
    });
    fillProfileForm();
  }

  function renderContracts() {
    if (!contracts.length) {
      nodes.workContractsList.innerHTML = '<div class="muted-small">Периоды условий пока не добавлены</div>';
      return;
    }
    const today = localTodayIso();
    nodes.workContractsList.innerHTML = contracts.map((item) => {
      const isCurrent = item.effective_from <= today && (!item.effective_to || item.effective_to >= today);
      return `
      <article class="plan-card work-contract-card">
        <div class="plan-card-main">
          <div class="work-contract-title"><strong>${escape(item.position || "Должность не указана")}</strong>${isCurrent ? '<span class="work-contract-current">Текущая</span>' : ""}</div>
          <span>${escape(item.company || "Компания не указана")}</span>
          <span class="muted-small">с ${formatDate(item.effective_from)}${item.effective_to ? ` по ${formatDate(item.effective_to)}` : " · действует сейчас"}</span>
          ${item.note ? `<span class="muted-small work-contract-note">${escape(item.note)}</span>` : ""}
        </div>
        <div class="work-contract-side">
          <strong>${item.salary_amount == null ? "—" : `${Number(item.salary_amount).toLocaleString("ru-RU")} ${escape(item.currency)}`}</strong>
          <div class="work-contract-actions">
            <button class="btn btn-secondary btn-xs" type="button" data-edit-work-contract="${Number(item.id)}">Изменить</button>
            <button class="btn btn-danger btn-xs" type="button" data-delete-work-contract="${Number(item.id)}">Удалить</button>
          </div>
        </div>
      </article>`;
    }).join("");
  }

  async function loadContracts() {
    contracts = await core.requestJson("/api/v1/work/contracts", authOptions());
    renderContracts();
  }

  function formatCompanyEarnings(item) {
    const values = (item.earnings || []).map((earning) => (
      `${Number(earning.amount || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ${escape(earning.currency)}`
    ));
    return values.length ? values.join(" · ") : "Нет зарплатных операций";
  }

  function renderCompanies() {
    if (!companies.length) {
      nodes.workCompaniesGrid.innerHTML = '<div class="muted-small">Добавьте период работы с компанией — карточка появится здесь автоматически.</div>';
      nodes.workCompanyDetails.innerHTML = "";
      return;
    }
    selectedCompanyIndex = Math.max(0, Math.min(selectedCompanyIndex, companies.length - 1));
    nodes.workCompaniesGrid.innerHTML = companies.map((item, index) => `
      <button class="work-company-card ${index === selectedCompanyIndex ? "is-selected" : ""}" type="button" data-work-company-index="${index}">
        <span class="work-company-card-head"><strong>${escape(item.company)}</strong>${item.is_current ? '<i class="work-contract-current">Текущая</i>' : ""}</span>
        <b>${formatCompanyEarnings(item)}</b>
        <span>${item.salary_operation_count || 0} зарплатных операций</span>
        <small>с ${formatDate(item.effective_from)}${item.effective_to ? ` по ${formatDate(item.effective_to)}` : " · работаете сейчас"}</small>
      </button>
    `).join("");
    const selected = companies[selectedCompanyIndex];
    const positions = (selected.positions || []).length ? selected.positions.join(" · ") : "Должности не указаны";
    nodes.workCompanyDetails.innerHTML = `
      <article class="work-company-detail-card">
        <div class="work-company-detail-head">
          <div><span class="muted-small">Выбранная компания</span><h3>${escape(selected.company)}</h3></div>
          <strong>${formatCompanyEarnings(selected)}</strong>
        </div>
        <div class="work-company-detail-meta">
          <span><b>${selected.contract_count || 0}</b> периодов</span>
          <span><b>${selected.salary_operation_count || 0}</b> выплат</span>
          <span>${escape(positions)}</span>
        </div>
        <div class="work-company-periods">
          ${(selected.periods || []).map((period) => `
            <div class="work-company-period">
              <div><strong>${escape(period.position || "Должность не указана")}</strong><span>с ${formatDate(period.effective_from)}${period.effective_to ? ` по ${formatDate(period.effective_to)}` : " · действует сейчас"}</span></div>
              <b>${period.salary_amount == null ? "Оклад не указан" : `${Number(period.salary_amount).toLocaleString("ru-RU")} ${escape(period.currency)}`}</b>
            </div>
          `).join("")}
        </div>
        <p class="muted-small work-company-calculation-note">Заработок рассчитан по фактическим доходным операциям категории «Зарплата», попавшим в периоды работы. День перехода относится к новому периоду.</p>
      </article>`;
  }

  async function loadCompanies() {
    companies = await core.requestJson("/api/v1/work/companies", authOptions());
    nodes.workCompanyOptions.innerHTML = companies.map((item) => `<option value="${escape(item.company)}"></option>`).join("");
    if (selectedCompanyIndex >= companies.length) selectedCompanyIndex = 0;
    renderCompanies();
  }

  async function loadPaymentHistory() {
    try {
      const today = localTodayIso();
      const fallbackFrom = `${new Date().getFullYear() - 10}-${String(new Date().getMonth() + 1).padStart(2, "0")}-${String(new Date().getDate()).padStart(2, "0")}`;
      const profileStart = snapshot?.profile?.employment_start_date;
      const dateFrom = profileStart && profileStart <= today
        ? (profileStart < fallbackFrom ? fallbackFrom : profileStart)
        : fallbackFrom;
      const params = new URLSearchParams({ date_from: dateFrom, date_to: today });
      const data = await core.requestJson(`/api/v1/work/payments/history?${params}`, authOptions());
      paymentHistory = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
    } catch (error) {
      paymentHistory = [];
      if (!String(error?.message || error).includes("404")) throw error;
    }
    renderActualPayments();
    renderPayments();
    renderCalendar();
  }

  function statisticsQuery() {
    const params = new URLSearchParams({ period: statisticsPeriod });
    if (["month", "year"].includes(statisticsPeriod)) {
      params.set("anchor", `${statisticsAnchor.getFullYear()}-${String(statisticsAnchor.getMonth() + 1).padStart(2, "0")}-01`);
    }
    if (statisticsPeriod === "custom") {
      params.set("date_from", nodes.workStatisticsDateFrom.value);
      params.set("date_to", nodes.workStatisticsDateTo.value);
    }
    return params.toString();
  }

  function renderStatistics() {
    const data = statistics || {};
    const label = statisticsPeriod === "month"
      ? monthFormatter.format(statisticsAnchor)
      : statisticsPeriod === "year"
        ? String(statisticsAnchor.getFullYear())
        : statisticsPeriod === "all_time"
          ? `Всё время · ${formatDate(data.date_from)} — ${formatDate(data.date_to)}`
          : `${formatDate(data.date_from)} — ${formatDate(data.date_to)}`;
    nodes.workStatisticsPeriodLabel.textContent = label.replace(/^./, (char) => char.toUpperCase());
    const cards = [
      ["План", `${formatHours(data.planned_hours)} ч`, `${data.planned_days || 0} рабочих дней`],
      ["Отработано", `${formatHours(data.actual_hours)} ч`, `${data.completed_days || 0} дней`],
      ["Оплачиваемые", `${formatHours(data.credited_hours)} ч`, `будущий план: ${formatHours(data.future_planned_hours)} ч`],
      ["Отпуск и сикдей", `${data.vacation_days || 0} / ${data.sick_days || 0}`, `исключений: ${data.override_days || 0}`],
      ["Сверх плана", `${formatHours(data.overtime_hours)} ч`, `${data.calendar_days || 0} календарных дней`],
    ];
    nodes.workStatisticsKpi.innerHTML = cards.map(([title, value, meta]) => `
      <article class="analytics-kpi-card analytics-kpi-neutral"><div class="muted-small">${escape(title)}</div><strong>${escape(value)}</strong><div class="muted-small">${escape(meta)}</div></article>
    `).join("");
    const percent = Math.max(0, Math.min(100, Number(data.completion_percent || 0)));
    nodes.workStatisticsProgressLabel.textContent = `${formatHours(percent)}%`;
    nodes.workStatisticsProgressBar.style.width = `${percent}%`;
    const monthLabel = new Intl.DateTimeFormat("ru-RU", { month: "short", year: "numeric" });
    nodes.workStatisticsMonths.innerHTML = (data.months || []).map((item) => {
      const [year, month] = item.month.split("-").map(Number);
      const planned = Math.max(0, Number(item.planned_hours || 0));
      const actual = Math.max(0, Number(item.actual_hours || 0));
      const ratio = planned > 0 ? Math.min(100, actual / planned * 100) : 0;
      return `<article class="work-statistics-month-row">
        <div><strong>${escape(monthLabel.format(new Date(year, month - 1, 1)))}</strong><span class="muted-small">${item.completed_days || 0} из ${item.planned_days || 0} дней</span></div>
        <div class="work-statistics-month-bars"><i style="width:100%"></i><b style="width:${ratio}%"></b></div>
        <div class="work-statistics-month-values"><strong>${formatHours(actual)} ч</strong><span>из ${formatHours(planned)} ч</span></div>
      </article>`;
    }).join("") || '<div class="muted-small">За выбранный период данных нет</div>';
    const movable = ["month", "year"].includes(statisticsPeriod);
    nodes.workStatisticsPrevBtn.disabled = !movable;
    nodes.workStatisticsNextBtn.disabled = !movable;
    nodes.workStatisticsCurrentBtn.classList.toggle("hidden", !movable);
  }

  async function loadStatistics() {
    statistics = await core.requestJson(`/api/v1/work/statistics?${statisticsQuery()}`, authOptions());
    renderStatistics();
  }

  function currentWorkLoadKey() {
    return monthValue(anchor);
  }

  function createWorkLoadRequest({ refresh = false } = {}) {
    const requestedAnchor = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    return { anchor: requestedAnchor, key: monthValue(requestedAnchor), refresh: Boolean(refresh) };
  }

  async function performWorkSectionLoad(request) {
    const year = request.anchor.getFullYear();
    const month = request.anchor.getMonth() + 1;
    if (request.key === currentWorkLoadKey()) {
      workPickerYear = year;
      renderWorkPeriodPicker();
    }
    const nextSnapshot = await core.requestJson(`/api/v1/work/month?year=${year}&month=${month}`, authOptions());
    if (request.key !== currentWorkLoadKey()) return;
    snapshot = nextSnapshot;
    const loadedMonth = `${Number(snapshot.year)}-${String(Number(snapshot.month)).padStart(2, "0")}`;
    if (loadedMonth === isoMonth(observedLocalDate)) midnightReloadPending = false;
    resetLiveBaseline();
    renderSummary();
    renderMoneySummary();
    renderPayments();
    renderCalendar();
    fillProfileForm();
    startLiveTimer();
    await Promise.all([loadPlanOptions(), loadContracts(), loadCompanies(), loadStatistics(), loadPaymentHistory()]);
  }

  async function drainWorkSectionLoads() {
    let latestError = null;
    while (queuedWorkLoad) {
      const request = queuedWorkLoad;
      queuedWorkLoad = null;
      activeWorkLoadKey = request.key;
      try {
        await performWorkSectionLoad(request);
        latestError = null;
      } catch (error) {
        latestError = error;
      }
    }
    if (latestError) throw latestError;
  }

  function loadWorkSection({ refresh = false } = {}) {
    if (!bound) bind();
    const request = createWorkLoadRequest({ refresh });
    if (workLoadPromise) {
      if (!request.refresh && activeWorkLoadKey === request.key) {
        const keepsQueuedRefresh = queuedWorkLoad?.key === request.key && queuedWorkLoad.refresh;
        if (!keepsQueuedRefresh) queuedWorkLoad = null;
        return workLoadPromise;
      }
      if (queuedWorkLoad?.key === request.key) {
        queuedWorkLoad.refresh ||= request.refresh;
        return workLoadPromise;
      }
      queuedWorkLoad = request;
      return workLoadPromise;
    }
    queuedWorkLoad = request;
    workLoadPromise = Promise.resolve()
      .then(drainWorkSectionLoads)
      .finally(() => {
        workLoadPromise = null;
        activeWorkLoadKey = "";
      });
    return workLoadPromise;
  }

  function openDayEditor(iso) {
    const item = (snapshot?.days || []).find((day) => day.date === iso);
    if (!item) return;
    const [year, month, day] = iso.split("-").map(Number);
    nodes.workDayEditorTitle.textContent = dayFormatter.format(new Date(year, month - 1, day));
    nodes.workDayDate.value = iso;
    nodes.workDayDateTo.value = iso;
    nodes.workDayStatus.value = item.status;
    nodes.workDayPlanned.value = Number(item.planned_hours || 0);
    nodes.workDayActual.value = Number(item.actual_hours || 0);
    nodes.workDayCredited.value = Number(item.credited_hours || 0);
    nodes.workDayNote.value = item.note || "";
    nodes.resetWorkDayBtn.classList.toggle("hidden", !item.is_manual);
    nodes.workDayForm.classList.remove("hidden");
    nodes.workDayForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function saveDay(event) {
    event.preventDefault();
    const iso = nodes.workDayDate.value;
    const dateTo = nodes.workDayDateTo.value || iso;
    const payload = {
      status: nodes.workDayStatus.value,
      planned_hours: Number(nodes.workDayPlanned.value || 0),
      actual_hours: Number(nodes.workDayActual.value || 0),
      credited_hours: Number(nodes.workDayCredited.value || 0),
      note: nodes.workDayNote.value.trim() || null,
    };
    const isRange = dateTo !== iso;
    const url = isRange ? "/api/v1/work/days" : `/api/v1/work/days/${iso}`;
    if (isRange) {
      payload.date_from = iso;
      payload.date_to = dateTo;
    }
    await core.requestJson(url, authOptions({ method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }));
    core.notify?.("Исключение сохранено", { type: "success" });
    nodes.workDayForm.classList.add("hidden");
    await loadWorkSection({ refresh: true });
  }

  async function resetDay() {
    const iso = nodes.workDayDate.value;
    if (!iso) return;
    await core.requestJson(`/api/v1/work/days/${iso}`, authOptions({ method: "DELETE" }));
    core.notify?.("День возвращён по графику", { type: "success" });
    nodes.workDayForm.classList.add("hidden");
    await loadWorkSection({ refresh: true });
  }

  async function saveSettings(event) {
    event.preventDefault();
    const workweekDays = [...nodes.workWeekdayPicker.querySelectorAll('input[type="checkbox"]:checked')].map((input) => Number(input.value));
    const payload = {
      company: nodes.workCompany.value.trim() || null,
      position: nodes.workPosition.value.trim() || null,
      employment_start_date: nodes.workStartDate.value || null,
      standard_hours_per_day: Number(nodes.workStandardHours.value || 8),
      workweek_days: workweekDays,
      salary_plan_id: nodes.workSalaryPlan.value ? Number(nodes.workSalaryPlan.value) : null,
      advance_plan_id: nodes.workAdvancePlan.value ? Number(nodes.workAdvancePlan.value) : null,
      salary_nominal_day: Number(nodes.workSalaryDay.value || 5),
      advance_nominal_day: Number(nodes.workAdvanceDay.value || 20),
      workday_start_time: nodes.workDayStartTime.value || "09:00",
      workday_end_time: nodes.workDayEndTime.value || "18:00",
      lunch_start_time: nodes.workLunchStartTime.value || "13:00",
      lunch_end_time: nodes.workLunchEndTime.value || "14:00",
    };
    await core.requestJson("/api/v1/work/profile", authOptions({ method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }));
    core.notify?.("Настройки табеля и планов сохранены", { type: "success" });
    await loadWorkSection({ refresh: true });
  }

  function resetContractForm() {
    editingContractId = null;
    nodes.workContractForm.reset();
    nodes.workContractFormHeading.textContent = "Новый период или смена работы";
    nodes.workContractFormSubtitle.textContent = "Новая текущая работа автоматически завершит предыдущий период этой же датой. Дата перехода будет относиться к новому периоду.";
    nodes.workContractSubmitBtn.textContent = "Добавить период";
    nodes.cancelWorkContractEditBtn.classList.add("hidden");
  }

  function editContract(id) {
    const item = contracts.find((contract) => Number(contract.id) === Number(id));
    if (!item) return;
    editingContractId = Number(item.id);
    nodes.workContractFrom.value = item.effective_from || "";
    nodes.workContractTo.value = item.effective_to || "";
    nodes.workContractCompany.value = item.company || "";
    nodes.workContractPosition.value = item.position || "";
    nodes.workContractSalary.value = item.salary_amount == null ? "" : Number(item.salary_amount);
    nodes.workContractCurrency.value = item.currency || "BYN";
    nodes.workContractNote.value = item.note || "";
    nodes.workContractFormHeading.textContent = "Редактировать период работы";
    nodes.workContractFormSubtitle.textContent = "Изменения текущего периода сразу обновят компанию и должность в настройках табеля.";
    nodes.workContractSubmitBtn.textContent = "Сохранить изменения";
    nodes.cancelWorkContractEditBtn.classList.remove("hidden");
    nodes.workContractForm.scrollIntoView({ behavior: "smooth", block: "start" });
    nodes.workContractPosition.focus();
  }

  async function saveContract(event) {
    event.preventDefault();
    const payload = {
      effective_from: nodes.workContractFrom.value,
      effective_to: nodes.workContractTo.value || null,
      company: nodes.workContractCompany.value.trim() || null,
      position: nodes.workContractPosition.value.trim() || null,
      salary_amount: nodes.workContractSalary.value ? Number(nodes.workContractSalary.value) : null,
      currency: nodes.workContractCurrency.value,
      note: nodes.workContractNote.value.trim() || null,
    };
    const isEditing = editingContractId != null;
    const url = isEditing ? `/api/v1/work/contracts/${editingContractId}` : "/api/v1/work/contracts";
    await core.requestJson(url, authOptions({ method: isEditing ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }));
    resetContractForm();
    core.notify?.(isEditing ? "Период работы обновлён" : "Период условий добавлен", { type: "success" });
    await loadWorkSection({ refresh: true });
  }

  async function deleteContract(id) {
    await core.requestJson(`/api/v1/work/contracts/${id}`, authOptions({ method: "DELETE" }));
    if (editingContractId === id) resetContractForm();
    core.notify?.("Период условий удалён", { type: "success" });
    await loadWorkSection({ refresh: true });
  }

  async function openPaymentOperation(operationId, sourceNode = null) {
    const resolvedId = Number(operationId || 0);
    if (!(resolvedId > 0)) return;
    selectedPaymentOperationId = resolvedId;
    document.querySelectorAll(".work-payment-context-selected").forEach((node) => node.classList.remove("work-payment-context-selected"));
    const contextNode = sourceNode?.closest?.(".work-day-cell, .work-actual-payment-card, .work-payment-card") || sourceNode;
    contextNode?.classList?.add("work-payment-context-selected");
    const operations = window.App.getRuntimeModule?.("operations") || {};
    if (operations.openMoneyFlowSource) {
      await operations.openMoneyFlowSource({ sourceKind: "operation", sourceId: resolvedId, mode: "edit" });
    }
  }

  function scheduleRefreshAfterPaymentMutation(event) {
    const path = String(event?.detail?.path || "");
    const changesPayroll = /^\/api\/v1\/(?:operations|plans|categories)(?:\/\d+)?(?:\/|$)/.test(path);
    if (!changesPayroll || nodes.workSection?.classList.contains("hidden")) return;
    window.clearTimeout(activityRefreshTimer);
    activityRefreshTimer = window.setTimeout(() => {
      refreshPayrollAfterLinkMutation().catch(handleError);
    }, 250);
  }

  function setView(view) {
    core.syncSegmentedActive?.(nodes.workViewTabs, "work-view", view);
    nodes.workStatisticsView.classList.toggle("hidden", view !== "statistics");
    nodes.workTimesheetView.classList.toggle("hidden", view !== "timesheet");
    nodes.workSettingsForm.classList.toggle("hidden", view !== "settings");
    nodes.workCompaniesView.classList.toggle("hidden", view !== "companies");
    nodes.workContractsView.classList.toggle("hidden", view !== "contracts");
  }

  function bind() {
    collectNodes();
    nodes.workPrevMonthBtn.addEventListener("click", () => { anchor = new Date(anchor.getFullYear(), anchor.getMonth() - 1, 1); loadWorkSection().catch(handleError); });
    nodes.workNextMonthBtn.addEventListener("click", () => { anchor = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 1); loadWorkSection().catch(handleError); });
    nodes.workTodayBtn.addEventListener("click", () => { const now = new Date(); anchor = new Date(now.getFullYear(), now.getMonth(), 1); loadWorkSection().catch(handleError); });
    nodes.workMonthTrigger.addEventListener("click", () => {
      workPickerYear = anchor.getFullYear();
      renderWorkPeriodPicker();
      setWorkMonthPopoverOpen(nodes.workMonthPopover.classList.contains("hidden"));
    });
    nodes.workMonthPopover.addEventListener("click", (event) => {
      const yearButton = event.target.closest("[data-work-picker-year]");
      if (yearButton) {
        workPickerYear = Number(yearButton.dataset.workPickerYear);
        renderWorkPeriodPicker();
        return;
      }
      const monthButton = event.target.closest("[data-work-picker-month]");
      if (!monthButton) return;
      const [year, month] = String(monthButton.dataset.workPickerMonth).split("-").map(Number);
      anchor = new Date(year, month - 1, 1);
      setWorkMonthPopoverOpen(false);
      loadWorkSection().catch(handleError);
    });
    nodes.workCalendarGrid.addEventListener("click", (event) => {
      const operationButton = event.target.closest("[data-work-operation-id]");
      if (operationButton) {
        event.stopPropagation();
        openPaymentOperation(operationButton.dataset.workOperationId, operationButton).catch(handleError);
        return;
      }
      const button = event.target.closest("[data-work-date]");
      if (button) openDayEditor(button.dataset.workDate);
    });
    nodes.workCalendarGrid.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const day = event.target.closest("[data-work-date]");
      if (!day || event.target.closest("[data-work-operation-id]")) return;
      event.preventDefault();
      openDayEditor(day.dataset.workDate);
    });
    nodes.workPaymentsGrid.addEventListener("click", (event) => {
      const operationButton = event.target.closest("[data-work-operation-id]");
      if (operationButton) {
        openPaymentOperation(operationButton.dataset.workOperationId, operationButton).catch(handleError);
        return;
      }
      const button = event.target.closest("[data-work-open-plan-picker]");
      if (!button) return;
      setView("settings");
      const select = button.dataset.workOpenPlanPicker === "advance" ? nodes.workAdvancePlan : nodes.workSalaryPlan;
      select?.focus();
      select?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    nodes.workCompaniesGrid.addEventListener("click", (event) => {
      const button = event.target.closest("[data-work-company-index]");
      if (!button) return;
      selectedCompanyIndex = Number(button.dataset.workCompanyIndex || 0);
      renderCompanies();
    });
    nodes.workViewTabs.addEventListener("click", (event) => { const button = event.target.closest("[data-work-view]"); if (button) setView(button.dataset.workView); });
    nodes.workStatisticsPeriodTabs.addEventListener("click", (event) => {
      const button = event.target.closest("[data-work-stat-period]");
      if (!button) return;
      statisticsPeriod = button.dataset.workStatPeriod;
      core.syncSegmentedActive?.(nodes.workStatisticsPeriodTabs, "work-stat-period", statisticsPeriod);
      nodes.workStatisticsCustomForm.classList.toggle("hidden", statisticsPeriod !== "custom");
      if (statisticsPeriod !== "custom") loadStatistics().catch(handleError);
    });
    nodes.workStatisticsPrevBtn.addEventListener("click", () => {
      statisticsAnchor = statisticsPeriod === "year"
        ? new Date(statisticsAnchor.getFullYear() - 1, 0, 1)
        : new Date(statisticsAnchor.getFullYear(), statisticsAnchor.getMonth() - 1, 1);
      loadStatistics().catch(handleError);
    });
    nodes.workStatisticsNextBtn.addEventListener("click", () => {
      statisticsAnchor = statisticsPeriod === "year"
        ? new Date(statisticsAnchor.getFullYear() + 1, 0, 1)
        : new Date(statisticsAnchor.getFullYear(), statisticsAnchor.getMonth() + 1, 1);
      loadStatistics().catch(handleError);
    });
    nodes.workStatisticsCurrentBtn.addEventListener("click", () => {
      const now = new Date();
      statisticsAnchor = new Date(now.getFullYear(), now.getMonth(), 1);
      loadStatistics().catch(handleError);
    });
    nodes.workStatisticsCustomForm.addEventListener("submit", (event) => {
      event.preventDefault();
      loadStatistics().catch(handleError);
    });
    nodes.workDayForm.addEventListener("submit", (event) => saveDay(event).catch(handleError));
    nodes.workDayStatus.addEventListener("change", () => {
      const status = nodes.workDayStatus.value;
      const planned = Number(nodes.workDayPlanned.value || snapshot?.profile?.standard_hours_per_day || 8);
      if (["vacation", "sick_paid", "company_day_off"].includes(status)) {
        nodes.workDayActual.value = 0;
        nodes.workDayCredited.value = planned;
      } else if (["sick_unpaid", "day_off", "unpaid_leave", "holiday", "weekend"].includes(status)) {
        nodes.workDayActual.value = 0;
        nodes.workDayCredited.value = 0;
      } else {
        nodes.workDayActual.value = planned;
        nodes.workDayCredited.value = planned;
      }
    });
    nodes.closeWorkDayEditorBtn.addEventListener("click", () => nodes.workDayForm.classList.add("hidden"));
    nodes.resetWorkDayBtn.addEventListener("click", () => resetDay().catch(handleError));
    nodes.workSettingsForm.addEventListener("submit", (event) => saveSettings(event).catch(handleError));
    nodes.workContractForm.addEventListener("submit", (event) => saveContract(event).catch(handleError));
    nodes.cancelWorkContractEditBtn.addEventListener("click", resetContractForm);
    nodes.workContractsList.addEventListener("click", (event) => {
      const editButton = event.target.closest("[data-edit-work-contract]");
      if (editButton) {
        editContract(Number(editButton.dataset.editWorkContract));
        return;
      }
      const deleteButton = event.target.closest("[data-delete-work-contract]");
      if (deleteButton) deleteContract(Number(deleteButton.dataset.deleteWorkContract)).catch(handleError);
    });
    nodes.workActualPaymentsList.addEventListener("click", (event) => {
      const unlinkButton = event.target.closest("[data-work-unlink-payment]");
      if (unlinkButton) {
        event.stopPropagation();
        core.showConfirm?.(
          "Удалить связь с выплатой? Сама финансовая операция останется без изменений.",
          () => unlinkPayment(unlinkButton.dataset.workUnlinkPayment, unlinkButton).catch(handleError),
          { title: "Отвязать выплату", confirmLabel: "Отвязать", confirmTone: "danger" },
        );
        return;
      }
      const card = event.target.closest("[data-work-operation-id]");
      if (card) openPaymentOperation(card.dataset.workOperationId, card).catch(handleError);
    });
    nodes.workPaymentLinkToggle.addEventListener("click", () => {
      setPaymentLinkPanelOpen(nodes.workPaymentLinkPanel.classList.contains("hidden"));
    });
    nodes.workPaymentLinkClose.addEventListener("click", () => setPaymentLinkPanelOpen(false));
    nodes.workPaymentLinkRole.addEventListener("click", (event) => {
      const button = event.target.closest("[data-work-payment-link-role]");
      if (!button) return;
      paymentCandidateRole = button.dataset.workPaymentLinkRole === "advance" ? "advance" : "salary";
      syncPaymentLinkRole();
    });
    nodes.workPaymentCandidateForm.addEventListener("submit", (event) => {
      event.preventDefault();
      loadPaymentCandidates().catch(handleError);
    });
    nodes.workPaymentCandidateSearch.addEventListener("input", () => {
      window.clearTimeout(paymentCandidatesSearchTimer);
      paymentCandidatesSearchTimer = window.setTimeout(() => loadPaymentCandidates().catch(handleError), 350);
    });
    nodes.workPaymentCandidatesList.addEventListener("click", (event) => {
      const linkButton = event.target.closest("[data-work-link-operation]");
      if (linkButton) {
        linkPaymentOperation(linkButton.dataset.workLinkOperation, linkButton).catch(handleError);
        return;
      }
      const operationButton = event.target.closest("[data-work-operation-id]");
      if (operationButton) openPaymentOperation(operationButton.dataset.workOperationId, operationButton).catch(handleError);
    });
    document.addEventListener("app:activity-changed", scheduleRefreshAfterPaymentMutation);
    bound = true;
  }

  function handleError(error) {
    core.setStatus?.(`Ошибка раздела «Работа»: ${core.errorMessage ? core.errorMessage(error) : String(error)}`);
  }

  window.App.registerRuntimeModule?.("work", { loadWorkSection, setView });
})();
