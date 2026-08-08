(() => {
  const { core } = window.App;
  const nodes = {};
  let anchor = new Date();
  anchor = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  let snapshot = null;
  let contracts = [];
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

  function collectNodes() {
    [
      "workMonthLabel", "workPrevMonthBtn", "workNextMonthBtn", "workTodayBtn", "workSummaryGrid",
      "workPaymentsGrid", "workCalendarGrid", "workViewTabs", "workTimesheetView", "workSettingsForm",
      "workContractsView", "workDayForm", "workDayEditorTitle", "workDayDate", "workDayStatus",
      "workDayDateTo",
      "workDayPlanned", "workDayActual", "workDayCredited", "workDayNote", "closeWorkDayEditorBtn",
      "resetWorkDayBtn", "workCompany", "workPosition", "workStartDate", "workStandardHours",
      "workWeekdayPicker", "workSalaryPlan", "workSalaryDay", "workAdvancePlan", "workAdvanceDay",
      "workContractForm", "workContractFrom", "workContractTo", "workContractCompany",
      "workContractPosition", "workContractSalary", "workContractCurrency", "workContractNote",
      "workContractsList",
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

  function renderPayments() {
    nodes.workPaymentsGrid.innerHTML = (snapshot?.payments || []).map((item) => `
      <article class="work-payment-card ${item.shifted ? "is-shifted" : ""}">
        <div><span class="muted-small">${escape(item.label)}</span><strong>${formatDate(item.effective_date)}</strong></div>
        <div class="work-payment-meta">
          ${item.shifted ? `<span>перенесено назад с ${formatDate(item.nominal_date)}</span>` : "<span>по номинальной дате</span>"}
          <span>${item.plan_id ? `план #${Number(item.plan_id)} связан` : "план не связан"}</span>
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
      if (payment) classes.push("has-payment");
      return `<button class="${classes.join(" ")}" type="button" data-work-date="${item.date}">
        <span class="work-day-number">${Number(String(item.date).slice(-2))}</span>
        <strong>${formatHours(item.planned_hours)} ч</strong>
        <span class="work-day-status">${escape(item.status_label)}</span>
        ${item.actual_hours > 0 ? `<span class="work-day-fact">факт ${formatHours(item.actual_hours)}</span>` : ""}
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
    nodes.workContractsList.innerHTML = contracts.map((item) => `
      <article class="plan-card work-contract-card">
        <div class="plan-card-main">
          <strong>${escape(item.position || "Должность не указана")}</strong>
          <span>${escape(item.company || "Компания не указана")}</span>
          <span class="muted-small">с ${formatDate(item.effective_from)}${item.effective_to ? ` по ${formatDate(item.effective_to)}` : " · действует сейчас"}</span>
        </div>
        <div class="work-contract-side">
          <strong>${item.salary_amount == null ? "—" : `${Number(item.salary_amount).toLocaleString("ru-RU")} ${escape(item.currency)}`}</strong>
          <button class="btn btn-danger btn-xs" type="button" data-delete-work-contract="${Number(item.id)}">Удалить</button>
        </div>
      </article>`).join("");
  }

  async function loadContracts() {
    contracts = await core.requestJson("/api/v1/work/contracts", authOptions());
    renderContracts();
  }

  async function loadWorkSection() {
    if (!bound) bind();
    const { year, month } = isoFromAnchor();
    nodes.workMonthLabel.textContent = monthFormatter.format(anchor).replace(/^./, (char) => char.toUpperCase());
    snapshot = await core.requestJson(`/api/v1/work/month?year=${year}&month=${month}`, authOptions());
    renderSummary();
    renderPayments();
    renderCalendar();
    fillProfileForm();
    await Promise.all([loadPlanOptions(), loadContracts()]);
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

  async function createContract(event) {
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
    await core.requestJson("/api/v1/work/contracts", authOptions({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }));
    nodes.workContractForm.reset();
    core.notify?.("Период условий добавлен", { type: "success" });
    await loadContracts();
  }

  async function deleteContract(id) {
    await core.requestJson(`/api/v1/work/contracts/${id}`, authOptions({ method: "DELETE" }));
    core.notify?.("Период условий удалён", { type: "success" });
    await loadContracts();
  }

  function setView(view) {
    core.syncSegmentedActive?.(nodes.workViewTabs, "work-view", view);
    nodes.workTimesheetView.classList.toggle("hidden", view !== "timesheet");
    nodes.workSettingsForm.classList.toggle("hidden", view !== "settings");
    nodes.workContractsView.classList.toggle("hidden", view !== "contracts");
  }

  function bind() {
    collectNodes();
    nodes.workPrevMonthBtn.addEventListener("click", () => { anchor = new Date(anchor.getFullYear(), anchor.getMonth() - 1, 1); loadWorkSection().catch(handleError); });
    nodes.workNextMonthBtn.addEventListener("click", () => { anchor = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 1); loadWorkSection().catch(handleError); });
    nodes.workTodayBtn.addEventListener("click", () => { const now = new Date(); anchor = new Date(now.getFullYear(), now.getMonth(), 1); loadWorkSection().catch(handleError); });
    nodes.workCalendarGrid.addEventListener("click", (event) => { const button = event.target.closest("[data-work-date]"); if (button) openDayEditor(button.dataset.workDate); });
    nodes.workViewTabs.addEventListener("click", (event) => { const button = event.target.closest("[data-work-view]"); if (button) setView(button.dataset.workView); });
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
    nodes.workContractForm.addEventListener("submit", (event) => createContract(event).catch(handleError));
    nodes.workContractsList.addEventListener("click", (event) => { const button = event.target.closest("[data-delete-work-contract]"); if (button) deleteContract(Number(button.dataset.deleteWorkContract)).catch(handleError); });
    bound = true;
  }

  function handleError(error) {
    core.setStatus?.(`Ошибка раздела «Работа»: ${core.errorMessage ? core.errorMessage(error) : String(error)}`);
  }

  window.App.registerRuntimeModule?.("work", { loadWorkSection, setView });
})();
