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
  let selectedCompanyIndex = 0;
  let editingContractId = null;
  let bound = false;

  const monthFormatter = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" });
  const dayFormatter = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric", weekday: "long" });

  function byId(id) { return document.getElementById(id); }
  function escape(value) { return core.escapeHtml ? core.escapeHtml(String(value ?? "")) : String(value ?? ""); }
  function authOptions(extra = {}) { return { ...extra, headers: { ...core.authHeaders(), ...(extra.headers || {}) } }; }
  function isoFromAnchor() { return { year: anchor.getFullYear(), month: anchor.getMonth() + 1 }; }
  function formatHours(value) { return Number(value || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 }); }
  function formatDate(iso) {
    const [year, month, day] = String(iso).split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString("ru-RU");
  }
  function localTodayIso() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  }
  function getPickerUtils() { return window.App.getRuntimeModule?.("picker-utils") || window.App.pickerUtils || {}; }
  function monthValue(value) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`; }
  function formatMonthLabel(value) { return monthFormatter.format(value).replace(/^./, (char) => char.toUpperCase()); }

  function collectNodes() {
    [
      "workMonthTrigger", "workMonthPopover", "workYearOptions", "workMonthOptions",
      "workPrevMonthBtn", "workNextMonthBtn", "workTodayBtn", "workSummaryGrid",
      "workPaymentsGrid", "workCalendarGrid", "workViewTabs", "workTimesheetView", "workSettingsForm",
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
    nodes.workPaymentsGrid.innerHTML = (snapshot?.payments || []).map((item) => `
      <article class="work-payment-card ${item.shifted ? "is-shifted" : ""}">
        <div><span class="muted-small">${escape(item.label)}</span><strong>${formatDate(item.effective_date)}</strong></div>
        <div class="work-payment-meta">
          ${item.shifted ? `<span>перенесено назад с ${formatDate(item.nominal_date)}</span>` : "<span>по номинальной дате</span>"}
          <button class="work-payment-plan-link" type="button" data-work-open-plan-picker="${escape(item.role)}">
            ${item.plan_id ? `План #${Number(item.plan_id)} · изменить` : "Выбрать план вручную"}
          </button>
        </div>
      </article>`).join("");
  }

  function renderCalendar() {
    const days = snapshot?.days || [];
    const paymentByDate = new Map((snapshot?.payments || []).map((item) => [item.effective_date, item]));
    const firstOffset = days.length ? Number(days[0].weekday || 0) : 0;
    const placeholders = Array.from({ length: firstOffset }, () => '<div class="work-day-cell work-day-empty"></div>').join("");
    nodes.workCalendarGrid.innerHTML = placeholders + days.map((item) => {
      const payment = paymentByDate.get(item.date);
      const classes = ["work-day-cell", `status-${item.status}`];
      if (item.is_manual) classes.push("is-manual");
      if (item.is_future) classes.push("is-future");
      if (Number(item.actual_hours || 0) > 0) classes.push("is-completed");
      if (item.is_future && Number(item.planned_hours || 0) > 0) classes.push("is-forecast");
      if (payment) classes.push("has-payment");
      const isToday = item.date === localTodayIso();
      if (isToday) classes.push("is-today");
      const plannedHours = Number(item.planned_hours || 0);
      const actualHours = Number(item.actual_hours || 0);
      let hours = "";
      if (item.is_future && plannedHours > 0) {
        hours = `<span class="work-hours-chip work-hours-chip-forecast">Прогноз · ${formatHours(plannedHours)} ч</span>`;
      } else if (!item.is_future && (plannedHours > 0 || actualHours > 0)) {
        const plan = plannedHours !== actualHours
          ? `<span class="work-hours-chip work-hours-chip-plan">План · ${formatHours(plannedHours)} ч</span>`
          : "";
        hours = `<span class="work-hours-chip work-hours-chip-fact">Факт · ${formatHours(actualHours)} ч</span>${plan}`;
      }
      const note = item.note
        ? `<span class="work-day-note" title="${escape(item.note)}">${escape(item.note)}</span>`
        : "";
      return `<button class="${classes.join(" ")}" type="button" data-work-date="${item.date}"${isToday ? ' aria-current="date"' : ""}>
        <span class="work-day-number">${Number(String(item.date).slice(-2))}</span>
        ${isToday ? '<span class="work-day-today-label">Сегодня</span>' : ""}
        <span class="work-day-hours">${hours}</span>
        <span class="work-day-status">${escape(item.status_label)}</span>
        ${note}
        ${payment ? `<span class="work-day-payment">${escape(payment.label)}</span>` : ""}
        ${item.is_manual ? '<span class="work-day-manual-mark" title="Изменено вручную">●</span>' : ""}
      </button>`;
    }).join("");
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

  async function loadWorkSection() {
    if (!bound) bind();
    const { year, month } = isoFromAnchor();
    workPickerYear = anchor.getFullYear();
    renderWorkPeriodPicker();
    snapshot = await core.requestJson(`/api/v1/work/month?year=${year}&month=${month}`, authOptions());
    renderSummary();
    renderPayments();
    renderCalendar();
    fillProfileForm();
    await Promise.all([loadPlanOptions(), loadContracts(), loadCompanies(), loadStatistics()]);
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
    await loadWorkSection();
  }

  async function resetDay() {
    const iso = nodes.workDayDate.value;
    if (!iso) return;
    await core.requestJson(`/api/v1/work/days/${iso}`, authOptions({ method: "DELETE" }));
    core.notify?.("День возвращён по графику", { type: "success" });
    nodes.workDayForm.classList.add("hidden");
    await loadWorkSection();
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
    };
    await core.requestJson("/api/v1/work/profile", authOptions({ method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }));
    core.notify?.("Настройки табеля и планов сохранены", { type: "success" });
    await loadWorkSection();
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
    await loadWorkSection();
  }

  async function deleteContract(id) {
    await core.requestJson(`/api/v1/work/contracts/${id}`, authOptions({ method: "DELETE" }));
    if (editingContractId === id) resetContractForm();
    core.notify?.("Период условий удалён", { type: "success" });
    await loadWorkSection();
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
    nodes.workCalendarGrid.addEventListener("click", (event) => { const button = event.target.closest("[data-work-date]"); if (button) openDayEditor(button.dataset.workDate); });
    nodes.workPaymentsGrid.addEventListener("click", (event) => {
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
    bound = true;
  }

  function handleError(error) {
    core.setStatus?.(`Ошибка раздела «Работа»: ${core.errorMessage ? core.errorMessage(error) : String(error)}`);
  }

  window.App.registerRuntimeModule?.("work", { loadWorkSection, setView });
})();
