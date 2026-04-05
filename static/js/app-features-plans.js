(() => {
  const { state, el, core } = window.App;
  const dashboardData = window.App.getRuntimeModule?.("dashboard-data") || {};
  const operationModal = window.App.getRuntimeModule?.("operation-modal") || {};

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function getItemCatalogFeature() {
    return window.App.getRuntimeModule?.("item-catalog") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getAnalyticsFeature() {
    return window.App.getRuntimeModule?.("analytics") || {};
  }

  function getPickerUtils() {
    return window.App.getRuntimeModule?.("picker-utils") || {};
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getDashboardPlansPeriodBounds(period = state.dashboardPlansPeriod || "month", anchor = state.dashboardPlansPeriodAnchor || "current") {
    if (period === "all_time") {
      return null;
    }
    const current = core.getPeriodBounds ? core.getPeriodBounds(period) : null;
    if (!current?.dateFrom || !current?.dateTo || anchor !== "previous") {
      return current;
    }
    const parseIso = (value) => {
      const parsed = new Date(`${String(value || "").trim()}T00:00:00Z`);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    };
    const toIso = (value) => value instanceof Date && !Number.isNaN(value.getTime()) ? value.toISOString().slice(0, 10) : "";
    const addDays = (value, deltaDays) => {
      const parsed = parseIso(value);
      if (!parsed) {
        return "";
      }
      parsed.setUTCDate(parsed.getUTCDate() + deltaDays);
      return toIso(parsed);
    };
    if (period === "week") {
      return {
        dateFrom: addDays(current.dateFrom, -7),
        dateTo: addDays(current.dateTo, -7),
      };
    }
    if (period === "month") {
      const currentStart = parseIso(current.dateFrom);
      if (!currentStart) {
        return current;
      }
      const prevMonthStart = new Date(Date.UTC(currentStart.getUTCFullYear(), currentStart.getUTCMonth() - 1, 1));
      const prevMonthEnd = new Date(Date.UTC(currentStart.getUTCFullYear(), currentStart.getUTCMonth(), 0));
      return {
        dateFrom: toIso(prevMonthStart),
        dateTo: toIso(prevMonthEnd),
      };
    }
    return current;
  }

  function closeDashboardPlansPeriodPopover() {
    getPickerUtils().setPopoverOpen?.(el.dashboardPlansPeriodPopover, false, {
      owners: [el.dashboardPlansPeriodTabs].filter(Boolean),
    });
  }

  function renderDashboardPlansPeriodOptions(period = state.dashboardPlansPeriod || "month") {
    if (!el.dashboardPlansPeriodOptions) {
      return;
    }
    const currentBounds = getDashboardPlansPeriodBounds(period, "current");
    const previousBounds = getDashboardPlansPeriodBounds(period, "previous");
    const currentLabel = period === "week" ? "Эта неделя" : "Этот месяц";
    const previousLabel = period === "week" ? "Прошлая неделя" : "Прошлый месяц";
    el.dashboardPlansPeriodOptions.innerHTML = [
      `
        <button class="btn btn-secondary settings-picker-option active" type="button" data-dashboard-plans-quick-period="${period}" data-dashboard-plans-quick-anchor="current">
          ${currentLabel}
          <span class="muted-small">${core.formatPeriodLabel(currentBounds?.dateFrom || "", currentBounds?.dateTo || "")}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-dashboard-plans-quick-period="${period}" data-dashboard-plans-quick-anchor="previous">
          ${previousLabel}
          <span class="muted-small">${core.formatPeriodLabel(previousBounds?.dateFrom || "", previousBounds?.dateTo || "")}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-dashboard-plans-quick-period="all_time" data-dashboard-plans-quick-anchor="current">
          Все активные планы
          <span class="muted-small">Без ограничения по периоду</span>
        </button>
      `,
    ].join("");
  }

  function getPlansCacheKey() {
    return "plans:list";
  }

  function getPlanItems() {
    return Array.isArray(state.plansItems) ? state.plansItems : [];
  }

  function getPlanHistoryItems() {
    return Array.isArray(state.plansHistoryItems) ? state.plansHistoryItems : [];
  }

  function getCategoryMetaById(categoryId) {
    const id = Number(categoryId || 0);
    if (!id) {
      return null;
    }
    const category = (state.categories || []).find((item) => Number(item.id) === id);
    if (!category) {
      return null;
    }
    return {
      id: category.id,
      name: category.name,
      icon: category.icon || category.group_icon || null,
      accent_color: category.group_accent_color || null,
      kind: category.kind,
      group_name: category.group_name || "",
    };
  }

  function getPlanDisplayCategories(item) {
    const categories = core.getReceiptCategoryMetas
      ? core.getReceiptCategoryMetas(item?.receipt_items, item?.category_id, getCategoryMetaById)
      : [];
    if (categories.length) {
      return categories;
    }
    if (item?.category_name) {
      return [{
        id: item?.category_id ? Number(item.category_id) : null,
        name: item.category_name,
        icon: item.category_icon || null,
        accent_color: item.category_accent_color || null,
      }];
    }
    const fallback = getCategoryMetaById(item?.category_id);
    return fallback?.name ? [fallback] : [];
  }

  function getPlanBaseAmountValue(item) {
    const live = Number(item?.current_base_amount ?? NaN);
    if (Number.isFinite(live)) {
      return live;
    }
    return Number(item?.amount || 0);
  }

  function formatPlanAmountHtml(item) {
    const originalAmount = Number((item?.original_amount ?? item?.amount) || 0);
    const currency = String(item?.currency || "BYN").toUpperCase();
    const baseCurrency = String(item?.base_currency || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
    if (currency === baseCurrency) {
      return core.formatMoney(originalAmount, { currency });
    }
    const currentBaseAmount = getPlanBaseAmountValue(item);
    const currentRate = Number(item?.current_rate || 0);
    const rateDate = item?.current_rate_date ? core.formatDateRu(item.current_rate_date) : "";
    const secondary = currentRate > 0
      ? `≈ ${core.formatMoney(currentBaseAmount, { currency: baseCurrency })} по текущему курсу${rateDate ? ` · ${rateDate}` : ""}`
      : `≈ ${core.formatMoney(currentBaseAmount, { currency: baseCurrency })}`;
    return `
      <span>${core.formatMoney(originalAmount, { currency })}</span>
      <div class="muted-small">${secondary}</div>
    `;
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
      const amount = getPlanBaseAmountValue(item);
      acc.activeCount += 1;
      if (item.status === "due" || item.status === "overdue") {
        acc.dueCount += 1;
      }
      if (item.status === "due") {
        acc.todayCount += 1;
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
      activeCount: 0,
      dueCount: 0,
      todayCount: 0,
      overdueCount: 0,
      upcomingCount: 0,
      potentialExpense: 0,
      potentialIncome: 0,
      netPlanned: 0,
    });
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

  async function ensurePlansAllTimeBalance(force = false) {
    if (!force && Number.isFinite(Number(state.plansAllTimeBalance))) {
      return Number(state.plansAllTimeBalance || 0);
    }
    const data = await (dashboardData.loadAllTimeSummary
      ? dashboardData.loadAllTimeSummary({ force })
      : core.requestJson("/api/v1/dashboard/summary?period=all_time", { headers: core.authHeaders() }));
    state.plansAllTimeBalance = Number(data?.balance || 0);
    return state.plansAllTimeBalance;
  }

  function dueProgressMeta(item) {
    const dueDate = String(item.due_date || "").trim();
    if (!dueDate) {
      return { label: "Без срока", tone: "none", percent: 0 };
    }
    const dueAt = new Date(`${dueDate}T23:59:59`);
    if (Number.isNaN(dueAt.getTime())) {
      return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "none", percent: 0 };
    }
    const anchorRaw = item.progress_anchor_at || item.created_at || "";
    const anchorAt = anchorRaw ? new Date(anchorRaw) : null;
    const anchorMs = anchorAt && !Number.isNaN(anchorAt.getTime()) ? anchorAt.getTime() : Date.now();
    const totalMs = Math.max(86400000, dueAt.getTime() - anchorMs);
    const elapsedMs = Math.max(0, Date.now() - anchorMs);
    const percent = Math.max(0, Math.min(100, Math.round((elapsedMs / totalMs) * 100)));
    if (item.status === "overdue") {
      return { label: `Просрочен с ${core.formatDateRu(dueDate)}`, tone: "overdue", percent: 100 };
    }
    if (item.status === "due") {
      return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "due", percent: Math.max(90, percent) };
    }
    return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "upcoming", percent };
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

  function getUserReminderTimeZone() {
    const preferred = String(state.preferences?.data?.ui?.timezone || "").trim();
    const browserTimeZone = String(state.preferences?.data?.ui?.browser_timezone || "").trim();
    if (preferred && preferred !== "auto") {
      return preferred;
    }
    if (browserTimeZone) {
      return browserTimeZone;
    }
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    } catch {
      return "UTC";
    }
  }

  function isWorkdaysOnlyEnabled() {
    return String(el.planRecurrenceWorkdaysOnly?.value || "off") === "on";
  }

  function isMonthEndModeEnabled() {
    return String(el.planRecurrenceMonthEnd?.value || "off") === "on";
  }

  function getMonthEndIso(isoDate) {
    const normalized = core.parseDateInputValue(isoDate || "") || core.getTodayIso();
    const [year, month] = normalized.split("-").map((value) => Number(value || 0));
    if (!year || !month) {
      return core.getTodayIso();
    }
    const lastDay = new Date(year, month, 0).getDate();
    return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
  }

  function syncMonthEndScheduleDateLock() {
    const opDateInput = document.getElementById("opDate");
    const opDateWrap = document.getElementById("opDateField");
    const opDateTrigger = opDateWrap?.querySelector(".date-input-trigger");
    const shouldLock = (el.planScheduleMode?.value || "oneoff") === "recurring"
      && (el.planRecurrenceFrequency?.value || "monthly") === "monthly"
      && isMonthEndModeEnabled();
    if (!opDateInput) {
      return;
    }
    if (shouldLock) {
      core.syncDateFieldValue(opDateInput, getMonthEndIso(opDateInput.value || core.getTodayIso()));
    }
    opDateInput.disabled = shouldLock;
    if (opDateTrigger) {
      opDateTrigger.disabled = shouldLock;
      opDateTrigger.setAttribute("aria-disabled", shouldLock ? "true" : "false");
    }
    opDateWrap?.classList.toggle("is-disabled", shouldLock);
  }

  function setMonthEndMode(enabled) {
    const next = enabled ? "on" : "off";
    if (el.planRecurrenceMonthEnd) {
      el.planRecurrenceMonthEnd.value = next;
    }
    if (el.planRecurrenceMonthEndSwitch) {
      core.syncSegmentedActive(el.planRecurrenceMonthEndSwitch, "plan-month-end", next);
    }
    syncMonthEndScheduleDateLock();
  }

  function setWorkdaysOnlyMode(enabled) {
    const next = enabled ? "on" : "off";
    if (el.planRecurrenceWorkdaysOnly) {
      el.planRecurrenceWorkdaysOnly.value = next;
    }
    if (el.planRecurrenceWorkdaysSwitch) {
      core.syncSegmentedActive(el.planRecurrenceWorkdaysSwitch, "plan-workdays-only", next);
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

  function reminderLabel(item) {
    if (!item?.next_reminder_at) {
      return "";
    }
    try {
      const reminderAt = new Date(item.next_reminder_at);
      if (Number.isNaN(reminderAt.getTime())) {
        return "";
      }
      if (reminderAt.getTime() <= Date.now() + 120000) {
        return "Напоминание скоро";
      }
      return `Напоминание ${new Intl.DateTimeFormat("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: getUserReminderTimeZone(),
      }).format(reminderAt)}`;
    } catch {
      return "";
    }
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
    const enabled = (el.planScheduleMode?.value || "oneoff") === "recurring";
    el.planRecurrenceFields?.classList.toggle("hidden", !enabled);
    const frequency = el.planRecurrenceFrequency?.value || "monthly";
    const daily = enabled && frequency === "daily";
    const weekly = enabled && frequency === "weekly";
    const monthly = enabled && frequency === "monthly";
    el.planRecurrenceWorkdaysWrap?.classList.toggle("hidden", !daily);
    el.planRecurrenceWeeklyBlock?.classList.toggle("hidden", !weekly);
    el.planRecurrenceMonthEndWrap?.classList.toggle("hidden", !monthly);
    if (!daily && el.planRecurrenceWorkdaysOnly) {
      setWorkdaysOnlyMode(false);
    }
    if (weekly && !getSelectedPlanWeekdays().length) {
      setSelectedPlanWeekdays([getPlanAnchorWeekday()]);
    }
    if (!weekly) {
      setSelectedPlanWeekdays([]);
    }
    if (!monthly && el.planRecurrenceMonthEnd) {
      setMonthEndMode(false);
    }
    syncMonthEndScheduleDateLock();
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

  function renderPlanCard(item, options = {}) {
    const dashboardCompact = options.dashboardCompact === true;
    const hideActions = options.hideActions === true;
    const kindClass = item.kind === "income" ? "income" : "expense";
    const categoryChips = core.renderCategoryChipList
      ? core.renderCategoryChipList(getPlanDisplayCategories(item), "")
      : "<span class='muted-small'>Без категории</span>";
    const dateLabel = item.due_date ? core.formatDateRu(item.due_date) : "Без срока";
    const progress = dueProgressMeta(item);
    const kindLabel = item.kind === "income" ? "Доход" : "Расход";
    const hasReceiptItems = Array.isArray(item.receipt_items) && item.receipt_items.length > 0;
    const reminderMeta = reminderLabel(item)
      ? `<span class="meta-chip meta-chip-neutral">${core.escapeHtml(reminderLabel(item))}</span>`
      : "";
    const positionsMeta = hasReceiptItems
      ? `<button class="meta-chip-btn meta-chip-btn-neutral" type="button" data-plan-receipt-view-id="${item.id}">Чек</button>`
      : "";
    const noteMeta = item.note ? `<span class="muted-small">${core.highlightText(item.note, "")}</span>` : "";
    const showConfirm = item.status !== "confirmed" && item.status !== "skipped";
    const canEdit = !dashboardCompact && showConfirm;
    const canSkip = !dashboardCompact && item.recurrence_enabled && item.status !== "confirmed";
    const canDelete = !dashboardCompact;
    const showMenu = canEdit || canSkip || canDelete;
    const interactiveClass = canEdit ? " plan-card-interactive" : "";
    const interactiveAttrs = canEdit ? ` data-plan-card-edit-id="${item.id}" tabindex="0"` : "";
    return `
      <article class="panel plan-card plan-card-kind-${kindClass} plan-card-${item.status || "upcoming"}${interactiveClass}"${interactiveAttrs}>
        <div class="plan-card-topline">
          <div class="plan-card-top-meta">
            <span class="meta-chip meta-chip-neutral">${recurrenceLabel(item)}</span>
            <span class="meta-chip meta-chip-neutral">${statusLabel(item.status)}</span>
            ${reminderMeta}
          </div>
          ${showMenu ? `
            <div class="plan-card-menu-wrap">
              <button class="btn btn-secondary plan-card-menu-trigger" type="button" data-plan-menu-trigger="${item.id}" aria-label="Дополнительные действия">
                <span aria-hidden="true">⋮</span>
              </button>
              <div class="app-popover hidden plan-card-actions-popover table-kebab-popover" data-plan-menu="${item.id}">
                <div class="plan-card-actions-menu table-kebab-menu">
                  ${canEdit ? `<button class="btn btn-secondary" type="button" data-plan-action="edit" data-plan-id="${item.id}">Редактировать</button>` : ""}
                  ${canSkip ? `<button class="btn btn-secondary" type="button" data-plan-action="skip" data-plan-id="${item.id}">Пропустить</button>` : ""}
                  ${canDelete ? `<button class="btn btn-danger" type="button" data-plan-action="delete" data-plan-id="${item.id}">Удалить</button>` : ""}
                </div>
              </div>
            </div>` : ""}
        </div>
        <div class="plan-card-row">
          <div class="plan-card-primary">
            <div class="plan-card-fields">
              <div class="plan-card-field">
                <span class="muted-small">Дата</span>
                <strong>${dateLabel}</strong>
              </div>
              <div class="plan-card-field">
                <span class="muted-small">Тип</span>
                <span class="kind-pill kind-pill-${kindClass}">${kindLabel}</span>
              </div>
              <div class="plan-card-field plan-card-field-category">
                <span class="muted-small">Категория</span>
                ${categoryChips}
              </div>
              <div class="plan-card-field plan-card-field-positions">
                ${positionsMeta || "<span class='muted-small'>—</span>"}
              </div>
              <div class="plan-card-field plan-card-field-amount">
                <span class="muted-small">Сумма</span>
                <strong class="plan-card-amount amount-${kindClass}">${formatPlanAmountHtml(item)}</strong>
              </div>
            </div>
            <div class="plan-card-meta">
              ${noteMeta}
            </div>
            <div class="plan-card-progress">
              <span class="muted-small">${progress.label}</span>
              <div class="plan-card-progress-track">
                <span class="plan-card-progress-bar plan-card-progress-bar-${progress.tone}" style="width:${progress.percent}%"></span>
              </div>
            </div>
          </div>
          ${hideActions ? "" : `
          <div class="actions row-actions plan-card-actions">
            ${showConfirm ? `<button class="btn btn-primary" type="button" data-plan-action="confirm" data-plan-id="${item.id}">В операцию</button>` : ""}
          </div>`}
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
            <strong class="plan-card-amount amount-${kindClass}">${formatPlanAmountHtml(item)}</strong>
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

  function getDashboardPlansPeriodFilteredItems() {
    const period = state.dashboardPlansPeriod || "month";
    const activeItems = getPlanItems().filter((item) => item.status === "due" || item.status === "overdue" || item.status === "upcoming");
    if (period === "all_time") {
      return activeItems;
    }
    const bounds = getDashboardPlansPeriodBounds(period, state.dashboardPlansPeriodAnchor || "current");
    if (!bounds?.dateFrom || !bounds?.dateTo) {
      return activeItems;
    }
    return activeItems.filter((item) => {
      if (item.status === "overdue") {
        return true;
      }
      const dueDate = String(item.scheduled_date || item.due_date || item.operation_date || "");
      return Boolean(dueDate) && dueDate >= bounds.dateFrom && dueDate <= bounds.dateTo;
    });
  }

  function getDashboardPlansPeriodLabel() {
    const period = state.dashboardPlansPeriod || "month";
    if (period === "all_time") {
      return "Все активные планы";
    }
    const anchor = state.dashboardPlansPeriodAnchor || "current";
    const bounds = getDashboardPlansPeriodBounds(period, anchor);
    if (!bounds?.dateFrom || !bounds?.dateTo) {
      return period === "week" ? "Планы на текущую неделю" : "Планы на текущий месяц";
    }
    const base = core.formatPeriodLabel ? core.formatPeriodLabel(bounds.dateFrom, bounds.dateTo) : `${bounds.dateFrom} - ${bounds.dateTo}`;
    if (period === "week") {
      return anchor === "previous" ? `Планы за прошлую неделю: ${base}` : `Планы на неделю: ${base}`;
    }
    return anchor === "previous" ? `Планы за прошлый месяц: ${base}` : `Планы на месяц: ${base}`;
  }

  function renderDashboardPlans() {
    if (!el.dashboardPlansList || !el.dashboardPlansKpi) {
      return;
    }
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (el.dashboardPlansPeriodTabs) {
      core.syncSegmentedActive(el.dashboardPlansPeriodTabs, "dashboard-plans-period", state.dashboardPlansPeriod || "month");
    }
    if (el.dashboardPlansPeriodLabel) {
      el.dashboardPlansPeriodLabel.textContent = getDashboardPlansPeriodLabel();
    }
    const items = getDashboardPlansPeriodFilteredItems()
      .sort((a, b) => String(a.scheduled_date || a.due_date || a.operation_date || "").localeCompare(String(b.scheduled_date || b.due_date || b.operation_date || "")))
      .slice(0, ui?.dashboardOperationsLimit || 8);
    const summary = summarizePlans(items);
    el.dashboardPlansKpi.innerHTML = `
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">Активных: ${summary.activeCount}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">Сегодня: ${summary.todayCount}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-negative">Просрочено: ${summary.overdueCount}</span>
      <span class="analytics-kpi-chip ${summary.netPlanned >= 0 ? "analytics-kpi-chip-positive" : "analytics-kpi-chip-negative"}">Плановый сдвиг: ${summary.netPlanned < 0 ? "-" : "+"}${core.formatMoney(Math.abs(summary.netPlanned))}</span>
    `;
    el.dashboardPlansList.innerHTML = items.length
      ? items.map((item) => renderPlanCard(item, { dashboardCompact: true })).join("")
      : "<div class='muted-small'>Планов пока нет</div>";
  }

  async function renderPlansSection() {
    const isHistoryTab = (state.plansTab || "due") === "history";
    const items = isHistoryTab ? getFilteredHistoryItems() : getFilteredPlans();
    const summary = summarizePlans(getPlanItems().filter((item) => item.status !== "confirmed" && item.status !== "skipped"));
    const baseBalance = await ensurePlansAllTimeBalance();
    const projectedBalance = baseBalance + Number(summary.netPlanned || 0);
    if (el.plansDueChip) {
      el.plansDueChip.textContent = `Активных: ${summary.activeCount}`;
    }
    if (el.plansTodayChip) {
      el.plansTodayChip.textContent = `Сегодня: ${summary.todayCount}`;
    }
    if (el.plansOverdueChip) {
      el.plansOverdueChip.textContent = `Просрочено: ${summary.overdueCount}`;
    }
    if (el.plansFinancialValue) {
      el.plansFinancialValue.textContent = `${baseBalance < 0 ? "-" : ""}${core.formatMoney(Math.abs(baseBalance))}`;
    }
    if (el.plansFinancialDelta) {
      const netDelta = Number(summary.netPlanned || 0);
      const positive = netDelta > 0.000001;
      const negative = netDelta < -0.000001;
      el.plansFinancialDelta.textContent = `${negative ? "-" : positive ? "+" : ""}${core.formatMoney(Math.abs(netDelta))}`;
      el.plansFinancialDelta.classList.toggle("plans-financial-kpi-delta-positive", positive);
      el.plansFinancialDelta.classList.toggle("plans-financial-kpi-delta-negative", negative);
      el.plansFinancialDelta.classList.toggle("plans-financial-kpi-delta-neutral", !positive && !negative);
    }
    if (el.plansFinancialMeta) {
      el.plansFinancialMeta.textContent = `${projectedBalance < 0 ? "-" : ""}${core.formatMoney(Math.abs(projectedBalance))}`;
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
    if (el.opCurrency) {
      el.opCurrency.value = core.getCurrencyConfig?.().code || "BYN";
      el.opCurrency.disabled = false;
      el.opCurrency.title = "";
    }
    if (el.opFxRate) {
      el.opFxRate.value = "1";
    }
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

  async function fillPlanModal(plan = null) {
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
    document.getElementById("opAmount").value = plan?.original_amount || plan?.amount || "";
    document.getElementById("opNote").value = plan?.note || "";
    if (el.opCurrency) {
      el.opCurrency.value = plan?.currency || (core.getCurrencyConfig?.().code || "BYN");
    }
    operationModal.setOperationKind("create", plan?.kind || "expense");
    operationModal.selectCreateCategory?.(plan?.category_id ? Number(plan.category_id) : null);
    hydrateCreateReceiptItems(plan?.receipt_items || []);
    operationModal.setCreateOperationMode(state.createReceiptItems.length ? "receipt" : "common");
    await operationModal.syncOperationCurrencyFields?.("create");
    operationModal.renderReceiptItems?.("create");
    operationModal.renderReceiptSummary?.("create");
    state.editPlanId = plan?.id ? Number(plan.id) : null;
    if (el.planScheduleMode) {
      el.planScheduleMode.value = plan?.recurrence_enabled ? "recurring" : "oneoff";
    }
    if (el.planScheduleModeSwitch) {
      core.syncSegmentedActive(el.planScheduleModeSwitch, "plan-schedule-mode", el.planScheduleMode?.value || "oneoff");
    }
    if (el.planRecurrenceFrequency) {
      el.planRecurrenceFrequency.value = plan?.recurrence_frequency || "monthly";
    }
    if (el.planRecurrenceInterval) {
      el.planRecurrenceInterval.value = String(plan?.recurrence_interval || 1);
    }
    setWorkdaysOnlyMode(Boolean(plan?.recurrence_workdays_only));
    setMonthEndMode(Boolean(plan?.recurrence_month_end));
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
    const recurrenceEnabled = (el.planScheduleMode?.value || "oneoff") === "recurring";
    const recurrenceEndDate = core.parseDateInputValue(el.planRecurrenceEndDate?.value || "");
    return {
      kind: el.opKind.value,
      category_id: el.opCategory.value ? Number(el.opCategory.value) : null,
      amount: canDeriveAmountFromReceipt ? null : amount.formatted,
      currency: String(el.opCurrency?.value || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase(),
      scheduled_date: scheduledDate,
      note: String(document.getElementById("opNote").value || "").trim() || null,
      receipt_items: receiptItems,
      recurrence_enabled: recurrenceEnabled,
      recurrence_frequency: recurrenceEnabled ? (el.planRecurrenceFrequency?.value || "monthly") : null,
      recurrence_interval: recurrenceEnabled ? Math.max(1, Number(el.planRecurrenceInterval?.value || 1)) : 1,
      recurrence_weekdays: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "weekly" ? getSelectedPlanWeekdays() : [],
      recurrence_workdays_only: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "daily" ? isWorkdaysOnlyEnabled() : false,
      recurrence_month_end: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "monthly" ? isMonthEndModeEnabled() : false,
      recurrence_end_date: recurrenceEnabled ? (recurrenceEndDate || null) : null,
    };
  }

  async function refreshAfterPlanMutation({ confirmed = false } = {}) {
    core.invalidateUiRequestCache?.("plans");
    core.invalidateUiRequestCache?.("item-catalog");
    core.invalidateUiRequestCache?.("analytics");
    core.invalidateUiRequestCache?.("dashboard:highlights");
    if (confirmed) {
      state.plansAllTimeBalance = null;
      dashboardData.invalidateSummaryCache?.();
    }
    await loadPlans({ force: true });
    const itemCatalogFeature = getItemCatalogFeature();
    if (itemCatalogFeature.loadItemCatalog) {
      await itemCatalogFeature.loadItemCatalog({ force: true });
    }
    if (!confirmed) {
      return;
    }
    const jobs = [];
    const operationsFeature = getOperationsFeature();
    const dashboardFeature = getDashboardFeature();
    const analyticsFeature = getAnalyticsFeature();
    if (operationsFeature.loadOperations) {
      jobs.push({ label: "Операции", run: () => operationsFeature.loadOperations({ reset: true }) });
    }
    if (dashboardFeature.loadDashboard) {
      jobs.push({ label: "Дашборд", run: () => dashboardFeature.loadDashboard() });
    }
    if (dashboardFeature.loadDashboardOperations) {
      jobs.push({ label: "Планы на дашборде", run: () => dashboardFeature.loadDashboardOperations() });
    }
    if (analyticsFeature.loadAnalyticsSection) {
      jobs.push({ label: "Аналитика", run: () => analyticsFeature.loadAnalyticsSection({ force: true }) });
    }
    const results = await Promise.allSettled(jobs.map((job) => job.run()));
    const failed = [];
    for (let idx = 0; idx < results.length; idx += 1) {
      if (results[idx].status !== "rejected") {
        continue;
      }
      failed.push(jobs[idx].label);
    }
    if (failed.length > 0) {
      console.warn("Plan confirm post-refresh partial failure", failed);
    }
  }

  async function loadPlans(options = {}) {
    const { force = false } = options;
    if (!force) {
      const cached = core.getUiRequestCache?.(getPlansCacheKey(), 30_000);
      if (cached?.plans?.items) {
        state.plansItems = Array.isArray(cached.plans.items) ? cached.plans.items : [];
        state.plansHistoryItems = Array.isArray(cached.history?.items) ? cached.history.items : [];
        await renderPlansSection();
        renderDashboardPlans();
        state.dashboardPlansHydrated = true;
        state.plansSectionHydrated = true;
        return;
      }
    }
    if (!state.plansSectionHydrated && state.activeSection === "plans") {
      getLoadingSkeletons().renderPlansSectionSkeleton?.();
    }
    if (!state.dashboardPlansHydrated && state.activeSection === "dashboard") {
      getLoadingSkeletons().renderDashboardPlansSkeleton?.();
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
    await renderPlansSection();
    renderDashboardPlans();
    state.dashboardPlansHydrated = true;
    state.plansSectionHydrated = true;
  }

  async function setPlansTab(value) {
    state.plansTab = value || "due";
    core.syncSegmentedActive(el.plansTabTabs, "plan-tab", state.plansTab);
    await renderPlansSection();
  }

  async function setPlansKindFilter(value) {
    state.plansKindFilter = value || "all";
    core.syncSegmentedActive(el.plansKindTabs, "plan-kind", state.plansKindFilter);
    await renderPlansSection();
  }

  async function setPlansStatusFilter(value) {
    state.plansStatusFilter = value || "all";
    core.syncSegmentedActive(el.plansStatusTabs, "plan-status", state.plansStatusFilter);
    await renderPlansSection();
    getSessionFeature().savePreferencesDebounced?.(250);
  }

  async function setPlansHistoryEventFilter(value) {
    state.plansHistoryEventFilter = value || "all";
    core.syncSegmentedActive(el.plansHistoryEventTabs, "plan-history-event", state.plansHistoryEventFilter);
    await renderPlansSection();
    getSessionFeature().savePreferencesDebounced?.(250);
  }

  function openDashboardPlansPeriodPopover(period, trigger) {
    if (!["week", "month"].includes(period) || !el.dashboardPlansPeriodPopover) {
      return;
    }
    renderDashboardPlansPeriodOptions(period);
    getPickerUtils().setPopoverOpen?.(el.dashboardPlansPeriodPopover, true, {
      owners: [trigger || el.dashboardPlansPeriodTabs].filter(Boolean),
      onClose: () => closeDashboardPlansPeriodPopover(),
    });
  }

  async function setDashboardPlansPeriod(value, anchor = "current") {
    const next = ["week", "month", "all_time"].includes(value) ? value : "month";
    state.dashboardPlansPeriod = next;
    state.dashboardPlansPeriodAnchor = next === "all_time" ? "current" : (anchor === "previous" ? "previous" : "current");
    core.syncSegmentedActive(el.dashboardPlansPeriodTabs, "dashboard-plans-period", next);
    closeDashboardPlansPeriodPopover();
    if (!getPlanItems().length) {
      await loadPlans({ force: true });
      getSessionFeature().savePreferencesDebounced?.(250);
      return;
    }
    renderDashboardPlans();
    getSessionFeature().savePreferencesDebounced?.(250);
  }

  function applyPlansSearch() {
    renderPlansSection().catch((err) => core.setStatus(String(err)));
  }

  async function openCreatePlan() {
    await operationModal.openCreateModal();
    await fillPlanModal(null);
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
      await operationModal.openCreateModal();
      await fillPlanModal(item);
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
    const menuTrigger = event.target.closest("button[data-plan-menu-trigger]");
    if (menuTrigger) {
      const planId = String(menuTrigger.dataset.planMenuTrigger || "");
      const menu = document.querySelector(`.plan-card-actions-popover[data-plan-menu="${planId}"]`);
      const card = menuTrigger.closest(".plan-card");
      const pickerUtils = getPickerUtils();
      if (menu && pickerUtils?.setPopoverOpen) {
        const owners = [menuTrigger, menuTrigger.parentElement].filter(Boolean);
        const clearOpenState = () => {
          card?.classList.remove("plan-card-menu-open");
        };
        const shouldOpen = menu.classList.contains("hidden");
        document.querySelectorAll(".plan-card.plan-card-menu-open").forEach((node) => {
          if (node !== card) {
            node.classList.remove("plan-card-menu-open");
          }
        });
        document.querySelectorAll(".plan-card-actions-popover:not(.hidden)").forEach((node) => {
          if (node !== menu) {
            pickerUtils.setPopoverOpen(node, false, {
              owners: Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : [],
            });
            (Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
          }
        });
        pickerUtils.setPopoverOpen(menu, shouldOpen, { owners, onClose: clearOpenState });
        if (card) {
          card.classList.toggle("plan-card-menu-open", shouldOpen);
        }
        if (!shouldOpen) {
          clearOpenState();
          menuTrigger.blur?.();
        }
      }
      return;
    }
    const receiptBtn = event.target.closest("button[data-plan-receipt-view-id]");
    if (receiptBtn) {
      const item = findPlanById(Number(receiptBtn.dataset.planReceiptViewId || 0));
      const operationsFeature = getOperationsFeature();
      if (item?.id && operationsFeature.openOperationReceiptModal) {
        operationsFeature.openOperationReceiptModal({
          ...item,
          operation_date: item.due_date || item.operation_date || core.getTodayIso(),
        });
      }
      return;
    }
    const btn = event.target.closest("button[data-plan-action]");
    if (!btn) {
      const card = event.target.closest("article[data-plan-card-edit-id]");
      if (!card) {
        return;
      }
      const clickedInteractive = event.target.closest("button, a, input, select, textarea, label, .app-popover");
      if (clickedInteractive) {
        return;
      }
      const planId = Number(card.dataset.planCardEditId || 0);
      if (planId) {
        handlePlanAction("edit", planId).catch((err) => core.setStatus(String(err)));
      }
      return;
    }
    const menu = btn.closest(".plan-card-actions-popover");
    const pickerUtils = getPickerUtils();
    if (menu && pickerUtils?.setPopoverOpen) {
      pickerUtils.setPopoverOpen(menu, false, {
        owners: Array.isArray(menu.__appPopoverOwners) ? menu.__appPopoverOwners : [],
      });
      (Array.isArray(menu.__appPopoverOwners) ? menu.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
      menu.closest(".plan-card")?.classList.remove("plan-card-menu-open");
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

  if (el.dashboardPlansPeriodOptions) {
    el.dashboardPlansPeriodOptions.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-dashboard-plans-quick-period][data-dashboard-plans-quick-anchor]");
      if (!btn) {
        return;
      }
      setDashboardPlansPeriod(
        String(btn.dataset.dashboardPlansQuickPeriod || ""),
        String(btn.dataset.dashboardPlansQuickAnchor || "current"),
      ).catch((err) => core.setStatus(String(err)));
    });
  }

  const api = {
    loadPlans,
    renderPlansSection,
    renderDashboardPlans,
    renderPlanCardMarkup: renderPlanCard,
    setPlansTab,
    setPlansKindFilter,
    setPlansStatusFilter,
    setPlansHistoryEventFilter,
    setDashboardPlansPeriod,
    openDashboardPlansPeriodPopover,
    applyPlansSearch,
    openCreatePlan,
    submitPlanForm,
    handlePlanActionClick,
    syncPlanRecurrenceUi,
    togglePlanWeekday,
  };

  window.App.registerRuntimeModule?.("plans", api);

  document.addEventListener("keydown", (event) => {
    const card = event.target.closest?.("article[data-plan-card-edit-id]");
    if (!card) {
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    const planId = Number(card.dataset.planCardEditId || 0);
    if (planId) {
      handlePlanAction("edit", planId).catch((err) => core.setStatus(String(err)));
    }
  });
})();
