(() => {
  const { state, el, core } = window.App;
  const operationModal = window.App.operationModal;

  function getPlansCacheKey() {
    return "plans:list";
  }

  function getPlanItems() {
    return Array.isArray(state.plansItems) ? state.plansItems : [];
  }

  function getPlanHistoryItems() {
    return Array.isArray(state.plansHistoryItems) ? state.plansHistoryItems : [];
  }

  function getFilteredPlans() {
    const query = String(el.plansSearchQ?.value || "").trim().toLowerCase();
    const activeTab = state.plansTab || "due";
    const activeKind = state.plansKindFilter || "all";
    const activeStatus = state.plansStatusFilter || "all";
    return getPlanItems().filter((item) => {
      const kindOk = activeKind === "all" || item.kind === activeKind;
      const statusOk = activeStatus === "all" || item.status === activeStatus;
      const tabOk = activeTab === "history"
        ? item.status === "confirmed" || item.status === "skipped"
        : activeTab === "oneoff"
          ? item.recurrence_enabled !== true && item.status !== "confirmed" && item.status !== "skipped"
          : activeTab === "recurring"
            ? item.recurrence_enabled === true && item.status !== "confirmed" && item.status !== "skipped"
            : item.status === "due" || item.status === "overdue" || item.status === "upcoming";
      if (!kindOk || !tabOk || !statusOk) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = [
        item.category_name || "",
        item.note || "",
        item.title || "",
      ].join(" ").toLowerCase();
      return haystack.includes(query);
    });
  }

  function getFilteredHistoryItems() {
    const query = String(el.plansSearchQ?.value || "").trim().toLowerCase();
    const activeKind = state.plansKindFilter || "all";
    const activeEventType = state.plansHistoryEventFilter || "all";
    return getPlanHistoryItems().filter((item) => {
      if (activeKind !== "all" && item.kind !== activeKind) {
        return false;
      }
      if (activeEventType !== "all" && item.event_type !== activeEventType) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = [
        item.category_name || "",
        item.note || "",
        item.event_type || "",
      ].join(" ").toLowerCase();
      return haystack.includes(query);
    });
  }

  function summarizePlans(items) {
    return items.reduce((acc, item) => {
      const amount = Number(item.amount || 0);
      if (item.status === "due" || item.status === "overdue") {
        acc.dueCount += 1;
      }
      if (item.status === "overdue") {
        acc.overdueCount += 1;
      }
      if (item.status === "upcoming") {
        acc.upcomingCount += 1;
      }
      if (item.kind === "income") {
        acc.potentialIncome += amount;
      } else {
        acc.potentialExpense += amount;
      }
      acc.netPlanned += item.kind === "income" ? amount : -amount;
      return acc;
    }, {
      dueCount: 0,
      overdueCount: 0,
      upcomingCount: 0,
      potentialExpense: 0,
      potentialIncome: 0,
      netPlanned: 0,
    });
  }

  function planNetLabel(summary) {
    const net = Number(summary?.netPlanned || 0);
    if (net > 0.000001) {
      return "Потенциальный доход";
    }
    if (net < -0.000001) {
      return "Потенциальный расход";
    }
    return "Плановый итог";
  }

  function planNetMeta(summary) {
    const expense = Number(summary?.potentialExpense || 0);
    const income = Number(summary?.potentialIncome || 0);
    if (income > 0.000001 && expense > 0.000001) {
      return `Доход: ${core.formatMoney(income)} | Расход: ${core.formatMoney(expense)}`;
    }
    if (income > 0.000001) {
      return `Потенциальный доход: ${core.formatMoney(income)}`;
    }
    if (expense > 0.000001) {
      return `Потенциальный расход: ${core.formatMoney(expense)}`;
    }
    return "Планов пока нет";
  }

  function dueProgressMeta(item) {
    const dueDate = String(item.due_date || "").trim();
    if (!dueDate) {
      return { label: "Без срока", tone: "none", percent: 0 };
    }
    if (item.status === "overdue") {
      return { label: `Просрочен с ${core.formatDateRu(dueDate)}`, tone: "overdue", percent: 100 };
    }
    if (item.status === "due") {
      return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "due", percent: 78 };
    }
    return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "upcoming", percent: 42 };
  }

  function recurrenceLabel(item) {
    if (!item.recurrence_enabled) {
      return "Разовый";
    }
    return item.recurrence_label || "Регулярный";
  }

  function formatDateTimeRu(value) {
    if (!value) {
      return "";
    }
    try {
      const date = value instanceof Date ? value : new Date(value);
      if (Number.isNaN(date.getTime())) {
        return String(value);
      }
      return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(date);
    } catch {
      return String(value);
    }
  }

  function statusLabel(status) {
    if (status === "overdue") {
      return "Просрочен";
    }
    if (status === "due") {
      return "К подтверждению";
    }
    if (status === "confirmed") {
      return "Подтвержден";
    }
    if (status === "skipped") {
      return "Пропущен";
    }
    return "Запланирован";
  }

  function historyEventLabel(eventType) {
    if (eventType === "confirmed") {
      return "Подтвержден";
    }
    if (eventType === "skipped") {
      return "Пропущен";
    }
    if (eventType === "reminded") {
      return "Напоминание";
    }
    return "Событие";
  }

  function syncPlanRecurrenceUi() {
    const enabled = Boolean(el.planRecurrenceEnabled?.checked);
    el.planRecurrenceFields?.classList.toggle("hidden", !enabled);
    const frequency = el.planRecurrenceFrequency?.value || "monthly";
    const daily = enabled && frequency === "daily";
    const weekly = enabled && frequency === "weekly";
    const monthly = enabled && frequency === "monthly";
    el.planRecurrenceWorkdaysWrap?.classList.toggle("hidden", !daily);
    el.planRecurrenceWeeklyBlock?.classList.toggle("hidden", !weekly);
    el.planRecurrenceMonthEndWrap?.classList.toggle("hidden", !monthly);
    if (!daily && el.planRecurrenceWorkdaysOnly) {
      el.planRecurrenceWorkdaysOnly.checked = false;
    }
    if (weekly && !getSelectedPlanWeekdays().length) {
      setSelectedPlanWeekdays([getPlanAnchorWeekday()]);
    }
    if (!weekly) {
      setSelectedPlanWeekdays([]);
    }
    if (monthly && el.planRecurrenceMonthEnd && state.editPlanId == null && isDateAtMonthEnd(document.getElementById("opDate")?.value || "")) {
      el.planRecurrenceMonthEnd.checked = true;
    }
    if (!monthly && el.planRecurrenceMonthEnd) {
      el.planRecurrenceMonthEnd.checked = false;
    }
  }

  function getPlanAnchorWeekday() {
    const scheduledDate = core.parseDateInputValue(document.getElementById("opDate")?.value || "") || core.getTodayIso();
    const anchor = new Date(`${scheduledDate}T00:00:00`);
    const jsWeekday = anchor.getDay();
    return (jsWeekday + 6) % 7;
  }

  function isDateAtMonthEnd(isoDate) {
    const normalized = String(isoDate || "").trim();
    if (!normalized) {
      return false;
    }
    const [year, month, day] = normalized.split("-").map((value) => Number(value || 0));
    if (!year || !month || !day) {
      return false;
    }
    return day === new Date(year, month, 0).getDate();
  }

  function getSelectedPlanWeekdays() {
    if (!el.planRecurrenceWeekdays) {
      return [];
    }
    return Array.from(el.planRecurrenceWeekdays.querySelectorAll("button[data-plan-weekday].active"))
      .map((button) => Number(button.dataset.planWeekday || 0))
      .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
      .sort((a, b) => a - b);
  }

  function setSelectedPlanWeekdays(values) {
    if (!el.planRecurrenceWeekdays) {
      return;
    }
    const selected = new Set(Array.isArray(values) ? values.map((value) => Number(value)) : []);
    Array.from(el.planRecurrenceWeekdays.querySelectorAll("button[data-plan-weekday]")).forEach((button) => {
      const weekday = Number(button.dataset.planWeekday || 0);
      button.classList.toggle("active", selected.has(weekday));
    });
  }

  function togglePlanWeekday(weekday) {
    if (!el.planRecurrenceWeekdays || Number.isNaN(weekday)) {
      return;
    }
    const button = el.planRecurrenceWeekdays.querySelector(`button[data-plan-weekday="${weekday}"]`);
    if (!button) {
      return;
    }
    const selected = new Set(getSelectedPlanWeekdays());
    if (selected.has(weekday) && selected.size > 1) {
      selected.delete(weekday);
    } else {
      selected.add(weekday);
    }
    setSelectedPlanWeekdays(Array.from(selected));
  }

  function renderPlanCard(item) {
    const kindClass = item.kind === "income" ? "income" : "expense";
    const categoryChip = item.category_name
      ? core.renderCategoryChip({ name: item.category_name, icon: item.category_icon || "", accent_color: item.category_accent_color || null }, "")
      : "<span class='muted-small'>Без категории</span>";
    const dateLabel = item.due_date ? core.formatDateRu(item.due_date) : "Без срока";
    const progress = dueProgressMeta(item);
    const kindLabel = item.kind === "income" ? "Доход" : "Расход";
    return `
      <article class="panel plan-card plan-card-${item.status || "upcoming"}">
        <div class="plan-card-main">
          <div class="plan-card-head">
            <div class="plan-card-title-row">
              ${categoryChip}
              <span class="meta-chip meta-chip-neutral">${recurrenceLabel(item)}</span>
              <span class="meta-chip meta-chip-neutral">${statusLabel(item.status)}</span>
            </div>
            <strong class="plan-card-amount amount-${kindClass}">${core.formatMoney(item.amount || 0)}</strong>
          </div>
          <div class="plan-card-fields">
            <div class="plan-card-field"><span class="muted-small">Дата</span><strong>${dateLabel}</strong></div>
            <div class="plan-card-field"><span class="muted-small">Тип</span><span class="kind-pill kind-pill-${kindClass}">${kindLabel}</span></div>
            <div class="plan-card-field"><span class="muted-small">Категория</span>${categoryChip}</div>
            <div class="plan-card-field"><span class="muted-small">Сумма</span><strong class="plan-card-amount amount-${kindClass}">${core.formatMoney(item.amount || 0)}</strong></div>
          </div>
          <div class="plan-card-meta">
            ${item.note ? `<strong>${core.highlightText(item.note, "")}</strong>` : ""}
            ${item.receipt_items?.length ? `<span class="muted-small">Позиций: ${item.receipt_items.length}</span>` : ""}
          </div>
          <div class="plan-card-progress">
            <div class="plan-card-progress-track">
              <span class="plan-card-progress-bar plan-card-progress-bar-${progress.tone}" style="width:${progress.percent}%"></span>
            </div>
            <span class="muted-small">${progress.label}</span>
          </div>
        </div>
        <div class="actions row-actions plan-card-actions">
          ${item.status !== "confirmed" && item.status !== "skipped" ? `<button class="btn btn-primary" type="button" data-plan-action="confirm" data-plan-id="${item.id}">Подтвердить</button>` : ""}
          ${item.status !== "confirmed" && item.status !== "skipped" ? `<button class="btn btn-secondary" type="button" data-plan-action="edit" data-plan-id="${item.id}">Редактировать</button>` : ""}
          ${item.recurrence_enabled && item.status !== "confirmed" ? `<button class="btn btn-secondary" type="button" data-plan-action="skip" data-plan-id="${item.id}">Пропустить</button>` : ""}
          <button class="btn btn-danger" type="button" data-plan-action="delete" data-plan-id="${item.id}">Удалить</button>
        </div>
      </article>
    `;
  }

  function renderHistoryCard(item) {
    const kindClass = item.kind === "income" ? "income" : "expense";
    const categoryChip = item.category_name
      ? core.renderCategoryChip({ name: item.category_name, icon: "", accent_color: null }, "")
      : "<span class='muted-small'>Без категории</span>";
    const eventLabel = historyEventLabel(item.event_type);
    const effectiveDate = item.effective_date ? core.formatDateRu(item.effective_date) : "Без даты";
    const createdAt = item.created_at ? formatDateTimeRu(item.created_at) : "";
    const operationMeta = item.operation_id ? `<span class="muted-small">Операция #${item.operation_id}</span>` : "";
    return `
      <article class="panel plan-card plan-history-card plan-history-card-${item.event_type || "event"}">
        <div class="plan-card-main">
          <div class="plan-card-head">
            <div class="plan-card-title-row">
              ${categoryChip}
              <span class="meta-chip meta-chip-neutral">${eventLabel}</span>
            </div>
            <strong class="plan-card-amount amount-${kindClass}">${core.formatMoney(item.amount || 0)}</strong>
          </div>
          <div class="plan-card-meta">
            ${item.note ? `<strong>${core.highlightText(item.note, "")}</strong>` : ""}
            <span class="muted-small">Дата плана: ${effectiveDate}</span>
            ${createdAt ? `<span class="muted-small">Событие: ${createdAt}</span>` : ""}
            ${operationMeta}
          </div>
        </div>
      </article>
    `;
  }

  function renderDashboardPlans() {
    if (!el.dashboardPlansList || !el.dashboardPlansKpi) {
      return;
    }
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    const items = getPlanItems()
      .filter((item) => item.status === "due" || item.status === "overdue" || item.status === "upcoming")
      .sort((a, b) => String(a.due_date || "").localeCompare(String(b.due_date || "")))
      .slice(0, ui?.dashboardOperationsLimit || 8);
    const summary = summarizePlans(items);
    el.dashboardPlansKpi.innerHTML = `
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">К подтверждению: ${summary.dueCount}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-negative">Просрочено: ${summary.overdueCount}</span>
      <span class="analytics-kpi-chip ${summary.netPlanned >= 0 ? "analytics-kpi-chip-positive" : "analytics-kpi-chip-negative"}">${planNetLabel(summary)}: ${core.formatMoney(Math.abs(summary.netPlanned))}</span>
    `;
    el.dashboardPlansList.innerHTML = items.length
      ? items.map(renderPlanCard).join("")
      : "<div class='muted-small'>Планов пока нет</div>";
  }

  function renderPlansSection() {
    const isHistoryTab = (state.plansTab || "due") === "history";
    const items = isHistoryTab ? getFilteredHistoryItems() : getFilteredPlans();
    const summary = summarizePlans(getPlanItems().filter((item) => item.status !== "confirmed" && item.status !== "skipped"));
    if (el.plansDueChip) {
      el.plansDueChip.textContent = `К подтверждению: ${summary.dueCount}`;
    }
    if (el.plansOverdueChip) {
      el.plansOverdueChip.textContent = `Просрочено: ${summary.overdueCount}`;
    }
    if (el.plansFinancialValue) {
      const label = planNetLabel(summary);
      el.plansFinancialValue.textContent = `${summary.netPlanned < 0 ? "-" : summary.netPlanned > 0 ? "+" : ""}${core.formatMoney(Math.abs(summary.netPlanned))}`;
      el.plansFinancialValue.dataset.plansFinancialLabel = label;
    }
    if (el.plansFinancialMeta) {
      el.plansFinancialMeta.textContent = planNetMeta(summary);
    }
    if (!el.plansList) {
      return;
    }
    el.plansStatusTabs?.classList.toggle("hidden", isHistoryTab);
    el.plansHistoryEventTabs?.classList.toggle("hidden", !isHistoryTab);
    el.plansList.innerHTML = items.length
      ? items.map(isHistoryTab ? renderHistoryCard : renderPlanCard).join("")
      : `<div class='panel muted-small'>${isHistoryTab ? "История по выбранному фильтру пока пуста" : "Планов для выбранного фильтра пока нет"}</div>`;
  }

  function resetPlanModalState() {
    state.createFlowMode = "plan";
    state.editPlanId = null;
    el.createEntryModeSwitch?.classList.add("hidden");
    el.planRecurrenceBlock?.classList.remove("hidden");
  }

  function hydrateCreateReceiptItems(items) {
    operationModal.clearReceiptItems?.("create");
    if (typeof operationModal.createReceiptDraft !== "function") {
      state.createReceiptItems = [];
      return;
    }
    state.createReceiptItems = (Array.isArray(items) ? items : []).map((row) => operationModal.createReceiptDraft({
      category_id: row.category_id || null,
      shop_name: row.shop_name || "",
      name: row.name || "",
      quantity: row.quantity || 0,
      unit_price: row.unit_price || 0,
      note: row.note || "",
    }, "create"));
  }

  function fillPlanModal(plan = null) {
    resetPlanModalState();
    const createTitle = document.getElementById("createTitle");
    const submitBtn = document.getElementById("submitCreateOperationBtn");
    if (createTitle) {
      createTitle.textContent = plan?.id ? "Редактировать план" : "Новый план";
    }
    if (submitBtn) {
      submitBtn.textContent = plan?.id ? "Сохранить план" : "Сохранить план";
    }
    core.syncDateFieldValue(document.getElementById("opDate"), plan?.scheduled_date || core.getTodayIso());
    document.getElementById("opAmount").value = plan?.amount || "";
    document.getElementById("opNote").value = plan?.note || "";
    operationModal.setOperationKind("create", plan?.kind || "expense");
    operationModal.selectCreateCategory?.(plan?.category_id ? Number(plan.category_id) : null);
    hydrateCreateReceiptItems(plan?.receipt_items || []);
    operationModal.setCreateOperationMode(state.createReceiptItems.length ? "receipt" : "common");
    operationModal.renderReceiptItems?.("create");
    operationModal.renderReceiptSummary?.("create");
    state.editPlanId = plan?.id ? Number(plan.id) : null;
    if (el.planRecurrenceEnabled) {
      el.planRecurrenceEnabled.checked = Boolean(plan?.recurrence_enabled);
    }
    if (el.planRecurrenceFrequency) {
      el.planRecurrenceFrequency.value = plan?.recurrence_frequency || "monthly";
    }
    if (el.planRecurrenceInterval) {
      el.planRecurrenceInterval.value = String(plan?.recurrence_interval || 1);
    }
    if (el.planRecurrenceWorkdaysOnly) {
      el.planRecurrenceWorkdaysOnly.checked = Boolean(plan?.recurrence_workdays_only);
    }
    if (el.planRecurrenceMonthEnd) {
      el.planRecurrenceMonthEnd.checked = Boolean(plan?.recurrence_month_end);
    }
    setSelectedPlanWeekdays(plan?.recurrence_weekdays || []);
    if (el.planRecurrenceEndDate) {
      core.syncDateFieldValue(el.planRecurrenceEndDate, plan?.recurrence_end_date || "");
    }
    syncPlanRecurrenceUi();
    operationModal.updateCreatePreview?.();
  }

  function getValidatedPlanPayload() {
    const scheduledDate = core.parseDateInputValue(document.getElementById("opDate").value);
    if (!scheduledDate) {
      throw new Error("Проверь дату плана");
    }
    const receiptItems = operationModal.getCreateReceiptPayload ? operationModal.getCreateReceiptPayload() : [];
    const amount = core.resolveMoneyInput(document.getElementById("opAmount").value);
    const hasReceiptItems = receiptItems.length > 0;
    const canDeriveAmountFromReceipt = hasReceiptItems && amount.empty;
    if (!canDeriveAmountFromReceipt && (!amount.valid || amount.value <= 0)) {
      throw new Error("Проверь сумму плана");
    }
    const recurrenceEnabled = Boolean(el.planRecurrenceEnabled?.checked);
    const recurrenceEndDate = core.parseDateInputValue(el.planRecurrenceEndDate?.value || "");
    return {
      kind: el.opKind.value,
      category_id: el.opCategory.value ? Number(el.opCategory.value) : null,
      amount: canDeriveAmountFromReceipt ? null : amount.formatted,
      scheduled_date: scheduledDate,
      note: String(document.getElementById("opNote").value || "").trim() || null,
      receipt_items: receiptItems,
      recurrence_enabled: recurrenceEnabled,
      recurrence_frequency: recurrenceEnabled ? (el.planRecurrenceFrequency?.value || "monthly") : null,
      recurrence_interval: recurrenceEnabled ? Math.max(1, Number(el.planRecurrenceInterval?.value || 1)) : 1,
      recurrence_weekdays: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "weekly" ? getSelectedPlanWeekdays() : [],
      recurrence_workdays_only: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "daily" ? Boolean(el.planRecurrenceWorkdaysOnly?.checked) : false,
      recurrence_month_end: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "monthly" ? Boolean(el.planRecurrenceMonthEnd?.checked) : false,
      recurrence_end_date: recurrenceEnabled ? (recurrenceEndDate || null) : null,
    };
  }

  async function refreshAfterPlanMutation({ confirmed = false } = {}) {
    core.invalidateUiRequestCache?.("plans");
    await loadPlans({ force: true });
    if (!confirmed) {
      return;
    }
    const actions = window.App.actions || {};
    const jobs = [];
    if (actions.loadOperations) {
      jobs.push(actions.loadOperations({ reset: true }));
    }
    if (actions.loadDashboard) {
      jobs.push(actions.loadDashboard());
    }
    if (actions.loadDashboardOperations) {
      jobs.push(actions.loadDashboardOperations());
    }
    if (actions.loadAnalyticsSection) {
      jobs.push(actions.loadAnalyticsSection({ force: true }));
    }
    await Promise.all(jobs);
  }

  async function loadPlans(options = {}) {
    const { force = false } = options;
    if (!force) {
      const cached = core.getUiRequestCache?.(getPlansCacheKey(), 30_000);
      if (cached?.plans?.items) {
        state.plansItems = Array.isArray(cached.plans.items) ? cached.plans.items : [];
        state.plansHistoryItems = Array.isArray(cached.history?.items) ? cached.history.items : [];
        renderPlansSection();
        renderDashboardPlans();
        return;
      }
    }
    const [plansData, historyData] = await Promise.all([
      core.requestJson("/api/v1/plans", {
        headers: core.authHeaders(),
      }),
      core.requestJson("/api/v1/plans/history", {
        headers: core.authHeaders(),
      }),
    ]);
    state.plansItems = Array.isArray(plansData.items) ? plansData.items : [];
    state.plansHistoryItems = Array.isArray(historyData.items) ? historyData.items : [];
    core.setUiRequestCache?.(getPlansCacheKey(), { plans: plansData, history: historyData });
    renderPlansSection();
    renderDashboardPlans();
  }

  async function setPlansTab(value) {
    state.plansTab = value || "due";
    core.syncSegmentedActive(el.plansTabTabs, "plan-tab", state.plansTab);
    renderPlansSection();
  }

  async function setPlansKindFilter(value) {
    state.plansKindFilter = value || "all";
    core.syncSegmentedActive(el.plansKindTabs, "plan-kind", state.plansKindFilter);
    renderPlansSection();
  }

  async function setPlansStatusFilter(value) {
    state.plansStatusFilter = value || "all";
    core.syncSegmentedActive(el.plansStatusTabs, "plan-status", state.plansStatusFilter);
    renderPlansSection();
    window.App.actions?.savePreferencesDebounced?.(250);
  }

  async function setPlansHistoryEventFilter(value) {
    state.plansHistoryEventFilter = value || "all";
    core.syncSegmentedActive(el.plansHistoryEventTabs, "plan-history-event", state.plansHistoryEventFilter);
    renderPlansSection();
    window.App.actions?.savePreferencesDebounced?.(250);
  }

  function applyPlansSearch() {
    renderPlansSection();
  }

  function openCreatePlan() {
    operationModal.openCreateModal();
    fillPlanModal(null);
  }

  async function submitPlanForm(event) {
    event.preventDefault();
    const payload = getValidatedPlanPayload();
    const planId = Number(state.editPlanId || 0);
    const method = planId > 0 ? "PATCH" : "POST";
    const url = planId > 0 ? `/api/v1/plans/${planId}` : "/api/v1/plans";
    await core.requestJson(url, {
      method,
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    operationModal.closeCreateModal();
    await refreshAfterPlanMutation();
  }

  function findPlanById(planId) {
    return getPlanItems().find((item) => Number(item.id) === Number(planId)) || null;
  }

  async function handlePlanAction(action, planId) {
    const item = findPlanById(planId);
    if (!item) {
      throw new Error("План не найден");
    }
    if (action === "edit") {
      operationModal.openCreateModal();
      fillPlanModal(item);
      return;
    }
    if (action === "confirm") {
      await core.requestJson(`/api/v1/plans/${planId}/confirm`, {
        method: "POST",
        headers: core.authHeaders(),
      });
      await refreshAfterPlanMutation({ confirmed: true });
      return;
    }
    if (action === "skip") {
      await core.requestJson(`/api/v1/plans/${planId}/skip`, {
        method: "POST",
        headers: core.authHeaders(),
      });
      await refreshAfterPlanMutation();
      return;
    }
    if (action === "delete") {
      core.runDestructiveAction({
        confirmMessage: "Удалить план?",
        doDelete: async () => {
          await core.requestJson(`/api/v1/plans/${planId}`, {
            method: "DELETE",
            headers: core.authHeaders(),
          });
        },
        onAfterDelete: async () => {
          await refreshAfterPlanMutation();
        },
        onDeleteError: "Не удалось удалить план",
      });
    }
  }

  function handlePlanActionClick(event) {
    const btn = event.target.closest("button[data-plan-action]");
    if (!btn) {
      return;
    }
    const action = btn.dataset.planAction || "";
    const planId = Number(btn.dataset.planId || 0);
    if (!planId || !action) {
      return;
    }
    const meta = {
      confirm: { pendingText: "Подтверждение...", successMessage: "План подтвержден" },
      skip: { pendingText: "Обновление...", successMessage: "План обновлен" },
    }[action];
    if (!meta) {
      handlePlanAction(action, planId).catch((err) => core.setStatus(String(err)));
      return;
    }
    core.runAction({
      button: btn,
      pendingText: meta.pendingText,
      successMessage: meta.successMessage,
      errorPrefix: "Ошибка работы с планом",
      action: () => handlePlanAction(action, planId),
    });
  }

  window.App.featurePlans = {
    loadPlans,
    renderPlansSection,
    renderDashboardPlans,
    setPlansTab,
    setPlansKindFilter,
    setPlansStatusFilter,
    setPlansHistoryEventFilter,
    applyPlansSearch,
    openCreatePlan,
    submitPlanForm,
    handlePlanActionClick,
    syncPlanRecurrenceUi,
    togglePlanWeekday,
  };
})();
